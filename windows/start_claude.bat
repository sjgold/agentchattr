@echo off
call "%~dp0start_cli_agent.bat" claude %*
exit /b %ERRORLEVEL%
