import csv
import json
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.db import connection
from django.db.models import Prefetch
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from functools import wraps
from django.shortcuts import redirect
from django.contrib.auth.hashers import make_password, check_password

from .models import (
    Activo, Amenaza, Vulnerabilidad, EscenarioRiesgo, Usuario,
    Tratamiento, Comunicacion,
)

# ============================================================
# AUTENTICACIÓN BASADA EN SESIONES (tabla mercpd.Usuarios)
# ============================================================

def login_requerido(vista_func):
    """
    Decorador que protege vistas de plantilla y endpoints de API.
    Verifica que exista una sesión activa (usuario_id en session).
    Si no la hay, redirige a /login/ (vistas HTML) o devuelve 401 (APIs).
    """
    @wraps(vista_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('usuario_id'):
            if request.path.startswith('/api/'):
                return JsonResponse({'success': False, 'message': 'Sesión no válida. Inicie sesión nuevamente.'}, status=401)
            return redirect(f"/login/?next={request.path}")
        return vista_func(request, *args, **kwargs)
    return wrapper

def rol_requerido(*roles_permitidos):
    """
    Decorador que exige, además de sesión activa, que el rol del usuario
    logueado esté dentro de roles_permitidos. Replica a nivel de aplicación
    el principio de menor privilegio ya aplicado con GRANT/DENY en SQL Server.
    """
    def decorador(vista_func):
        @wraps(vista_func)
        def wrapper(request, *args, **kwargs):
            if not request.session.get('usuario_id'):
                if request.path.startswith('/api/'):
                    return JsonResponse({'success': False, 'message': 'Sesión no válida.'}, status=401)
                return redirect(f"/login/?next={request.path}")

            if request.session.get('usuario_rol') not in roles_permitidos:
                if request.path.startswith('/api/'):
                    return JsonResponse({'success': False, 'message': 'No tiene permisos suficientes para esta acción.'}, status=403)
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
        return redirect(next_url)

    return render(request, 'mercpd_app/login.html')


def vista_logout(request):
    """Cierra la sesión activa."""
    request.session.flush()
    return redirect('/login/')

# ============================================================
# REGLAS DE NEGOCIO MERC-PD
# ============================================================

def calcular_valor_activo(c, i, d):
    """
    Regla de Negocio 1: Valor del Activo
    Fórmula: VA = (C * 0.4) + (I * 0.35) + (D * 0.25)
    """
    va = (c * 0.4) + (i * 0.35) + (d * 0.25)
    return Decimal(str(va)).quantize(Decimal('0.001'))


def calcular_impacto_y_riesgo(va, probabilidad, impacto_operativo, impacto_spdp, impacto_financiero):
    """
    Reglas de Negocio 2, 3 y 4, alineadas con la metodología MERC-PD (Tarea 8):

    - Factor Suelo / Piso de Criticidad (Sección 3.4, regla 1): si el activo
      tiene VA >= 2.5 (Muy Alto/Crítico), el impacto de Protección de Datos
      (SPDP) no puede quedar por debajo de 3 (Alto). Cualquier incidente que
      toque un activo tan crítico arrastra automáticamente ese nivel de
      exposición regulatoria, sin importar lo capturado por el evaluador.
    - Impacto Base = max(Operativo, SPDP [con piso aplicado], Financiero)
    - Impacto Final = Impacto Base * (VA / 3.0)
    - Riesgo Total = Probabilidad * Impacto Final

    Devuelve además `piso_aplicado` para informar al usuario en el frontend.
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
    Tiempos de respuesta obligatorios por nivel (Sección 6.3 de la
    metodología): Bajo -> 90 días, Medio -> 30 días, Alto -> 15 días,
    Crítico -> 7 días (corrección definitiva tras la contención de 0-24h).
    """
    riesgo_total = float(riesgo_total)
    if riesgo_total >= 7.5:
        dias = 7
    elif riesgo_total >= 5.0:
        dias = 15
    elif riesgo_total >= 3.0:
        dias = 30
    else:
        dias = 90
    return timezone.now() + timedelta(days=dias)


def nivel_de_riesgo(puntaje):
    """Traduce un puntaje numérico al nivel cualitativo (Sección 6.2)."""
    puntaje = float(puntaje)
    if puntaje >= 7.5:
        return 'Critico'
    if puntaje >= 5.0:
        return 'Alto'
    if puntaje >= 3.0:
        return 'Medio'
    return 'Bajo'


# ============================================================
# VISTAS DEL FRONTEND (RENDERIZADO DE PLANTILLAS HTML)
# ============================================================

@login_requerido
def vista_dashboard_principal(request):
    """Renderiza la Pantalla 3: El Dashboard del Semáforo"""
    return render(request, 'mercpd_app/dashboard.html')

@rol_requerido('Administrador', 'Arquitecto de Seguridad')
def vista_registro_activos(request):
    """Renderiza la Pantalla 1: Ingreso de Activos"""
    return render(request, 'mercpd_app/activos.html')

@rol_requerido('Administrador', 'Arquitecto de Seguridad')
def vista_identificacion_riesgos(request):
    """Renderiza la Pantalla 2: Cruce de Amenazas y Vulnerabilidades"""
    return render(request, 'mercpd_app/identificador_riesgos.html')

@rol_requerido('Administrador', 'Arquitecto de Seguridad')
def vista_tratamiento_riesgo(request):
    """Renderiza la Pantalla 4: Tratamiento del Riesgo"""
    return render(request, 'mercpd_app/tratamientos.html')

@login_requerido
def vista_comunicacion_reportes(request):
    """Renderiza la Pantalla 5: Comunicación y Reportes"""
    return render(request, 'mercpd_app/comunicacion.html')


# ============================================================
# API - PANTALLA 1: REGISTRO Y VALORACIÓN DE ACTIVOS
# ============================================================

@login_requerido
def api_activos_lista(request):
    """
    Devuelve el listado de activos. Si el usuario logueado es Custodio de
    Activo, se filtra para que solo vea los activos donde él es el custodio
    asignado (CustodioID) — esto es el "filtrado real" pedido, no solo
    ocultar botones en el frontend.
    """
    activos = Activo.objects.all().order_by('nombre')

    if request.session.get('usuario_rol') == 'Custodio de Activo':
        activos = activos.filter(custodio_id=request.session.get('usuario_id'))

    data = [
        {'id': a.activoid, 'nombre': a.nombre, 'va': float(a.valoractivo)}
        for a in activos
    ]
    return JsonResponse({'activos': data})


@login_requerido
def api_usuarios_lista(request):
    """
    Devuelve el catálogo de usuarios registrados en el sistema, usado para
    poblar el <select> de Custodio en la Pantalla 1 (Registro de Activos).
    Requiere sesión activa: expone nombres y roles del personal, por lo que
    no debe quedar público (hallazgo de seguridad corregido en Fase 4).
    """
    usuarios = Usuario.objects.all().order_by('nombre')
    data = [
        {'id': u.usuarioid, 'nombre': u.nombre, 'rol': u.rol}
        for u in usuarios
    ]
    return JsonResponse({'usuarios': data})


@login_requerido
def api_amenazas_lista(request):
    """
    Devuelve el catálogo REAL de amenazas (sembrado en la Fase 1 en SQL Server),
    usado para poblar el <select> de Amenaza en la Pantalla 2.
    """
    amenazas = Amenaza.objects.all().order_by('tipo', 'nombre')
    data = [
        {'id': a.amenazaid, 'nombre': a.nombre, 'tipo': a.tipo}
        for a in amenazas
    ]
    return JsonResponse({'amenazas': data})


@login_requerido
def api_vulnerabilidades_lista(request):
    """
    Devuelve el catálogo REAL de vulnerabilidades (sembrado en la Fase 1 en SQL Server),
    usado para poblar el <select> de Vulnerabilidad en la Pantalla 2.
    """
    vulnerabilidades = Vulnerabilidad.objects.all().order_by('tipo', 'nombre')
    data = [
        {'id': v.vulnerabilidadid, 'nombre': v.nombre, 'tipo': v.tipo}
        for v in vulnerabilidades
    ]
    return JsonResponse({'vulnerabilidades': data})


@rol_requerido('Administrador', 'Arquitecto de Seguridad')
@require_http_methods(["POST"])
def api_activos_registrar(request):
    """
    Registra un nuevo activo aplicando la Regla de Negocio 1 (Valor del Activo).
    """
    try:
        body = json.loads(request.body)

        nombre = (body.get('nombre') or '').strip()
        tipo = (body.get('tipo') or '').strip()

        if not nombre or not tipo:
            return JsonResponse({'success': False, 'message': 'Nombre y tipo de activo son obligatorios.'})

        c = int(body.get('confidencialidad'))
        i = int(body.get('integridad'))
        d = int(body.get('disponibilidad'))

        if not all(1 <= v <= 3 for v in (c, i, d)):
            return JsonResponse({'success': False, 'message': 'Los valores C, I, D deben estar entre 1 y 3.'})

        va = calcular_valor_activo(c, i, d)

        # Custodio es opcional: si no se selecciona, queda en NULL
        custodio_id_raw = body.get('custodio_id')
        custodio_id = int(custodio_id_raw) if custodio_id_raw else None
        if custodio_id is not None:
            get_object_or_404(Usuario, pk=custodio_id)  # valida que exista

        activo = Activo.objects.create(
            nombre=nombre,
            categoria=tipo,
            confidencialidad=c,
            integridad=i,
            disponibilidad=d,
            valoractivo=va,
            custodio_id=custodio_id,
        )

        return JsonResponse({
            'success': True,
            'va': float(va),
            'activo_id': activo.activoid,
            'critico': va >= Decimal('2.5'),
        })

    except (ValueError, TypeError, KeyError):
        return JsonResponse({'success': False, 'message': 'Datos inválidos. Verifique los campos enviados.'}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Formato de solicitud inválido (JSON).'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error inesperado: {str(e)}'}, status=500)


@login_requerido
def api_escenarios_lista(request):
    """
    Devuelve el listado de escenarios de riesgo ya evaluados, usado para
    poblar el <select> de Escenario en las Pantallas 4 (Tratamiento) y
    5 (Comunicación). Protegido con sesión: incluye puntajes de riesgo.
    """
    escenarios = EscenarioRiesgo.objects.select_related(
        'activo', 'amenaza', 'vulnerabilidad'
    ).order_by('-fechaevaluacion')

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


# ============================================================
# API - PANTALLA 2: IDENTIFICACIÓN DE RIESGOS
# ============================================================

@rol_requerido('Administrador', 'Arquitecto de Seguridad')
@require_http_methods(["POST"])
def api_riesgos_evaluar(request):
    """
    Registra un escenario de riesgo (Amenaza x Vulnerabilidad sobre un Activo)
    y aplica las Reglas de Negocio 2, 3 y 4 de la metodología MERC-PD,
    incluyendo el Factor Suelo (Sección 3.4) y el cálculo de la fecha límite
    de tratamiento (Sección 6.3).
    """
    try:
        body = json.loads(request.body)

        activo_id = int(body.get('activo_id'))
        activo = get_object_or_404(Activo, pk=activo_id)

        amenaza_id = int(body.get('amenaza_id'))
        vulnerabilidad_id = int(body.get('vulnerabilidad_id'))

        amenaza = get_object_or_404(Amenaza, pk=amenaza_id)
        vulnerabilidad = get_object_or_404(Vulnerabilidad, pk=vulnerabilidad_id)

        probabilidad = int(body.get('probabilidad'))
        impacto_operativo = int(body.get('impacto_operativo'))
        impacto_spdp = int(body.get('impacto_spdp'))
        impacto_financiero = int(body.get('impacto_financiero'))

        campos_1_3 = (probabilidad, impacto_operativo, impacto_spdp, impacto_financiero)
        if not all(1 <= v <= 3 for v in campos_1_3):
            return JsonResponse({'success': False, 'message': 'Probabilidad e impactos deben estar entre 1 y 3.'})

        impacto_base, impacto_final_dec, riesgo_total_dec, piso_aplicado = calcular_impacto_y_riesgo(
            va=activo.valoractivo,
            probabilidad=probabilidad,
            impacto_operativo=impacto_operativo,
            impacto_spdp=impacto_spdp,
            impacto_financiero=impacto_financiero,
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

        mensaje_piso = (
            'Se aplicó el Factor Suelo: el activo tiene VA >= 2.5, por lo que el '
            'impacto de Protección de Datos (SPDP) se elevó automáticamente a Alto (3).'
        ) if piso_aplicado else None

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

    except (ValueError, TypeError, KeyError):
        return JsonResponse({'success': False, 'message': 'Datos inválidos. Verifique los campos enviados.'}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Formato de solicitud inválido (JSON).'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error inesperado: {str(e)}'}, status=500)


# ============================================================
# API - PANTALLA 3: DASHBOARD DE MONITOREO (SEMÁFORO)
# ============================================================

@login_requerido
def api_dashboard_datos(request):
    """
    Alimenta el Dashboard. Si el usuario es Custodio de Activo, el semáforo
    se limita a sus propios activos (filtrado real, no visual). Incluye
    fecha de detección, fecha límite y estado de SLA (Sección 6.3).
    """
    escenarios = EscenarioRiesgo.objects.select_related(
        'activo', 'amenaza', 'vulnerabilidad'
    )

    if request.session.get('usuario_rol') == 'Custodio de Activo':
        escenarios = escenarios.filter(activo__custodio_id=request.session.get('usuario_id'))

    escenarios = escenarios.prefetch_related(
        Prefetch(
            'tratamiento_set',
            queryset=Tratamiento.objects.order_by('-fechatratamiento'),
            to_attr='tratamientos_ordenados',
        )
    ).order_by('-fechaevaluacion')

    ahora = timezone.now()
    riesgos = []
    for esc in escenarios:
        ultimo_tratamiento = esc.tratamientos_ordenados[0] if esc.tratamientos_ordenados else None
        riesgo_actual = float(ultimo_tratamiento.riesgoresidual) if ultimo_tratamiento else float(esc.riesgototal)

        vencido = bool(
            not ultimo_tratamiento and esc.fechalimitetratamiento and esc.fechalimitetratamiento < ahora
        )
        dias_restantes = None
        if not ultimo_tratamiento and esc.fechalimitetratamiento:
            dias_restantes = (esc.fechalimitetratamiento - ahora).days

        riesgos.append({
            'escenario_id': esc.escenarioid,
            'activo_nombre': esc.activo.nombre,
            'amenaza': esc.amenaza.nombre,
            'vulnerabilidad': esc.vulnerabilidad.nombre,
            'va': float(esc.activo.valoractivo),
            'probabilidad': esc.probabilidad,
            'impacto_final': float(esc.impactofinal),
            'riesgo_inherente': float(esc.riesgototal),
            'estado_tratamiento': ultimo_tratamiento.opciontratamiento if ultimo_tratamiento else 'Sin Tratamiento',
            'riesgo_actual': riesgo_actual,
            'puntaje_total': riesgo_actual,
            'fecha_deteccion': esc.fechaevaluacion.strftime('%Y-%m-%d'),
            'fecha_limite_tratamiento': esc.fechalimitetratamiento.strftime('%Y-%m-%d') if esc.fechalimitetratamiento else None,
            'dias_restantes': dias_restantes,
            'vencido': vencido,
        })

    return JsonResponse({'riesgos': riesgos})


@login_requerido
def api_dashboard_kpis(request):
    """
    Alimenta los gráficos del dashboard con los KPIs de monitoreo continuo
    de la metodología MERC-PD (Sección 7.3): distribución de riesgos por
    zona del semáforo, riesgo acumulado por categoría de activo, Índice de
    Riesgo Residual Promedio (IRRP), % de riesgos críticos sin control y
    cumplimiento de SLA (escenarios vencidos vs. en plazo).
    """
    escenarios = EscenarioRiesgo.objects.select_related('activo').prefetch_related(
        Prefetch('tratamiento_set', queryset=Tratamiento.objects.order_by('-fechatratamiento'), to_attr='tratamientos_ordenados')
    )

    if request.session.get('usuario_rol') == 'Custodio de Activo':
        escenarios = escenarios.filter(activo__custodio_id=request.session.get('usuario_id'))

    ahora = timezone.now()
    zonas = {'Bajo': 0, 'Medio': 0, 'Alto': 0, 'Critico': 0}
    por_categoria = {}
    criticos_totales = 0
    criticos_sin_control = 0
    vencidos = 0
    en_plazo = 0
    suma_riesgo = 0.0
    total = 0

    for esc in escenarios:
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

        cat = esc.activo.categoria
        por_categoria[cat] = round(por_categoria.get(cat, 0.0) + riesgo_actual, 3)

        if not ultimo and esc.fechalimitetratamiento:
            if esc.fechalimitetratamiento < ahora:
                vencidos += 1
            else:
                en_plazo += 1

    irrp = round(suma_riesgo / total, 3) if total else 0.0
    pct_criticos_sin_control = round((criticos_sin_control / criticos_totales * 100), 1) if criticos_totales else 0.0

    return JsonResponse({
        'distribucion_zonas': zonas,
        'riesgo_por_categoria': por_categoria,
        'irrp': irrp,
        'pct_criticos_sin_control': pct_criticos_sin_control,
        'sla': {'vencidos': vencidos, 'en_plazo': en_plazo},
        'total_escenarios': total,
    })


# ============================================================
# API - MANTENIMIENTO / RECÁLCULO PUNTUAL (uso interno / admin)
# ============================================================

@rol_requerido('Administrador')
def vista_registro_usuario(request):
    """
    Pantalla de registro de nuevos usuarios del sistema.
    Acceso exclusivo para el rol Administrador (máximo privilegio).
    """
    if request.method == 'POST':
        nombre = (request.POST.get('nombre') or '').strip()
        email = (request.POST.get('email') or '').strip()
        rol = (request.POST.get('rol') or '').strip()
        password = request.POST.get('password') or ''

        if not all([nombre, email, rol, password]):
            return render(request, 'mercpd_app/registro_usuario.html', {'error': 'Todos los campos son obligatorios.'})

        if rol not in ('Administrador', 'Arquitecto de Seguridad', 'Custodio de Activo', 'Auditor'):
            return render(request, 'mercpd_app/registro_usuario.html', {'error': 'Rol inválido.'})

        if Usuario.objects.filter(email=email).exists():
            return render(request, 'mercpd_app/registro_usuario.html', {'error': 'Ya existe un usuario con ese correo.'})

        Usuario.objects.create(
            nombre=nombre,
            email=email,
            rol=rol,
            passwordhash=make_password(password),
        )
        return render(request, 'mercpd_app/registro_usuario.html', {'success': f'Usuario "{nombre}" creado exitosamente.'})

    return render(request, 'mercpd_app/registro_usuario.html')

def procesar_evaluacion_riesgo(request, escenario_id):
    """
    Recalcula y persiste Impacto Base, Impacto Final y Riesgo Total
    para un escenario ya existente (por ejemplo, tras corregir manualmente
    algún dato en SSMS). No es llamado por el flujo normal del frontend.
    """
    escenario = get_object_or_404(EscenarioRiesgo, pk=escenario_id)
    activo = escenario.activo

    impacto_base, impacto_final_dec, riesgo_total_dec, piso_aplicado = calcular_impacto_y_riesgo(
        va=activo.valoractivo,
        probabilidad=escenario.probabilidad,
        impacto_operativo=escenario.impactooperativo,
        impacto_spdp=escenario.impactospdp,
        impacto_financiero=escenario.impactofinanciero,
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
        }
    })

# ============================================================
# API - PANTALLA 4: TRATAMIENTO DEL RIESGO
# ============================================================

@rol_requerido('Administrador', 'Arquitecto de Seguridad')
@require_http_methods(["POST"])
def api_tratamientos_registrar(request):
    """
    Registra un tratamiento de riesgo (Aspecto 3: Tratamiento del riesgo),
    tomando como referencia las opciones de respuesta de ISO/IEC 27002:2022
    (Mitigar, Transferir, Evitar, Aceptar).

    Regla de "Priorización automática de controles" (Sección 3.4.3 y Regla
    de aplicación 6.2 de la metodología MERC-PD): no se permite 'Aceptar'
    un riesgo Alto/Crítico (>=5.0) ni un riesgo sobre un activo con
    VA >= 2.5. El trigger trg_ValidarAceptacionRiesgo en SQL Server actúa
    como respaldo si alguien intenta saltarse esta validación por fuera
    de la aplicación.

    El Riesgo Residual (Aspecto 4) lo recalcula automáticamente el trigger
    trg_ActualizarRiesgoResidual en SQL Server justo después del INSERT;
    aquí solo se refresca el objeto para devolver el valor ya calculado
    por la base de datos (fuente única de verdad del cálculo).
    """
    try:
        body = json.loads(request.body)

        escenario_id = int(body.get('escenario_id'))
        escenario = get_object_or_404(EscenarioRiesgo, pk=escenario_id)

        opcion = (body.get('opcion_tratamiento') or '').strip()
        opciones_validas = ('Mitigar', 'Transferir', 'Evitar', 'Aceptar')
        if opcion not in opciones_validas:
            return JsonResponse({'success': False, 'message': f'Opción inválida. Use una de: {", ".join(opciones_validas)}.'})

        va_activo = float(escenario.activo.valoractivo)
        riesgo_actual = float(escenario.riesgototal)
        if opcion == 'Aceptar' and (va_activo >= 2.5 or riesgo_actual >= 5.0):
            return JsonResponse({
                'success': False,
                'message': (
                    'No se puede ACEPTAR este riesgo: es Alto/Crítico o pertenece a un activo '
                    'con Valor >= 2.5 (metodología MERC-PD, Secciones 3.4.3 y 6.2). '
                    'Seleccione Mitigar, Transferir o Evitar.'
                ),
            })

        control = (body.get('control_aplicado') or '').strip()
        if not control:
            return JsonResponse({'success': False, 'message': 'Debe describir el control aplicado.'})

        eficacia = Decimal(str(body.get('eficacia_control')))
        if not (Decimal('0.00') <= eficacia <= Decimal('1.00')):
            return JsonResponse({'success': False, 'message': 'La eficacia del control debe estar entre 0.00 y 1.00.'})

        tratamiento = Tratamiento.objects.create(
            escenario=escenario,
            opciontratamiento=opcion,
            controlaplicado=control,
            eficaciacontrol=eficacia,
            fechalimitecierre=escenario.fechalimitetratamiento,
        )
        tratamiento.refresh_from_db()  # trae el RiesgoResidual calculado por el trigger

        return JsonResponse({
            'success': True,
            'tratamiento_id': tratamiento.tratamientoid,
            'riesgo_residual': float(tratamiento.riesgoresidual),
        })

    except (ValueError, TypeError, KeyError, InvalidOperation):
        return JsonResponse({'success': False, 'message': 'Datos inválidos. Verifique los campos enviados.'}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Formato de solicitud inválido (JSON).'}, status=400)
    except Exception as e:
        mensaje = str(e)
        # El trigger trg_ValidarAceptacionRiesgo de SQL Server puede rechazar
        # el INSERT como respaldo; se traduce a un mensaje claro para el usuario.
        if 'ACEPTAR' in mensaje.upper():
            return JsonResponse({'success': False, 'message': 'La base de datos rechazó la operación: no se puede aceptar un riesgo Alto/Crítico.'}, status=400)
        return JsonResponse({'success': False, 'message': f'Error inesperado: {mensaje}'}, status=500)


# ============================================================
# API - PANTALLA 5: COMUNICACIÓN, CONSULTA Y REPORTES
# ============================================================

@rol_requerido('Administrador', 'Arquitecto de Seguridad', 'Custodio de Activo')
@require_http_methods(["POST"])
def api_comunicaciones_registrar(request):
    try:
        body = json.loads(request.body)

        escenario_id = int(body.get('escenario_id'))
        escenario = get_object_or_404(EscenarioRiesgo, pk=escenario_id)

        # Un Custodio solo puede comentar escenarios de SUS activos
        if request.session.get('usuario_rol') == 'Custodio de Activo':
            if escenario.activo.custodio_id != request.session.get('usuario_id'):
                return JsonResponse({'success': False, 'message': 'Solo puede registrar comunicaciones sobre sus propios activos.'}, status=403)

        tipo = (body.get('tipo') or '').strip()
        if tipo not in ('Observacion', 'Recomendacion'):
            return JsonResponse({'success': False, 'message': 'Tipo inválido. Use Observacion o Recomendacion.'})

        contenido = (body.get('contenido') or '').strip()
        if not contenido:
            return JsonResponse({'success': False, 'message': 'El contenido no puede estar vacío.'})

        comunicacion = Comunicacion.objects.create(
            escenario=escenario,
            usuario_id=request.session.get('usuario_id'),
            tipo=tipo,
            contenido=contenido,
        )

        return JsonResponse({'success': True, 'comunicacion_id': comunicacion.comunicacionid})

    except (ValueError, TypeError, KeyError):
        return JsonResponse({'success': False, 'message': 'Datos inválidos. Verifique los campos enviados.'}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Formato de solicitud inválido (JSON).'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error inesperado: {str(e)}'}, status=500)


@login_requerido
def api_comunicaciones_lista(request):
    # nota: select_related directo a activo no aplica aquí; se filtra vía escenario__activo
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
    """
    Genera un reporte descargable (CSV) para partes interesadas, leyendo
    directamente la vista consolidada mercpd.vw_DashboardRiesgos creada
    en la Fase 1 (Aspecto 5: opción de generar reportes).
    """
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM mercpd.vw_DashboardRiesgos ORDER BY RiesgoActual DESC")
        columnas = [col[0] for col in cursor.description]
        filas = cursor.fetchall()

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="reporte_riesgos_kushki.csv"'

    writer = csv.writer(response)
    writer.writerow(columnas)
    writer.writerows(filas)

    return response