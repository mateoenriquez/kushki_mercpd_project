@echo off
title ARGOS MERC-PD - Aplicacion Django

cd /d "D:\UDLA\S_Proyectos\S6_Proyectos\S.Informática\kushki_mercpd_project"

set DJANGO_SECRET_KEY=argos-mercpd-demo-2026-seguridad
set DJANGO_DEBUG=False
set DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,.trycloudflare.com
set DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:8080,http://127.0.0.1:8080,https://*.trycloudflare.com
set DJANGO_DB_NAME=Kushki_MERCPD
set DJANGO_DB_HOST=.
set DJANGO_DB_DRIVER=ODBC Driver 17 for SQL Server
set DJANGO_DB_TRUSTED_CONNECTION=yes
set DJANGO_SECURE_COOKIES=False

call venv\Scripts\activate

echo Verificando proyecto Django...
python manage.py check

echo.
echo Recolectando archivos estaticos...
python manage.py collectstatic --noinput

echo.
echo Iniciando ARGOS MERC-PD en http://127.0.0.1:8080
waitress-serve --listen=127.0.0.1:8080 kushki_core.wsgi:application

pause