from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# Seguridad: la llave ya no tiene fallback hardcodeado en el repositorio.
# Para ejecutar localmente, definir por ejemplo:
#   set DJANGO_SECRET_KEY=valor-seguro-de-desarrollo
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    raise RuntimeError('Falta DJANGO_SECRET_KEY. Defina la variable de entorno antes de iniciar Django.')

# Seguridad: DEBUG queda desactivado por defecto. Activar solo en desarrollo local.
DEBUG = os.environ.get('DJANGO_DEBUG', 'False').lower() in ('1', 'true', 'yes', 'on')

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
    if host.strip()
]

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        'DJANGO_CSRF_TRUSTED_ORIGINS',
        'http://localhost:8080,http://127.0.0.1:8080,https://*.trycloudflare.com'
    ).split(',')
    if origin.strip()
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'mercpd_app.apps.MercpdAppConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'kushki_core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
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

DATABASES = {
    'default': {
        'ENGINE': 'mssql',
        'NAME': os.environ.get('DJANGO_DB_NAME', 'Kushki_MERCPD'),
        'HOST': os.environ.get('DJANGO_DB_HOST', '.'),
        'PORT': os.environ.get('DJANGO_DB_PORT', ''),
        'OPTIONS': {
            'driver': os.environ.get('DJANGO_DB_DRIVER', 'ODBC Driver 17 for SQL Server'),
            'Trusted_Connection': os.environ.get('DJANGO_DB_TRUSTED_CONNECTION', 'yes'),
            'host_is_server': True,
        },
    }
}

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SECURE_COOKIES = os.environ.get('DJANGO_SECURE_COOKIES', 'False').lower() in ('1', 'true', 'yes', 'on')
SESSION_COOKIE_SECURE = SECURE_COOKIES
CSRF_COOKIE_SECURE = SECURE_COOKIES
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False
SESSION_COOKIE_AGE = 60 * 60 * 4
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
X_FRAME_OPTIONS = 'DENY'

# Cabeceras seguras recomendadas para despliegue HTTPS.
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
