@echo off
cd /d "%~dp0"
where py >nul 2>&1
if errorlevel 1 (echo Instala Python 3.12 desde python.org & pause & exit /b 1)
if not exist .venv\Scripts\python.exe (
    py -3.12 -m venv .venv
    if errorlevel 1 (echo No se pudo crear entorno con Python 3.12 & pause & exit /b 1)
)
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (echo Error instalando dependencias & pause & exit /b 1)
start "" "http://127.0.0.1:5000"
.venv\Scripts\python.exe app.py
pause
