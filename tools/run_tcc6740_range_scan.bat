@echo off
setlocal

if "%~1"=="" goto :usage
if "%~2"=="" goto :usage

set "HOST=%~1"
set "PORT=%~2"
set "PROTOCOL=%~3"
set "LOCAL_PORT=%~4"
set "COARSE_STEP=%~5"
set "STOP_AFTER_NG=%~6"
set "TARGETS=%~7"

set "DEFAULT_TARGETS=P,K,V,T,C,L,X,Y,M,S,N,R,D,P1-P,P1-K,P1-V,P1-T,P1-C,P1-L,P1-X,P1-Y,P1-M,P1-S,P1-N,P1-R,P1-D,P2-P,P2-K,P2-V,P2-T,P2-C,P2-L,P2-X,P2-Y,P2-M,P2-S,P2-N,P2-R,P2-D,P3-P,P3-K,P3-V,P3-T,P3-C,P3-L,P3-X,P3-Y,P3-M,P3-S,P3-N,P3-R,P3-D,EP,EK,EV,ET,EC,EL,EX,EY,EM,GX,GY,GM,ES,EN,H,U"

if "%PROTOCOL%"=="" set "PROTOCOL=tcp"
if "%LOCAL_PORT%"=="" set "LOCAL_PORT=0"
if "%COARSE_STEP%"=="" set "COARSE_STEP=16"
if "%STOP_AFTER_NG%"=="" set "STOP_AFTER_NG=32"
if "%TARGETS%"=="" set "TARGETS=%DEFAULT_TARGETS%"

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "STAMP=%%i"
set "LOGDIR=logs\tcc6740_range_scan_%STAMP%"
set "COARSE_LOG=%LOGDIR%\coarse.log"
set "FINE_LOG=%LOGDIR%\fine.log"
set "SUMMARY=%LOGDIR%\summary.txt"

if not exist logs mkdir logs
mkdir "%LOGDIR%"

echo.
echo Host           : %HOST%
echo Port           : %PORT%
echo Protocol       : %PROTOCOL%
echo Local UDP Port : %LOCAL_PORT%
echo Coarse Step    : %COARSE_STEP%
echo Stop After NG  : %STOP_AFTER_NG%
echo Targets        : %TARGETS%
echo Log Dir        : %LOGDIR%
echo.

(
echo TCC-6740 Range Scan Summary
echo ===========================
echo Host           : %HOST%
echo Port           : %PORT%
echo Protocol       : %PROTOCOL%
echo Local UDP Port : %LOCAL_PORT%
echo Coarse Step    : %COARSE_STEP%
echo Stop After NG  : %STOP_AFTER_NG%
echo Targets        : %TARGETS%
echo Log Dir        : %LOGDIR%
echo.
) > "%SUMMARY%"

echo [1/2] Coarse forward scan
echo [1/2] Coarse forward scan>> "%SUMMARY%"
echo Command: python -m tools.exhaustive_writable_scan --host %HOST% --port %PORT% --protocol %PROTOCOL% --local-port %LOCAL_PORT% --targets %TARGETS% --step %COARSE_STEP% --refine-boundary --stop-after-ng %STOP_AFTER_NG% --log "%COARSE_LOG%">> "%SUMMARY%"
python -m tools.exhaustive_writable_scan --host %HOST% --port %PORT% --protocol %PROTOCOL% --local-port %LOCAL_PORT% --targets %TARGETS% --step %COARSE_STEP% --refine-boundary --stop-after-ng %STOP_AFTER_NG% --log "%COARSE_LOG%"
if errorlevel 1 goto :failed

echo.>> "%SUMMARY%"
type "%COARSE_LOG%" >> "%SUMMARY%"
echo.>> "%SUMMARY%"

echo [2/2] Fine forward scan
echo [2/2] Fine forward scan>> "%SUMMARY%"
echo Command: python -m tools.exhaustive_writable_scan --host %HOST% --port %PORT% --protocol %PROTOCOL% --local-port %LOCAL_PORT% --targets %TARGETS% --step 1 --stop-after-ng %STOP_AFTER_NG% --log "%FINE_LOG%">> "%SUMMARY%"
python -m tools.exhaustive_writable_scan --host %HOST% --port %PORT% --protocol %PROTOCOL% --local-port %LOCAL_PORT% --targets %TARGETS% --step 1 --stop-after-ng %STOP_AFTER_NG% --log "%FINE_LOG%"
if errorlevel 1 goto :failed

echo.>> "%SUMMARY%"
type "%FINE_LOG%" >> "%SUMMARY%"

echo.
echo TCC-6740 range scan completed successfully.
echo Logs: %LOGDIR%
echo Summary: %SUMMARY%
goto :eof

:failed
echo.
echo TCC-6740 range scan failed. Check logs under %LOGDIR%.
exit /b 1

:usage
echo Usage:
echo   tools\run_tcc6740_range_scan.bat ^<HOST^> ^<PORT^> [PROTOCOL] [LOCAL_PORT] [COARSE_STEP] [STOP_AFTER_NG] [TARGETS]
echo.
echo Example ^(TCP^):
echo   tools\run_tcc6740_range_scan.bat 192.168.250.101 1025 tcp 0 16 32
echo.
echo Example ^(UDP^):
echo   tools\run_tcc6740_range_scan.bat 192.168.250.101 1027 udp 12000 16 32
exit /b 2
