"""
WSGI config for kushki_mercpd_project.
"""

import os

from django.core.wsgi import get_wsgi_application

# Apunta a tus configuraciones principales
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kushki_core.settings')

# Esta es la variable que Django estaba buscando
application = get_wsgi_application()