@echo off
title ARGOS MERC-PD - ngrok Tunnel

echo Iniciando tunel publico fijo con ngrok hacia http://127.0.0.1:8080
echo.
echo IMPORTANTE:
echo No cierres esta ventana mientras el profesor revisa.
echo.

C:\ngrok\ngrok.exe http 8080 --url https://unedited-subside-pregnant.ngrok-free.dev

pause