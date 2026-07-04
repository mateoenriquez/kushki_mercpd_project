import csv
import json
from decimal import Decimal, InvalidOperation

from django.db import connection
from django.db.models import Prefetch
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
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
    Reglas de Negocio 2, 3 y 4:
    - Impacto Base = max(Operativo, SPDP, Financiero)
    - Impacto Final = Impacto Base * (VA / 3.0)
    - Riesgo Total = Probabilidad * Impacto Final
    """
    impacto_base = max(impacto_operativo, impacto_spdp, impacto_financiero)

    impacto_final = impacto_base * (float(va) / 3.0)
    impacto_final_dec = Decimal(str(impacto_final)).quantize(Decimal('0.001'))

    riesgo_total = probabilidad * float(impacto_final_dec)
    riesgo_total_dec = Decimal(str(riesgo_total)).quantize(Decimal('0.001'))

    return impacto_base, impacto_final_dec, riesgo_total_dec


# ============================================================
# VISTAS DEL FRONTEND (RENDERIZADO DE PLANTILLAS HTML)
# ============================================================

@login_requerido
def vista_dashboard_principal(request):
    """Renderiza la Pantalla 3: El Dashboard del Semáforo"""
    return render(request, 'mercpd_app/dashboard.html')

@login_requerido
def vista_registro_activos(request):
    """Renderiza la Pantalla 1: Ingreso de Activos"""
    return render(request, 'mercpd_app/activos.html')

@login_requerido
def vista_identificacion_riesgos(request):
    """Renderiza la Pantalla 2: Cruce de Amenazas y Vulnerabilidades"""
    return render(request, 'mercpd_app/identificador_riesgos.html')

@login_requerido
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

def api_activos_lista(request):
    """
    Devuelve el listado de activos registrados, usado para poblar
    el <select> de la Pantalla 2 (Identificación de Riesgos).
    """
    activos = Activo.objects.all().order_by('nombre')
    data = [
        {
            'id': a.activoid,
            'nombre': a.nombre,
            'va': float(a.valoractivo),
        }
        for a in activos
    ]
    return JsonResponse({'activos': data})


def api_usuarios_lista(request):
    """
    Devuelve el catálogo de usuarios registrados en el sistema, usado para
    poblar el <select> de Custodio en la Pantalla 1 (Registro de Activos).
    """
    usuarios = Usuario.objects.all().order_by('nombre')
    data = [
        {'id': u.usuarioid, 'nombre': u.nombre, 'rol': u.rol}
        for u in usuarios
    ]
    return JsonResponse({'usuarios': data})


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


@login_requerido
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
        })

    except (ValueError, TypeError, KeyError):
        return JsonResponse({'success': False, 'message': 'Datos inválidos. Verifique los campos enviados.'}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Formato de solicitud inválido (JSON).'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error inesperado: {str(e)}'}, status=500)
    

def api_escenarios_lista(request):
    """
    Devuelve el listado de escenarios de riesgo ya evaluados, usado para
    poblar el <select> de Escenario en las Pantallas 4 (Tratamiento) y
    5 (Comunicación).
    """
    escenarios = EscenarioRiesgo.objects.select_related(
        'activo', 'amenaza', 'vulnerabilidad'
    ).order_by('-fechaevaluacion')

    data = [
        {
            'id': e.escenarioid,
            'etiqueta': f"{e.activo.nombre} | {e.amenaza.nombre} x {e.vulnerabilidad.nombre} (Riesgo: {e.riesgototal})",
            'riesgo_total': float(e.riesgototal),
        }
        for e in escenarios
    ]
    return JsonResponse({'escenarios': data})


# ============================================================
# API - PANTALLA 2: IDENTIFICACIÓN DE RIESGOS
# ============================================================

@login_requerido
@require_http_methods(["POST"])
def api_riesgos_evaluar(request):
    """
    Registra un escenario de riesgo (Amenaza x Vulnerabilidad sobre un Activo)
    y aplica las Reglas de Negocio 2, 3 y 4 de la metodología MERC-PD.

    Amenaza y Vulnerabilidad se referencian por su ID REAL del catálogo
    (tablas Amenazas/Vulnerabilidades sembradas en la Fase 1), poblado
    dinámicamente en el frontend igual que el <select> de Activos.
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

        impacto_base, impacto_final_dec, riesgo_total_dec = calcular_impacto_y_riesgo(
            va=activo.valoractivo,
            probabilidad=probabilidad,
            impacto_operativo=impacto_operativo,
            impacto_spdp=impacto_spdp,
            impacto_financiero=impacto_financiero,
        )

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
        )

        return JsonResponse({
            'success': True,
            'escenario_id': escenario.escenarioid,
            'impacto_base': impacto_base,
            'impacto_final': float(impacto_final_dec),
            'riesgo_total': float(riesgo_total_dec),
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

def api_dashboard_datos(request):
    """
    Alimenta el Dashboard en tiempo real con datos REALES de SQL Server,
    incluyendo el estado de tratamiento y el riesgo actual (post-mitigación).
    """
    escenarios = EscenarioRiesgo.objects.select_related(
        'activo', 'amenaza', 'vulnerabilidad'
    ).prefetch_related(
        Prefetch(
            'tratamiento_set',
            queryset=Tratamiento.objects.order_by('-fechatratamiento'),
            to_attr='tratamientos_ordenados',
        )
    ).order_by('-fechaevaluacion')

    riesgos = []
    for esc in escenarios:
        ultimo_tratamiento = esc.tratamientos_ordenados[0] if esc.tratamientos_ordenados else None
        riesgo_actual = float(ultimo_tratamiento.riesgoresidual) if ultimo_tratamiento else float(esc.riesgototal)

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
            'puntaje_total': riesgo_actual,  # el semáforo ahora colorea según el riesgo ACTUAL
        })

    return JsonResponse({'riesgos': riesgos})


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

        if rol not in ('Administrador', 'Arquitecto de Seguridad'):
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

    impacto_base, impacto_final_dec, riesgo_total_dec = calcular_impacto_y_riesgo(
        va=activo.valoractivo,
        probabilidad=escenario.probabilidad,
        impacto_operativo=escenario.impactooperativo,
        impacto_spdp=escenario.impactospdp,
        impacto_financiero=escenario.impactofinanciero,
    )

    escenario.impactobase = impacto_base
    escenario.impactofinal = impacto_final_dec
    escenario.riesgototal = riesgo_total_dec
    escenario.save()

    return JsonResponse({
        'status': 'success',
        'mensaje': 'Cálculo de riesgo procesado exitosamente.',
        'data': {
            'impacto_base': impacto_base,
            'impacto_final': str(impacto_final_dec),
            'riesgo_total': str(riesgo_total_dec),
        }
    })
    
# ============================================================
# API - PANTALLA 4: TRATAMIENTO DEL RIESGO
# ============================================================

@login_requerido
@require_http_methods(["POST"])
def api_tratamientos_registrar(request):
    """
    Registra un tratamiento de riesgo (Aspecto 3: Tratamiento del riesgo),
    tomando como referencia las opciones de respuesta de ISO/IEC 27002:2022
    (Mitigar, Transferir, Evitar, Aceptar).

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
        return JsonResponse({'success': False, 'message': f'Error inesperado: {str(e)}'}, status=500)


# ============================================================
# API - PANTALLA 5: COMUNICACIÓN, CONSULTA Y REPORTES
# ============================================================

@login_requerido
@require_http_methods(["POST"])
def api_comunicaciones_registrar(request):
    """
    Registra una observación o recomendación sobre un escenario de riesgo
    (Aspecto 5: Comunicación y consulta).
    """
    try:
        body = json.loads(request.body)

        escenario_id = int(body.get('escenario_id'))
        escenario = get_object_or_404(EscenarioRiesgo, pk=escenario_id)

        tipo = (body.get('tipo') or '').strip()
        if tipo not in ('Observacion', 'Recomendacion'):
            return JsonResponse({'success': False, 'message': 'Tipo inválido. Use Observacion o Recomendacion.'})

        contenido = (body.get('contenido') or '').strip()
        if not contenido:
            return JsonResponse({'success': False, 'message': 'El contenido no puede estar vacío.'})

        usuario_id_raw = body.get('usuario_id')
        usuario_id = int(usuario_id_raw) if usuario_id_raw else None
        if usuario_id is not None:
            get_object_or_404(Usuario, pk=usuario_id)

        comunicacion = Comunicacion.objects.create(
            escenario=escenario,
            usuario_id=usuario_id,
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


def api_comunicaciones_lista(request):
    """
    Devuelve las observaciones/recomendaciones registradas, opcionalmente
    filtradas por escenario (?escenario_id=).
    """
    comunicaciones = Comunicacion.objects.select_related('escenario', 'usuario').order_by('-fechacomunicacion')

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