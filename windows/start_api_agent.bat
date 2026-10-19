@echo off
setlocal
set "agent_name=%~1"
if "%agent_name%"=="" set /p agent_name="Configured API agent name: "
if "%agent_name%"=="" exit /b 1
call "%~dp0start_cli_agent.bat" "%agent_name%"
exit /b %ERRORLEVEL%
