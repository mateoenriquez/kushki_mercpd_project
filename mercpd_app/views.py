from decimal import Decimal
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from .models import Activo, EscenarioRiesgo
from django.shortcuts import render


def calcular_valor_activo(c, i, d):
    """
    Regla de Negocio 1: Valor del Activo
    Fórmula: VA = (C * 0.4) + (I * 0.35) + (D * 0.25)
    """
    va = (c * 0.4) + (i * 0.35) + (d * 0.25)
    return Decimal(str(va)).quantize(Decimal('0.001'))

def procesar_evaluacion_riesgo(request, escenario_id):
    """
    Aplica las Reglas de Negocio 2, 3 y 4 de la metodología MERC-PD
    para un escenario específico y lo actualiza en la base de datos.
    """
    escenario = get_object_or_404(EscenarioRiesgo, pk=escenario_id)
    activo = escenario.activo
    
    # 1. Obtener VA (calculado previamente en el registro del activo)
    va = float(activo.valoractivo)
    
    # 2. Regla de Negocio 2: Impacto Base (El valor máximo entre las 3 dimensiones)
    impacto_base = max(
        escenario.impactooperativo, 
        escenario.impactospdp, 
        escenario.impactofinanciero
    )
    
    # 3. Regla de Negocio 3: Impacto Final = Impacto Base * (VA / 3.0)
    impacto_final = impacto_base * (va / 3.0)
    impacto_final_dec = Decimal(str(impacto_final)).quantize(Decimal('0.001'))
    
    # 4. Regla de Negocio 4: Riesgo = Probabilidad * Impacto Final
    riesgo_total = escenario.probabilidad * float(impacto_final_dec)
    riesgo_total_dec = Decimal(str(riesgo_total)).quantize(Decimal('0.001'))
    
    # 5. Persistir los resultados calculados en la Base de Datos
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
            'riesgo_total': str(riesgo_total_dec)
        }
    })

def vista_dashboard_datos(request):
    """
    Endpoint para alimentar el semáforo dinámico del Frontend en la Fase 3.
    Obtiene todos los escenarios y determina su color térmico.
    """
    escenarios = EscenarioRiesgo.objects.select_related('activo', 'amenaza', 'vulnerabilidad').all()
    datos = []
    
    for esc in escenarios:
        riesgo = float(esc.riesgototal)
        
        # Determinar zona de calor
        color = 'Verde'
        if riesgo >= 7.50:
            color = 'Rojo' # Crítico
        elif riesgo >= 4.50:
            color = 'Rojo' # Alto
        elif riesgo >= 2.50:
            color = 'Amarillo' # Medio
            
        datos.append({
            'escenario_id': esc.escenarioid,
            'activo': esc.activo.nombre,
            'amenaza': esc.amenaza.nombre,
            'vulnerabilidad': esc.vulnerabilidad.nombre,
            'riesgo_total': str(esc.riesgototal),
            'zona_calor': color
        })
        
    return JsonResponse({'datos': datos})

def api_dashboard_datos(request):
    """
    API que alimenta el Dashboard en tiempo real. 
    Simula la extracción de los cálculos MERC-PD de la Base de Datos.
    """
    datos_mercpd = {
        "estadisticas": {
            "total_activos": 12,
            "riesgos_criticos": 2,
            "riesgos_medios": 5,
            "riesgos_bajos": 5
        },
        "riesgos": [
            {
                "id": 1, 
                "activo": "Base de Datos de Tarjetas (Kushki)", 
                "amenaza": "Ransomware / Cifrado no autorizado", 
                "probabilidad": 3, 
                "impacto_final": 3.0, 
                "nivel": "Crítico"
            },
            {
                "id": 2, 
                "activo": "API de Transacciones", 
                "amenaza": "Ataque de Denegación de Servicio (DDoS)", 
                "probabilidad": 2, 
                "impacto_final": 2.2, 
                "nivel": "Medio"
            },
            {
                "id": 3, 
                "activo": "Laptops Corporativas", 
                "amenaza": "Pérdida o Robo de equipo", 
                "probabilidad": 1, 
                "impacto_final": 1.0, 
                "nivel": "Bajo"
            }
        ]
    }
    return JsonResponse(datos_mercpd)

# --- VISTAS DEL FRONTEND (INTERFAZ GRÁFICA) ---

def vista_dashboard_principal(request):
    """Renderiza la pantalla 3: El Dashboard del Semáforo"""
    return render(request, 'mercpd_app/dashboard.html')

def vista_registro_activos(request):
    """Renderiza la pantalla 1: Ingreso de Activos"""
    return render(request, 'mercpd_app/activos.html')

def vista_identificacion_riesgos(request):
    """Renderiza la pantalla 2: Cruce de Amenazas y Vulnerabilidades"""
    return render(request, 'mercpd_app/identificador_riesgos.html')