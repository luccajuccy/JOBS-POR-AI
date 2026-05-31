@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Ambiente virtual nao encontrado em .venv\Scripts\python.exe
    echo Crie a venv ou instale as dependencias antes de iniciar.
    pause
    exit /b 1
)

echo Iniciando Jobs por AI...
echo Acesse: http://localhost:5000
echo.

".venv\Scripts\python.exe" app.py

pause
