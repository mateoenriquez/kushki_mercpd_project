import json
from decimal import Decimal, InvalidOperation

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from .models import Activo, Amenaza, Vulnerabilidad, EscenarioRiesgo, Usuario


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

def vista_dashboard_principal(request):
    """Renderiza la Pantalla 3: El Dashboard del Semáforo"""
    return render(request, 'mercpd_app/dashboard.html')


def vista_registro_activos(request):
    """Renderiza la Pantalla 1: Ingreso de Activos"""
    return render(request, 'mercpd_app/activos.html')


def vista_identificacion_riesgos(request):
    """Renderiza la Pantalla 2: Cruce de Amenazas y Vulnerabilidades"""
    return render(request, 'mercpd_app/identificador_riesgos.html')


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


# ============================================================
# API - PANTALLA 2: IDENTIFICACIÓN DE RIESGOS
# ============================================================

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
    Alimenta el Dashboard en tiempo real con datos REALES de SQL Server.
    Los nombres de campo coinciden exactamente con lo que consume dashboard.js
    (activo_nombre, va, probabilidad, impacto_final, puntaje_total).
    """
    escenarios = EscenarioRiesgo.objects.select_related(
        'activo', 'amenaza', 'vulnerabilidad'
    ).order_by('-fechaevaluacion')

    riesgos = []
    for esc in escenarios:
        riesgos.append({
            'escenario_id': esc.escenarioid,
            'activo_nombre': esc.activo.nombre,
            'amenaza': esc.amenaza.nombre,
            'vulnerabilidad': esc.vulnerabilidad.nombre,
            'va': float(esc.activo.valoractivo),
            'probabilidad': esc.probabilidad,
            'impacto_final': float(esc.impactofinal),
            'puntaje_total': float(esc.riesgototal),
        })

    return JsonResponse({'riesgos': riesgos})


# ============================================================
# API - MANTENIMIENTO / RECÁLCULO PUNTUAL (uso interno / admin)
# ============================================================

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