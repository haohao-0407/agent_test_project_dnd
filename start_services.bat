@echo off
setlocal

set "ROOT=%~dp0"

echo Starting DND backend on http://127.0.0.1:8766
start "DND Backend API" /D "%ROOT%" cmd /k "python -m playscript_agent.api.app --host 127.0.0.1 --port 8766"

echo Starting DND frontend on http://127.0.0.1:5173
start "DND Frontend Vite" /D "%ROOT%web" cmd /k "npm run dev"

echo.
echo Services are starting in separate windows.
echo Frontend: http://127.0.0.1:5173
echo Backend:  http://127.0.0.1:8766
echo Use stop_services.bat to stop processes listening on ports 5173 and 8766.
