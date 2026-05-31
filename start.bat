@echo off
echo =========================================
echo Jobs por AI - Iniciando o Servidor...
echo =========================================
echo.

uvicorn app:app --host 0.0.0.0 --port 5000 --reload

pause
