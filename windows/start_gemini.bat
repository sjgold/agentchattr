@echo off
call "%~dp0start_cli_agent.bat" gemini %*
exit /b %ERRORLEVEL%
