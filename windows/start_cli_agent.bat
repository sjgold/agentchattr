@echo off
setlocal
cd /d "%~dp0.."
where python >nul 2>nul
if not errorlevel 1 (
    python launch_agent.py %*
) else (
    where py >nul 2>nul
    if errorlevel 1 (
        echo Python 3.11 or newer is required. Install Python and retry.
        pause
        exit /b 1
    )
    py -3 launch_agent.py %*
)
set "launch_code=%ERRORLEVEL%"
if not "%launch_code%"=="0" (
    echo Agent launch exited with code %launch_code%.
    pause
)
exit /b %launch_code%
