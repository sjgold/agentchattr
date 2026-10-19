@echo off
call "%~dp0start_cli_agent.bat" codex %*
exit /b %ERRORLEVEL%
