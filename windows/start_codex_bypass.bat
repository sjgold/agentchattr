@echo off
call "%~dp0start_cli_agent.bat" codex -- --dangerously-bypass-approvals-and-sandbox %*
exit /b %ERRORLEVEL%
