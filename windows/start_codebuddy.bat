@echo off
call "%~dp0start_cli_agent.bat" codebuddy %*
exit /b %ERRORLEVEL%
