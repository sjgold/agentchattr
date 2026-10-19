@echo off
call "%~dp0start_cli_agent.bat" hermes %*
exit /b %ERRORLEVEL%
