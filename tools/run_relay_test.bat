@echo off
setlocal

if "%~1"=="" goto :usage
if "%~2"=="" goto :usage

set "HOST=%~1"
set "PORT=%~2"
set "PROTOCOL=%~3"
set "LOCAL_PORT=%~4"
set "TIMEOUT=%~5"
set "RETRIES=%~6"
set "HOPS=%~7"
set "INNER=%~8"
set "DEVICE=%~9"
shift
shift
shift
shift
shift
shift
shift
shift
shift
set "COUNT=%~1"
set "RAW_INNER=%~2"

if "%PROTOCOL%"=="" set "PROTOCOL=tcp"
if "%LOCAL_PORT%"=="" set "LOCAL_PORT=0"
if "%TIMEOUT%"=="" set "TIMEOUT=5"
if "%RETRIES%"=="" set "RETRIES=0"
if "%HOPS%"=="" set "HOPS=1:1"
if "%INNER%"=="" set "INNER=cpu-status"
if "%DEVICE%"=="" set "DEVICE=D0000"
if "%COUNT%"=="" set "COUNT=1"

if /I "%INNER%"=="raw" (
  python -m tools.relay_test ^
    --host %HOST% ^
    --port %PORT% ^
    --protocol %PROTOCOL% ^
    --local-port %LOCAL_PORT% ^
    --timeout %TIMEOUT% ^
    --retries %RETRIES% ^
    --hops "%HOPS%" ^
    --inner %INNER% ^
    --raw-inner "%RAW_INNER%"
) else (
  python -m tools.relay_test ^
    --host %HOST% ^
    --port %PORT% ^
    --protocol %PROTOCOL% ^
    --local-port %LOCAL_PORT% ^
    --timeout %TIMEOUT% ^
    --retries %RETRIES% ^
    --hops "%HOPS%" ^
    --inner %INNER% ^
    --device %DEVICE% ^
    --count %COUNT%
)

exit /b %errorlevel%

:usage
echo Usage:
echo   tools\run_relay_test.bat ^<HOST^> ^<PORT^> [PROTOCOL] [LOCAL_PORT] [TIMEOUT] [RETRIES] [HOPS] [INNER] [DEVICE] [COUNT] [RAW_INNER]
echo.
echo CPU status example ^(UDP^):
echo   tools\run_relay_test.bat 192.168.250.101 1027 udp 12000 5 2 1:1 cpu-status
echo.
echo Word read example ^(UDP^):
echo   tools\run_relay_test.bat 192.168.250.101 1027 udp 12000 5 2 1:1 word-read D0000 1
echo.
echo Raw inner example ^(UDP^):
echo   tools\run_relay_test.bat 192.168.250.101 1027 udp 12000 5 2 1:1 raw D0000 1 "00 00 03 00 32 11 00"
exit /b 2
