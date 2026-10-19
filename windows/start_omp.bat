@echo off
call "%~dp0start_cli_agent.bat" omp %*
exit /b %ERRORLEVEL%
