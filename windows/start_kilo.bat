@echo off
if "%~1"=="" (
    call "%~dp0start_cli_agent.bat" kilo
) else (
    call "%~dp0start_cli_agent.bat" kilo -- -m "%~1"
)
exit /b %ERRORLEVEL%
