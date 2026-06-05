@echo off
setlocal

call :kill_port 5173 "DND frontend"
call :kill_port 8766 "DND backend"

echo.
echo Done.
exit /b 0

:kill_port
set "PORT=%~1"
set "LABEL=%~2"
set "FOUND="

for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%PORT% .*LISTENING"') do (
    set "FOUND=1"
    echo Stopping %LABEL% on port %PORT% ^(PID %%P^)...
    taskkill /PID %%P /T /F >nul 2>nul
    if errorlevel 1 (
        echo Failed to stop PID %%P.
    ) else (
        echo Stopped PID %%P.
    )
)

if not defined FOUND (
    echo No %LABEL% process found on port %PORT%.
)

exit /b 0
