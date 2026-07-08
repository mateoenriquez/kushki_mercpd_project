@echo off
title ARGOS MERC-PD - Cloudflare Tunnel

echo Iniciando tunel publico hacia http://127.0.0.1:8080
echo.
echo IMPORTANTE:
echo Copia la URL HTTPS que aparezca con trycloudflare.com
echo Esa URL es la que enviaras al profesor.
echo.

C:\cloudflared\cloudflared.exe tunnel --url http://127.0.0.1:8080 --protocol http2 --edge-ip-version 4

pause