from django.contrib import admin
from django.urls import path
from mercpd_app import views

urlpatterns = [
    # Panel de administración interno de Django
    path('admin/', admin.site.urls),
    
    # Rutas para el usuario (Frontend HTML)
    path('', views.vista_dashboard_principal, name='dashboard'), # Pantalla de inicio
    path('activos/', views.vista_registro_activos, name='activos'),
    path('riesgos/', views.vista_identificacion_riesgos, name='riesgos'),
    
    # Rutas de comunicación interna para tu JavaScript (APIs de Fetch)
    path('api/riesgos/dashboard/', views.api_dashboard_datos, name='api_dashboard_datos'),
    path('api/evaluar-riesgo/<int:escenario_id>/', views.procesar_evaluacion_riesgo, name='api_evaluar_riesgo'),
]   