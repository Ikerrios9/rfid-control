@echo off
setlocal
cd /d "%~dp0\.."

echo ============================================================
echo   Iniciando Sistema RFID
echo ============================================================

echo.
echo [1/4] Levantando Docker (db + app)...
docker compose up -d
if errorlevel 1 (
    echo.
    echo ERROR: docker compose fallo. Revisa que Docker Desktop este corriendo.
    pause
    exit /b 1
)

echo.
echo [2/4] Esperando a que la API responda en http://localhost:8000 ...
set /a tries=0
:wait_api
set /a tries+=1
for /f %%c in ('curl -s -o NUL -w "%%{http_code}" http://localhost:8000/login 2^>NUL') do set STATUS=%%c
if "%STATUS%"=="200" goto api_ready
if "%STATUS%"=="301" goto api_ready
if "%STATUS%"=="302" goto api_ready
if "%STATUS%"=="303" goto api_ready
if "%STATUS%"=="401" goto api_ready
if %tries% GEQ 30 (
    echo.
    echo ADVERTENCIA: La API no respondio tras 30 intentos. Continuando igualmente.
    goto api_ready
)
timeout /t 1 /nobreak >NUL
goto wait_api

:api_ready
echo    API lista (HTTP %STATUS%).

echo.
echo [3/4] Abriendo navegador...
rem  Ventana principal (panel / login) en el navegador por defecto
start "" "http://localhost:8000/"
rem  Pantalla de bienvenida en una VENTANA NUEVA (intenta Edge, luego Chrome, luego default)
start "" msedge --new-window "http://localhost:8000/display" 2>NUL
if errorlevel 1 start "" chrome --new-window "http://localhost:8000/display" 2>NUL
if errorlevel 1 start "" "http://localhost:8000/display"

echo.
echo [4/4] Iniciando lector RFID en Windows...
echo ============================================================
python lectores\lector_windows.py

endlocal
