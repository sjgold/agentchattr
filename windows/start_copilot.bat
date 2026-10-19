@echo off
call "%~dp0start_cli_agent.bat" copilot %*
exit /b %ERRORLEVEL%
