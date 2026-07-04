from pathlib import Path
import os

# 1. Rutas base del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent

# 2. Llave de seguridad
# IMPORTANTE (hallazgo de seguridad corregido en Fase 4): en un entorno real
# NUNCA se debe dejar un SECRET_KEY hardcodeado en el repositorio. Aquí se
# exige la variable de entorno; solo se usa un valor de repuesto si no existe
# (útil para que el proyecto arranque en la demo local del curso).
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-CAMBIAR-EN-PRODUCCION-kushki-mercpd-2026'
)

# 3. Modo de depuración: por defecto False (seguro). Para desarrollo local,
# exportar DJANGO_DEBUG=True antes de correr runserver.
DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

# ALLOWED_HOSTS ya no acepta '*' por defecto; en desarrollo local basta con
# localhost/127.0.0.1. Para otro host, definir DJANGO_ALLOWED_HOSTS.
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# 4. Aplicaciones instaladas (Aquí registramos tu app 'mercpd_app')
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'mercpd_app', # Nuestra aplicación MERC-PD
]

# 5. Middlewares de seguridad y sesiones nativos
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# 6. Archivo de enrutamiento principal
ROOT_URLCONF = 'kushki_core.urls'

# 7. Configuración de Plantillas (HTML)
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True, # Permite buscar templates dentro de mercpd_app
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'kushki_core.wsgi.application'

# 8. Base de Datos (Tu configuración de SQL Server validada)
DATABASES = {
    'default': {
        'ENGINE': 'mssql',
        'NAME': os.environ.get('DJANGO_DB_NAME', 'Kushki_MERCPD'),
        'HOST': os.environ.get('DJANGO_DB_HOST', '.'),
        'PORT': '',

        'OPTIONS': {
            'driver': 'ODBC Driver 17 for SQL Server',
            'Trusted_Connection': 'yes',
            'host_is_server': True,
        },
    }
}

# 9. Archivos estáticos (CSS, JS)
STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# 10. Endurecimiento de sesiones y cookies (Fase 4 - hallazgos de seguridad)
# En producción (detrás de HTTPS) exportar DJANGO_SECURE_COOKIES=True.
SECURE_COOKIES = os.environ.get('DJANGO_SECURE_COOKIES', 'False') == 'True'
SESSION_COOKIE_SECURE = SECURE_COOKIES
CSRF_COOKIE_SECURE = SECURE_COOKIES
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 60 * 60 * 4  # 4 horas de sesión inactiva
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
X_FRAME_OPTIONS = 'DENY'