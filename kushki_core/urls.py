from django.contrib import admin
from django.urls import path
from mercpd_app import views

urlpatterns = [
    # Panel de administración interno de Django
    path('admin/', admin.site.urls),

    # Rutas para el usuario (Frontend HTML)
    path('', views.vista_dashboard_principal, name='dashboard'),  # Pantalla de inicio
    path('activos/', views.vista_registro_activos, name='activos'),
    path('riesgos/', views.vista_identificacion_riesgos, name='riesgos'),

    # Catálogos (usados por los <select> dinámicos del frontend)
    path('api/activos/lista/', views.api_activos_lista, name='api_activos_lista'),
    path('api/usuarios/lista/', views.api_usuarios_lista, name='api_usuarios_lista'),
    path('api/amenazas/lista/', views.api_amenazas_lista, name='api_amenazas_lista'),
    path('api/vulnerabilidades/lista/', views.api_vulnerabilidades_lista, name='api_vulnerabilidades_lista'),

    # Registro y cálculo (Pantallas 1 y 2)
    path('api/activos/registrar/', views.api_activos_registrar, name='api_activos_registrar'),
    path('api/riesgos/evaluar/', views.api_riesgos_evaluar, name='api_riesgos_evaluar'),

    # Dashboard en tiempo real (Pantalla 3)
    path('api/riesgos/dashboard/', views.api_dashboard_datos, name='api_dashboard_datos'),

    # Recálculo puntual (uso interno / mantenimiento, no llamado por el frontend)
    path('api/evaluar-riesgo/<int:escenario_id>/', views.procesar_evaluacion_riesgo, name='api_evaluar_riesgo'),
]