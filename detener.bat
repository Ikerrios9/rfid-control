@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo   Deteniendo Sistema RFID
echo ============================================================

echo.
echo [1/2] Cerrando lector RFID en Windows (si esta corriendo)...
taskkill /FI "WINDOWTITLE eq lector_windows*" /T /F >NUL 2>&1
for /f "tokens=2" %%p in ('wmic process where "name='python.exe' and CommandLine like '%%lector_windows.py%%'" get ProcessId /value 2^>NUL ^| find "="') do (
    taskkill /PID %%p /F >NUL 2>&1
)
echo    Lector detenido.

echo.
echo [2/2] Bajando contenedores Docker (db + app)...
docker compose down
if errorlevel 1 (
    echo.
    echo ERROR: docker compose down fallo. Revisa que Docker Desktop este corriendo.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   Sistema RFID detenido correctamente.
echo ============================================================
echo.
pause
endlocal
