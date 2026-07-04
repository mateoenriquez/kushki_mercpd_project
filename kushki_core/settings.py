from pathlib import Path

# 1. Rutas base del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent

# 2. Llave de seguridad (Requerida por Django para arrancar)
SECRET_KEY = 'django-insecure-kushki-mercpd-super-secret-key-2026'

# 3. Modo de depuración (True para desarrollo local)
DEBUG = True
ALLOWED_HOSTS = ['*']

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
        'NAME': 'Kushki_MERCPD',
        'HOST': '.',
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