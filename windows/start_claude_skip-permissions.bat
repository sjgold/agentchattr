@echo off
call "%~dp0start_cli_agent.bat" claude --dangerously-skip-permissions %*
exit /b %ERRORLEVEL%
