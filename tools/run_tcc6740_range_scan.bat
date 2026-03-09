@echo off
setlocal
echo This script was renamed. Redirecting to tools\run_device_range_scan.bat...
call "%~dp0run_device_range_scan.bat" %*
exit /b %ERRORLEVEL%
