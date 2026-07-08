import csv
import json
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from functools import wraps

from django.contrib.auth.hashers import make_password, check_password
from django.db import connection
from django.db.models import Prefetch
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods

from .models import (
    Activo, Amenaza, Vulnerabilidad, EscenarioRiesgo, Usuario,
    Tratamiento, Comunicacion, AuditoriaCambio
)


# ============================================================
# AUTENTICACIÓN Y AUTORIZACIÓN
# ============================================================

def login_requerido(vista_func):
    """Protege vistas HTML y endpoints API mediante sesión activa."""
    @wraps(vista_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('usuario_id'):
            if request.path.startswith('/api/'):
                return JsonResponse(
                    {'success': False, 'message': 'Sesión no válida. Inicie sesión nuevamente.'},
                    status=401,
                )
            return redirect(f"/login/?next={request.path}")
        return vista_func(request, *args, **kwargs)
    return wrapper


def rol_requerido(*roles_permitidos):
    """Exige sesión activa y rol autorizado para ejecutar la acción."""
    def decorador(vista_func):
        @wraps(vista_func)
        def wrapper(request, *args, **kwargs):
            if not request.session.get('usuario_id'):
                if request.path.startswith('/api/'):
                    return JsonResponse({'success': False, 'message': 'Sesión no válida.'}, status=401)
                return redirect(f"/login/?next={request.path}")

            if request.session.get('usuario_rol') not in roles_permitidos:
                if request.path.startswith('/api/'):
                    return JsonResponse(
                        {'success': False, 'message': 'No tiene permisos suficientes para esta acción.'},
                        status=403,
                    )
                return render(request, 'mercpd_app/403.html', status=403)
            return vista_func(request, *args, **kwargs)
        return wrapper
    return decorador


def vista_login(request):
    """Pantalla de inicio de sesión."""
    if request.method == 'POST':
        email = (request.POST.get('email') or '').strip()
        password = request.POST.get('password') or ''

        try:
            usuario = Usuario.objects.get(email=email)
        except Usuario.DoesNotExist:
            return render(request, 'mercpd_app/login.html', {'error': 'Credenciales inválidas.'})

        if not usuario.passwordhash or not check_password(password, usuario.passwordhash):
            return render(request, 'mercpd_app/login.html', {'error': 'Credenciales inválidas.'})

        request.session['usuario_id'] = usuario.usuarioid
        request.session['usuario_nombre'] = usuario.nombre
        request.session['usuario_rol'] = usuario.rol

        next_url = request.GET.get('next') or request.POST.get('next') or '/'
        if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            next_url = '/'
        return redirect(next_url)

    return render(request, 'mercpd_app/login.html')


def vista_logout(request):
    """Cierra la sesión activa."""
    request.session.flush()
    return redirect('/login/')


# ============================================================
# REGLAS DE NEGOCIO MERC-PD v2.0
# ============================================================

def calcular_valor_activo(c, i, d):
    """VA = (C * 0.40) + (I * 0.35) + (D * 0.25), con entradas 1-3."""
    va = (c * 0.4) + (i * 0.35) + (d * 0.25)
    return Decimal(str(va)).quantize(Decimal('0.001'))


def calcular_impacto_y_riesgo(va, probabilidad, impacto_operativo, impacto_spdp, impacto_financiero):
    """
    Calcula Impacto Base, Impacto Final y Riesgo Total.
    Mantiene entradas 1-3 y clasifica el resultado final en 5 niveles.
    """
    va_float = float(va)
    impacto_spdp_efectivo = impacto_spdp
    piso_aplicado = False

    if va_float >= 2.5 and impacto_spdp < 3:
        impacto_spdp_efectivo = 3
        piso_aplicado = True

    impacto_base = max(impacto_operativo, impacto_spdp_efectivo, impacto_financiero)
    impacto_final = impacto_base * (va_float / 3.0)
    impacto_final_dec = Decimal(str(impacto_final)).quantize(Decimal('0.001'))
    riesgo_total = probabilidad * float(impacto_final_dec)
    riesgo_total_dec = Decimal(str(riesgo_total)).quantize(Decimal('0.001'))

    return impacto_base, impacto_final_dec, riesgo_total_dec, piso_aplicado


def calcular_fecha_limite(riesgo_total):
    """
    MERC-PD v2.0 - cinco niveles:
    Muy Bajo -> 180 días, Bajo -> 90 días, Medio -> 30 días,
    Alto -> 15 días, Crítico -> 7 días.
    """
    riesgo_total = float(riesgo_total)
    if riesgo_total >= 7.5:
        dias = 7
    elif riesgo_total >= 5.0:
        dias = 15
    elif riesgo_total >= 3.0:
        dias = 30
    elif riesgo_total >= 1.5:
        dias = 90
    else:
        dias = 180
    return timezone.now() + timedelta(days=dias)


def nivel_de_riesgo(puntaje):
    """Traduce el puntaje numérico al nivel cualitativo MERC-PD v2.0."""
    puntaje = float(puntaje)
    if puntaje < 1.5:
        return 'Muy Bajo'
    if puntaje < 3.0:
        return 'Bajo'
    if puntaje < 5.0:
        return 'Medio'
    if puntaje < 7.5:
        return 'Alto'
    return 'Critico'


def registrar_auditoria(request, tabla, registro_id, accion, detalle=''):
    """Registra bitácora de auditoría sin interrumpir el flujo principal."""
    try:
        AuditoriaCambio.objects.create(
            tablaafectada=tabla,
            registroid=registro_id,
            accion=accion,
            usuario_id=request.session.get('usuario_id'),
            detalle=detalle,
        )
    except Exception:
        pass


# ============================================================
# VISTAS HTML
# ============================================================

@login_requerido
def vista_dashboard_principal(request):
    return render(request, 'mercpd_app/dashboard.html')


@rol_requerido('Administrador', 'Arquitecto de Seguridad')
def vista_registro_activos(request):
    return render(request, 'mercpd_app/activos.html')


@rol_requerido('Administrador', 'Arquitecto de Seguridad')
def vista_identificacion_riesgos(request):
    return render(request, 'mercpd_app/identificador_riesgos.html')


@rol_requerido('Administrador', 'Arquitecto de Seguridad')
def vista_tratamiento_riesgo(request):
    return render(request, 'mercpd_app/tratamientos.html')


@login_requerido
def vista_comunicacion_reportes(request):
    return render(request, 'mercpd_app/comunicacion.html')


@rol_requerido('Administrador')
def vista_registro_usuario(request):
    """Permite al Administrador registrar usuarios del sistema."""
    if request.method == 'POST':
        nombre = (request.POST.get('nombre') or '').strip()
        email = (request.POST.get('email') or '').strip()
        rol = (request.POST.get('rol') or '').strip()
        password = request.POST.get('password') or ''

        roles_validos = ('Administrador', 'Arquitecto de Seguridad', 'Custodio de Activo', 'Auditor')
        if not all([nombre, email, rol, password]):
            return render(request, 'mercpd_app/registro_usuario.html', {'error': 'Todos los campos son obligatorios.'})
        if rol not in roles_validos:
            return render(request, 'mercpd_app/registro_usuario.html', {'error': 'Rol inválido.'})
        if Usuario.objects.filter(email=email).exists():
            return render(request, 'mercpd_app/registro_usuario.html', {'error': 'Ya existe un usuario con ese correo.'})

        usuario = Usuario.objects.create(
            nombre=nombre,
            email=email,
            rol=rol,
            passwordhash=make_password(password),
        )
        registrar_auditoria(request, 'Usuarios', usuario.usuarioid, 'CREAR', f'Usuario "{nombre}" ({rol}) creado.')
        return render(request, 'mercpd_app/registro_usuario.html', {'success': f'Usuario "{nombre}" creado exitosamente.'})

    return render(request, 'mercpd_app/registro_usuario.html')


@rol_requerido('Administrador', 'Auditor')
def vista_auditoria(request):
    return render(request, 'mercpd_app/auditoria.html')


# ============================================================
# API - CATÁLOGOS Y ACTIVOS
# ============================================================

@login_requerido
def api_activos_lista(request):
    activos = Activo.objects.all().order_by('nombre')
    if request.session.get('usuario_rol') == 'Custodio de Activo':
        activos = activos.filter(custodio_id=request.session.get('usuario_id'))
    data = [{'id': a.activoid, 'nombre': a.nombre, 'va': float(a.valoractivo)} for a in activos]
    return JsonResponse({'activos': data})


@rol_requerido('Administrador', 'Arquitecto de Seguridad')
def api_usuarios_lista(request):
    usuarios = Usuario.objects.all().order_by('nombre')
    data = [{'id': u.usuarioid, 'nombre': u.nombre, 'rol': u.rol} for u in usuarios]
    return JsonResponse({'usuarios': data})


@rol_requerido('Administrador', 'Arquitecto de Seguridad')
def api_amenazas_lista(request):
    amenazas = Amenaza.objects.all().order_by('tipo', 'nombre')
    data = [{'id': a.amenazaid, 'nombre': a.nombre, 'tipo': a.tipo} for a in amenazas]
    return JsonResponse({'amenazas': data})


@rol_requerido('Administrador', 'Arquitecto de Seguridad')
def api_vulnerabilidades_lista(request):
    vulnerabilidades = Vulnerabilidad.objects.all().order_by('tipo', 'nombre')
    data = [{'id': v.vulnerabilidadid, 'nombre': v.nombre, 'tipo': v.tipo} for v in vulnerabilidades]
    return JsonResponse({'vulnerabilidades': data})


@rol_requerido('Administrador', 'Arquitecto de Seguridad')
@require_http_methods(["POST"])
def api_activos_registrar(request):
    try:
        body = json.loads(request.body)
        nombre = (body.get('nombre') or '').strip()
        tipo = (body.get('tipo') or '').strip()
        if not nombre or not tipo:
            return JsonResponse({'success': False, 'message': 'Nombre y tipo de activo son obligatorios.'}, status=400)

        c = int(body.get('confidencialidad'))
        i = int(body.get('integridad'))
        d = int(body.get('disponibilidad'))
        if not all(1 <= v <= 3 for v in (c, i, d)):
            return JsonResponse({'success': False, 'message': 'Los valores C, I, D deben estar entre 1 y 3.'}, status=400)

        custodio_id_raw = body.get('custodio_id')
        custodio_id = int(custodio_id_raw) if custodio_id_raw else None
        if custodio_id is not None:
            get_object_or_404(Usuario, pk=custodio_id)

        va = calcular_valor_activo(c, i, d)
        activo = Activo.objects.create(
            nombre=nombre,
            categoria=tipo,
            confidencialidad=c,
            integridad=i,
            disponibilidad=d,
            valoractivo=va,
            custodio_id=custodio_id,
        )
        registrar_auditoria(request, 'Activos', activo.activoid, 'CREAR', f'Activo "{nombre}" registrado (VA={va}).')
        return JsonResponse({'success': True, 'va': float(va), 'activo_id': activo.activoid, 'critico': va >= Decimal('2.5')})
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Formato de solicitud inválido (JSON).'}, status=400)
    except (ValueError, TypeError, KeyError):
        return JsonResponse({'success': False, 'message': 'Datos inválidos. Verifique los campos enviados.'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error inesperado: {str(e)}'}, status=500)


# ============================================================
# API - IDENTIFICACIÓN Y EVALUACIÓN DE RIESGOS
# ============================================================

@login_requerido
def api_escenarios_lista(request):
    escenarios = EscenarioRiesgo.objects.select_related('activo', 'amenaza', 'vulnerabilidad').order_by('-fechaevaluacion')
    if request.session.get('usuario_rol') == 'Custodio de Activo':
        escenarios = escenarios.filter(activo__custodio_id=request.session.get('usuario_id'))
    data = [
        {
            'id': e.escenarioid,
            'etiqueta': f"{e.activo.nombre} | {e.amenaza.nombre} x {e.vulnerabilidad.nombre} (Riesgo: {e.riesgototal})",
            'riesgo_total': float(e.riesgototal),
            'va_activo': float(e.activo.valoractivo),
        }
        for e in escenarios
    ]
    return JsonResponse({'escenarios': data})


@rol_requerido('Administrador', 'Arquitecto de Seguridad')
@require_http_methods(["POST"])
def api_riesgos_evaluar(request):
    try:
        body = json.loads(request.body)
        activo = get_object_or_404(Activo, pk=int(body.get('activo_id')))
        amenaza = get_object_or_404(Amenaza, pk=int(body.get('amenaza_id')))
        vulnerabilidad = get_object_or_404(Vulnerabilidad, pk=int(body.get('vulnerabilidad_id')))

        probabilidad = int(body.get('probabilidad'))
        impacto_operativo = int(body.get('impacto_operativo'))
        impacto_spdp = int(body.get('impacto_spdp'))
        impacto_financiero = int(body.get('impacto_financiero'))

        if not all(1 <= v <= 3 for v in (probabilidad, impacto_operativo, impacto_spdp, impacto_financiero)):
            return JsonResponse({'success': False, 'message': 'Probabilidad e impactos deben estar entre 1 y 3.'}, status=400)

        impacto_base, impacto_final_dec, riesgo_total_dec, piso_aplicado = calcular_impacto_y_riesgo(
            activo.valoractivo, probabilidad, impacto_operativo, impacto_spdp, impacto_financiero
        )
        fecha_limite = calcular_fecha_limite(riesgo_total_dec)

        escenario = EscenarioRiesgo.objects.create(
            activo=activo,
            amenaza=amenaza,
            vulnerabilidad=vulnerabilidad,
            probabilidad=probabilidad,
            impactooperativo=impacto_operativo,
            impactospdp=impacto_spdp,
            impactofinanciero=impacto_financiero,
            impactobase=impacto_base,
            impactofinal=impacto_final_dec,
            riesgototal=riesgo_total_dec,
            fechalimitetratamiento=fecha_limite,
        )
        registrar_auditoria(
            request,
            'EscenariosRiesgo',
            escenario.escenarioid,
            'CREAR',
            f'Riesgo evaluado sobre "{activo.nombre}" ({amenaza.nombre} x {vulnerabilidad.nombre}), nivel {nivel_de_riesgo(riesgo_total_dec)}.',
        )
        mensaje_piso = (
            'Se aplicó el Factor Suelo: el activo tiene VA >= 2.5, por lo que el impacto SPDP se elevó automáticamente a Alto (3).'
            if piso_aplicado else None
        )
        return JsonResponse({
            'success': True,
            'escenario_id': escenario.escenarioid,
            'impacto_base': impacto_base,
            'impacto_final': float(impacto_final_dec),
            'riesgo_total': float(riesgo_total_dec),
            'nivel_riesgo': nivel_de_riesgo(riesgo_total_dec),
            'fecha_limite_tratamiento': fecha_limite.strftime('%Y-%m-%d'),
            'piso_aplicado': piso_aplicado,
            'mensaje_piso': mensaje_piso,
        })
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Formato de solicitud inválido (JSON).'}, status=400)
    except (ValueError, TypeError, KeyError):
        return JsonResponse({'success': False, 'message': 'Datos inválidos. Verifique los campos enviados.'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error inesperado: {str(e)}'}, status=500)


def procesar_evaluacion_riesgo(request, escenario_id):
    """Recalcula un escenario existente para mantenimiento interno."""
    escenario = get_object_or_404(EscenarioRiesgo, pk=escenario_id)
    impacto_base, impacto_final_dec, riesgo_total_dec, piso_aplicado = calcular_impacto_y_riesgo(
        escenario.activo.valoractivo,
        escenario.probabilidad,
        escenario.impactooperativo,
        escenario.impactospdp,
        escenario.impactofinanciero,
    )
    escenario.impactobase = impacto_base
    escenario.impactofinal = impacto_final_dec
    escenario.riesgototal = riesgo_total_dec
    if not escenario.fechalimitetratamiento:
        escenario.fechalimitetratamiento = calcular_fecha_limite(riesgo_total_dec)
    escenario.save()
    return JsonResponse({
        'status': 'success',
        'mensaje': 'Cálculo de riesgo procesado exitosamente.',
        'data': {
            'impacto_base': impacto_base,
            'impacto_final': str(impacto_final_dec),
            'riesgo_total': str(riesgo_total_dec),
            'piso_aplicado': piso_aplicado,
        },
    })


# ============================================================
# API - DASHBOARD Y KPIs
# ============================================================

@login_requerido
def api_dashboard_datos(request):
    escenarios = EscenarioRiesgo.objects.select_related('activo', 'amenaza', 'vulnerabilidad')
    if request.session.get('usuario_rol') == 'Custodio de Activo':
        escenarios = escenarios.filter(activo__custodio_id=request.session.get('usuario_id'))
    escenarios = escenarios.prefetch_related(
        Prefetch('tratamiento_set', queryset=Tratamiento.objects.order_by('-fechatratamiento'), to_attr='tratamientos_ordenados')
    ).order_by('-fechaevaluacion')

    ahora = timezone.now()
    riesgos = []
    for esc in escenarios:
        ultimo = esc.tratamientos_ordenados[0] if esc.tratamientos_ordenados else None
        riesgo_actual = float(ultimo.riesgoresidual) if ultimo else float(esc.riesgototal)
        fecha_limite = esc.fechalimitetratamiento or (ultimo.fechalimitecierre if ultimo else None)
        vencido = False
        if fecha_limite:
            vencido = (ultimo.fechatratamiento > fecha_limite) if ultimo else (fecha_limite < ahora)
        dias_restantes = (fecha_limite - ahora).days if (fecha_limite and not ultimo) else None
        riesgos.append({
            'escenario_id': esc.escenarioid,
            'activo_nombre': esc.activo.nombre,
            'amenaza': esc.amenaza.nombre,
            'vulnerabilidad': esc.vulnerabilidad.nombre,
            'va': float(esc.activo.valoractivo),
            'probabilidad': esc.probabilidad,
            'impacto_final': float(esc.impactofinal),
            'riesgo_inherente': float(esc.riesgototal),
            'estado_tratamiento': ultimo.opciontratamiento if ultimo else 'Sin Tratamiento',
            'control_aplicado': ultimo.controlaplicado if ultimo else None,
            'eficacia_control': float(ultimo.eficaciacontrol) if ultimo else None,
            'riesgo_actual': riesgo_actual,
            'puntaje_total': riesgo_actual,
            'fecha_deteccion': esc.fechaevaluacion.strftime('%Y-%m-%d'),
            'fecha_limite_tratamiento': fecha_limite.strftime('%Y-%m-%d') if fecha_limite else None,
            'dias_restantes': dias_restantes,
            'vencido': vencido,
        })
    return JsonResponse({'riesgos': riesgos})


@login_requerido
def api_dashboard_kpis(request):
    escenarios = EscenarioRiesgo.objects.select_related('activo').prefetch_related(
        Prefetch('tratamiento_set', queryset=Tratamiento.objects.order_by('-fechatratamiento'), to_attr='tratamientos_ordenados')
    )
    if request.session.get('usuario_rol') == 'Custodio de Activo':
        escenarios = escenarios.filter(activo__custodio_id=request.session.get('usuario_id'))

    ahora = timezone.now()
    zonas = {'Muy Bajo': 0, 'Bajo': 0, 'Medio': 0, 'Alto': 0, 'Critico': 0}
    por_categoria = {}
    dias_por_nivel = {k: [] for k in zonas}
    matriz_calor = {f'{p}-{i}': 0 for p in (1, 2, 3) for i in (1, 2, 3)}
    criticos_totales = criticos_sin_control = vencidos = en_plazo = total = 0
    suma_riesgo = 0.0

    for esc in escenarios:
        matriz_calor[f'{esc.probabilidad}-{esc.impactobase}'] = matriz_calor.get(f'{esc.probabilidad}-{esc.impactobase}', 0) + 1
        ultimo = esc.tratamientos_ordenados[0] if esc.tratamientos_ordenados else None
        riesgo_actual = float(ultimo.riesgoresidual) if ultimo else float(esc.riesgototal)
        suma_riesgo += riesgo_actual
        total += 1
        nivel = nivel_de_riesgo(riesgo_actual)
        zonas[nivel] += 1
        if nivel == 'Critico':
            criticos_totales += 1
            if not ultimo:
                criticos_sin_control += 1
        categoria = esc.activo.categoria
        por_categoria[categoria] = round(por_categoria.get(categoria, 0.0) + riesgo_actual, 3)

        fecha_limite = esc.fechalimitetratamiento or (ultimo.fechalimitecierre if ultimo else None)
        if not ultimo and fecha_limite:
            if fecha_limite < ahora:
                vencidos += 1
            else:
                en_plazo += 1
        if ultimo:
            dias_mitigacion = (ultimo.fechatratamiento - esc.fechaevaluacion).total_seconds() / 86400
            dias_por_nivel.setdefault(nivel_de_riesgo(esc.riesgototal), []).append(dias_mitigacion)

    metas_mttm_dias = {'Critico': 7, 'Alto': 15, 'Medio': 30, 'Bajo': 90, 'Muy Bajo': 180}
    mttm_por_nivel = {}
    todos_los_dias = []
    for nivel, lista_dias in dias_por_nivel.items():
        promedio = round(sum(lista_dias) / len(lista_dias), 2) if lista_dias else None
        todos_los_dias.extend(lista_dias)
        meta = metas_mttm_dias.get(nivel)
        mttm_por_nivel[nivel] = {
            'promedio_dias': promedio,
            'meta_dias': meta,
            'cumple_meta': promedio is not None and meta is not None and promedio <= meta,
            'muestras': len(lista_dias),
        }

    return JsonResponse({
        'distribucion_zonas': zonas,
        'riesgo_por_categoria': por_categoria,
        'irrp': round(suma_riesgo / total, 3) if total else 0.0,
        'pct_criticos_sin_control': round((criticos_sin_control / criticos_totales * 100), 1) if criticos_totales else 0.0,
        'sla': {'vencidos': vencidos, 'en_plazo': en_plazo},
        'matriz_calor': matriz_calor,
        'mttm': {
            'global_dias': round(sum(todos_los_dias) / len(todos_los_dias), 2) if todos_los_dias else None,
            'por_nivel': mttm_por_nivel,
        },
        'total_escenarios': total,
    })


# ============================================================
# API - TRATAMIENTO, COMUNICACIÓN, REPORTES Y AUDITORÍA
# ============================================================

@rol_requerido('Administrador', 'Arquitecto de Seguridad')
@require_http_methods(["POST"])
def api_tratamientos_registrar(request):
    try:
        body = json.loads(request.body)
        escenario = get_object_or_404(EscenarioRiesgo, pk=int(body.get('escenario_id')))
        opcion = (body.get('opcion_tratamiento') or '').strip()
        if opcion not in ('Mitigar', 'Transferir', 'Evitar', 'Aceptar'):
            return JsonResponse({'success': False, 'message': 'Opción de tratamiento inválida.'}, status=400)

        if opcion == 'Aceptar' and (float(escenario.activo.valoractivo) >= 2.5 or float(escenario.riesgototal) >= 5.0):
            return JsonResponse({
                'success': False,
                'message': 'No se puede aceptar este riesgo: es Alto/Crítico o pertenece a un activo con Valor >= 2.5.',
            }, status=400)

        control = (body.get('control_aplicado') or '').strip()
        if not control:
            return JsonResponse({'success': False, 'message': 'Debe describir el control aplicado.'}, status=400)
        eficacia = Decimal(str(body.get('eficacia_control')))
        if not (Decimal('0.00') <= eficacia <= Decimal('1.00')):
            return JsonResponse({'success': False, 'message': 'La eficacia del control debe estar entre 0.00 y 1.00.'}, status=400)

        tratamiento = Tratamiento.objects.create(
            escenario=escenario,
            opciontratamiento=opcion,
            controlaplicado=control,
            eficaciacontrol=eficacia,
            fechalimitecierre=escenario.fechalimitetratamiento,
        )
        tratamiento.refresh_from_db()
        registrar_auditoria(request, 'Tratamientos', tratamiento.tratamientoid, 'CREAR', f'Tratamiento "{opcion}" aplicado al escenario #{escenario.escenarioid}.')
        return JsonResponse({'success': True, 'tratamiento_id': tratamiento.tratamientoid, 'riesgo_residual': float(tratamiento.riesgoresidual)})
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Formato de solicitud inválido (JSON).'}, status=400)
    except (ValueError, TypeError, KeyError, InvalidOperation):
        return JsonResponse({'success': False, 'message': 'Datos inválidos. Verifique los campos enviados.'}, status=400)
    except Exception as e:
        mensaje = str(e)
        if 'ACEPTAR' in mensaje.upper():
            return JsonResponse({'success': False, 'message': 'La base de datos rechazó la operación: no se puede aceptar un riesgo Alto/Crítico.'}, status=400)
        return JsonResponse({'success': False, 'message': f'Error inesperado: {mensaje}'}, status=500)


@rol_requerido('Administrador', 'Arquitecto de Seguridad', 'Custodio de Activo')
@require_http_methods(["POST"])
def api_comunicaciones_registrar(request):
    try:
        body = json.loads(request.body)
        escenario = get_object_or_404(EscenarioRiesgo, pk=int(body.get('escenario_id')))
        if request.session.get('usuario_rol') == 'Custodio de Activo' and escenario.activo.custodio_id != request.session.get('usuario_id'):
            return JsonResponse({'success': False, 'message': 'Solo puede registrar comunicaciones sobre sus propios activos.'}, status=403)
        tipo = (body.get('tipo') or '').strip()
        if tipo not in ('Observacion', 'Recomendacion'):
            return JsonResponse({'success': False, 'message': 'Tipo inválido. Use Observacion o Recomendacion.'}, status=400)
        contenido = (body.get('contenido') or '').strip()
        if not contenido:
            return JsonResponse({'success': False, 'message': 'El contenido no puede estar vacío.'}, status=400)
        comunicacion = Comunicacion.objects.create(
            escenario=escenario,
            usuario_id=request.session.get('usuario_id'),
            tipo=tipo,
            contenido=contenido,
        )
        registrar_auditoria(request, 'Comunicaciones', comunicacion.comunicacionid, 'CREAR', f'{tipo} registrada sobre escenario #{escenario.escenarioid}.')
        return JsonResponse({'success': True, 'comunicacion_id': comunicacion.comunicacionid})
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Formato de solicitud inválido (JSON).'}, status=400)
    except (ValueError, TypeError, KeyError):
        return JsonResponse({'success': False, 'message': 'Datos inválidos. Verifique los campos enviados.'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error inesperado: {str(e)}'}, status=500)


@login_requerido
def api_comunicaciones_lista(request):
    comunicaciones = Comunicacion.objects.select_related('escenario__activo', 'usuario').order_by('-fechacomunicacion')
    if request.session.get('usuario_rol') == 'Custodio de Activo':
        comunicaciones = comunicaciones.filter(escenario__activo__custodio_id=request.session.get('usuario_id'))
    escenario_id = request.GET.get('escenario_id')
    if escenario_id:
        comunicaciones = comunicaciones.filter(escenario_id=escenario_id)
    data = [
        {
            'id': c.comunicacionid,
            'escenario_id': c.escenario_id,
            'tipo': c.tipo,
            'contenido': c.contenido,
            'usuario': c.usuario.nombre if c.usuario else 'Anónimo',
            'fecha': c.fechacomunicacion.strftime('%Y-%m-%d %H:%M'),
        }
        for c in comunicaciones
    ]
    return JsonResponse({'comunicaciones': data})


@rol_requerido('Administrador', 'Arquitecto de Seguridad', 'Auditor')
def api_reporte_csv(request):
    with connection.cursor() as cursor:
        cursor.execute('SELECT * FROM mercpd.vw_DashboardRiesgos ORDER BY RiesgoActual DESC')
        columnas = [col[0] for col in cursor.description]
        filas = cursor.fetchall()
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="reporte_riesgos_kushki.csv"'
    writer = csv.writer(response)
    writer.writerow(columnas)
    writer.writerows(filas)
    return response


@rol_requerido('Administrador', 'Auditor')
def api_auditoria_lista(request):
    registros = AuditoriaCambio.objects.select_related('usuario').order_by('-fechaaccion')[:200]
    data = [
        {
            'id': r.auditoriaid,
            'tabla': r.tablaafectada,
            'registro_id': r.registroid,
            'accion': r.accion,
            'usuario': r.usuario.nombre if r.usuario else 'Sistema',
            'detalle': r.detalle,
            'fecha': r.fechaaccion.strftime('%Y-%m-%d %H:%M'),
        }
        for r in registros
    ]
    return JsonResponse({'auditoria': data})
