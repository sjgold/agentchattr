@echo off
call "%~dp0start_cli_agent.bat" minimax %*
exit /b %ERRORLEVEL%
