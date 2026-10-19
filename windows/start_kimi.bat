@echo off
call "%~dp0start_cli_agent.bat" kimi %*
exit /b %ERRORLEVEL%
