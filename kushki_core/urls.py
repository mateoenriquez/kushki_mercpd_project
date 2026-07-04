from django.contrib import admin
from django.urls import path
from mercpd_app import views

urlpatterns = [
    # Autenticación
    path('login/', views.vista_login, name='login'),
    path('logout/', views.vista_logout, name='logout'),

    # Panel de administración interno de Django
    path('admin/', admin.site.urls),

    # Registro de usuarios (solo Administrador)
    path('usuarios/registrar/', views.vista_registro_usuario, name='registro_usuario'),

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
    path('api/riesgos/kpis/', views.api_dashboard_kpis, name='api_dashboard_kpis'),

    # Recálculo puntual (uso interno / mantenimiento, no llamado por el frontend)
    path('api/evaluar-riesgo/<int:escenario_id>/', views.procesar_evaluacion_riesgo, name='api_evaluar_riesgo'),

    # Pantallas 4 y 5 (Frontend)
    path('tratamientos/', views.vista_tratamiento_riesgo, name='tratamientos'),
    path('comunicacion/', views.vista_comunicacion_reportes, name='comunicacion'),

    # Catálogo de escenarios (usado por Pantallas 4 y 5)
    path('api/escenarios/lista/', views.api_escenarios_lista, name='api_escenarios_lista'),

    # Tratamiento del riesgo (Pantalla 4)
    path('api/tratamientos/registrar/', views.api_tratamientos_registrar, name='api_tratamientos_registrar'),

    # Comunicación, consulta y reportes (Pantalla 5)
    path('api/comunicaciones/registrar/', views.api_comunicaciones_registrar, name='api_comunicaciones_registrar'),
    path('api/comunicaciones/lista/', views.api_comunicaciones_lista, name='api_comunicaciones_lista'),
    path('api/reportes/csv/', views.api_reporte_csv, name='api_reporte_csv'),
]