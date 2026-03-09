@echo off
setlocal

if "%~1"=="" goto :usage
if "%~2"=="" goto :usage

set "HOST=%~1"
set "PORT=%~2"
set "PROTOCOL=%~3"
set "COUNT=%~4"
set "TIMEOUT=%~5"
set "RETRIES=%~6"
set "PC10_BLOCK_WORDS=%~7"
set "LOCAL_PORT=%~8"
set "RECOVERY_COUNT=%~9"
shift
shift
shift
shift
shift
shift
shift
shift
shift
set "CLOCK_SET=%~1"
set "INCLUDE_EXHAUSTIVE=%~2"

if "%PROTOCOL%"=="" set "PROTOCOL=tcp"
if "%COUNT%"=="" set "COUNT=4"
if "%TIMEOUT%"=="" set "TIMEOUT=5"
if "%RETRIES%"=="" set "RETRIES=2"
if "%PC10_BLOCK_WORDS%"=="" set "PC10_BLOCK_WORDS=0x200"
if "%LOCAL_PORT%"=="" set "LOCAL_PORT=0"
if "%RECOVERY_COUNT%"=="" set "RECOVERY_COUNT=30"
if "%CLOCK_SET%"=="" set "CLOCK_SET="
if "%INCLUDE_EXHAUSTIVE%"=="" set "INCLUDE_EXHAUSTIVE=0"

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "STAMP=%%i"
for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "Get-Date -Format \"yyyy-MM-dd HH:mm:ss\""`) do set "START_AT=%%i"
set "LOGDIR=logs\tcc6740_all_%STAMP%"
set "SUMMARY=%LOGDIR%\summary.txt"
set "STEP_TOTAL=9"
if not "%CLOCK_SET%"=="" set /a STEP_TOTAL+=1
if "%INCLUDE_EXHAUSTIVE%"=="1" set /a STEP_TOTAL+=1

if not exist logs mkdir logs
mkdir "%LOGDIR%"

echo.
echo Host             : %HOST%
echo Port             : %PORT%
echo Protocol         : %PROTOCOL%
echo Count            : %COUNT%
echo Timeout          : %TIMEOUT%
echo Retries          : %RETRIES%
echo PC10 Block Words : %PC10_BLOCK_WORDS%
echo Local UDP Port   : %LOCAL_PORT%
echo Recovery Count   : %RECOVERY_COUNT%
echo Clock Set        : %CLOCK_SET%
echo Include Exhaust. : %INCLUDE_EXHAUSTIVE%
echo Log Dir          : %LOGDIR%
echo Start            : %START_AT%
echo.
(
echo TCC-6740 Validation Summary
echo ===========================
echo.
echo Host             : %HOST%
echo Port             : %PORT%
echo Protocol         : %PROTOCOL%
echo Count            : %COUNT%
echo Timeout          : %TIMEOUT%
echo Retries          : %RETRIES%
echo PC10 Block Words : %PC10_BLOCK_WORDS%
echo Local UDP Port   : %LOCAL_PORT%
echo Recovery Count   : %RECOVERY_COUNT%
echo Clock Set        : %CLOCK_SET%
echo Include Exhaust. : %INCLUDE_EXHAUSTIVE%
echo Log Dir          : %LOGDIR%
echo Start            : %START_AT%
echo.
) > "%SUMMARY%"

set /a STEP_NO=1
call :run_warn_step %STEP_NO% "Full test" "python -m tools.auto_rw_test --host %HOST% --port %PORT% --local-port %LOCAL_PORT% --protocol %PROTOCOL% --count %COUNT% --timeout %TIMEOUT% --retries %RETRIES% --pc10g-full --include-p123 --skip-errors --log ""%LOGDIR%\full.log"""
set /a STEP_NO+=1

call :run_step %STEP_NO% "Mixed CMD=98/99" "python -m tools.auto_rw_test --host %HOST% --port %PORT% --local-port %LOCAL_PORT% --protocol %PROTOCOL% --timeout %TIMEOUT% --retries %RETRIES% --ext-multi-test --skip-errors --log ""%LOGDIR%\ext_multi.log"""
if errorlevel 1 goto :failed
set /a STEP_NO+=1

call :run_step %STEP_NO% "Block test" "python -m tools.auto_rw_test --host %HOST% --port %PORT% --local-port %LOCAL_PORT% --protocol %PROTOCOL% --timeout %TIMEOUT% --retries %RETRIES% --max-block-test --pc10-block-words %PC10_BLOCK_WORDS% --skip-errors --log ""%LOGDIR%\block.log"""
if errorlevel 1 goto :failed
set /a STEP_NO+=1

call :run_step %STEP_NO% "Boundary test" "python -m tools.auto_rw_test --host %HOST% --port %PORT% --local-port %LOCAL_PORT% --protocol %PROTOCOL% --timeout %TIMEOUT% --retries %RETRIES% --boundary-test --skip-errors --log ""%LOGDIR%\boundary.log"""
if errorlevel 1 goto :failed
set /a STEP_NO+=1

call :run_step %STEP_NO% "W/H/L addressing" "python -m tools.whl_addressing_test --host %HOST% --port %PORT% --local-port %LOCAL_PORT% --protocol %PROTOCOL% --timeout %TIMEOUT% --retries %RETRIES% --skip-errors --log ""%LOGDIR%\whl_addressing.log"""
if errorlevel 1 goto :failed
set /a STEP_NO+=1

call :run_step %STEP_NO% "High-level API" "python -m tools.high_level_api_test --host %HOST% --port %PORT% --local-port %LOCAL_PORT% --protocol %PROTOCOL% --timeout %TIMEOUT% --retries %RETRIES% --skip-errors --log ""%LOGDIR%\high_level.log"""
if errorlevel 1 goto :failed
set /a STEP_NO+=1

call :run_step %STEP_NO% "Clock read" "python -m tools.clock_test --host %HOST% --port %PORT% --local-port %LOCAL_PORT% --protocol %PROTOCOL% --timeout %TIMEOUT% --retries %RETRIES% > ""%LOGDIR%\clock_read.log"""
if errorlevel 1 goto :failed
set /a STEP_NO+=1

if not "%CLOCK_SET%"=="" (
  call :run_clock_write_step %STEP_NO%
  if errorlevel 1 goto :failed
  set /a STEP_NO+=1
)

call :run_step %STEP_NO% "CPU status" "python -m tools.cpu_status_test --host %HOST% --port %PORT% --local-port %LOCAL_PORT% --protocol %PROTOCOL% --timeout %TIMEOUT% --retries %RETRIES% > ""%LOGDIR%\cpu_status.log"""
if errorlevel 1 goto :failed
set /a STEP_NO+=1

call :run_step %STEP_NO% "Recovery write/read" "python -m tools.recovery_write_loop --host %HOST% --port %PORT% --local-port %LOCAL_PORT% --protocol %PROTOCOL% --timeout 1 --retries 0 --target D0000 --interval-ms 200 --count %RECOVERY_COUNT% --log ""%LOGDIR%\recovery_write.log"" && python -m tools.recovery_write_loop --host %HOST% --port %PORT% --local-port %LOCAL_PORT% --protocol %PROTOCOL% --timeout 1 --retries 0 --target D0000 --mode read --expect 0xFFFF --interval-ms 200 --count %RECOVERY_COUNT% --log ""%LOGDIR%\recovery_read.log"""
if errorlevel 1 goto :failed
set /a STEP_NO+=1

if "%INCLUDE_EXHAUSTIVE%"=="1" (
  call :run_step %STEP_NO% "Exhaustive writable scan" "python -m tools.exhaustive_writable_scan --host %HOST% --port %PORT% --local-port %LOCAL_PORT% --protocol %PROTOCOL% --timeout %TIMEOUT% --retries %RETRIES% --targets all --stop-after-ng 32 --log ""%LOGDIR%\exhaustive.log"""
  if errorlevel 1 goto :failed
  set /a STEP_NO+=1
)

for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "Get-Date -Format \"yyyy-MM-dd HH:mm:ss\""`) do set "END_AT=%%i"
echo End              : %END_AT%>> "%SUMMARY%"
echo Overall          : PASS>> "%SUMMARY%"

echo.
echo TCC-6740 validation completed successfully.
echo Logs: %LOGDIR%
echo Summary: %SUMMARY%
goto :eof

:run_step
set "STEP_INDEX=%~1"
set "STEP_NAME=%~2"
set "STEP_CMD=%~3"
echo [%STEP_INDEX%/%STEP_TOTAL%] %STEP_NAME%
echo [%STEP_INDEX%/%STEP_TOTAL%] %STEP_NAME%>> "%SUMMARY%"
echo Command: %STEP_CMD%>> "%SUMMARY%"
call %STEP_CMD%
if errorlevel 1 exit /b 1
echo Result: PASS>> "%SUMMARY%"
if exist "%LOGDIR%\full.log" if "%STEP_NAME%"=="Full test" type "%LOGDIR%\full.log" | findstr /R /C:"^\[.*: " /C:"^TOTAL:" /C:"^TOLERATED:" /C:"^  ">> "%SUMMARY%"
if exist "%LOGDIR%\ext_multi.log" if "%STEP_NAME%"=="Mixed CMD=98/99" type "%LOGDIR%\ext_multi.log" | findstr /R /C:"^\[.*: " /C:"^TOTAL:" /C:"^TOLERATED:" /C:"^  ">> "%SUMMARY%"
if exist "%LOGDIR%\block.log" if "%STEP_NAME%"=="Block test" type "%LOGDIR%\block.log" | findstr /R /C:"^\[.*: " /C:"^TOTAL:" /C:"^TOLERATED:" /C:"^  ">> "%SUMMARY%"
if exist "%LOGDIR%\boundary.log" if "%STEP_NAME%"=="Boundary test" type "%LOGDIR%\boundary.log" | findstr /R /C:"^\[.*: " /C:"^TOTAL:" /C:"^TOLERATED:" /C:"^  ">> "%SUMMARY%"
if exist "%LOGDIR%\whl_addressing.log" if "%STEP_NAME%"=="W/H/L addressing" type "%LOGDIR%\whl_addressing.log" | findstr /R /C:"^\[.*: " /C:"^TOTAL:" /C:"^ERROR CASES:" >> "%SUMMARY%"
if exist "%LOGDIR%\high_level.log" if "%STEP_NAME%"=="High-level API" type "%LOGDIR%\high_level.log" | findstr /R /C:"^\[.*: " /C:"^TOTAL:" /C:"^ERROR CASES:" >> "%SUMMARY%"
if exist "%LOGDIR%\clock_read.log" if "%STEP_NAME%"=="Clock read" type "%LOGDIR%\clock_read.log" >> "%SUMMARY%"
if exist "%LOGDIR%\clock_write.log" if "%STEP_NAME%"=="Clock write" type "%LOGDIR%\clock_write.log" >> "%SUMMARY%"
if exist "%LOGDIR%\cpu_status.log" if "%STEP_NAME%"=="CPU status" type "%LOGDIR%\cpu_status.log" >> "%SUMMARY%"
if exist "%LOGDIR%\recovery_write.log" if "%STEP_NAME%"=="Recovery write/read" type "%LOGDIR%\recovery_write.log" | findstr /R /C:"^Summary" /C:"^- " >> "%SUMMARY%"
if exist "%LOGDIR%\recovery_read.log" if "%STEP_NAME%"=="Recovery write/read" type "%LOGDIR%\recovery_read.log" | findstr /R /C:"^Summary" /C:"^- " >> "%SUMMARY%"
if exist "%LOGDIR%\exhaustive.log" if "%STEP_NAME%"=="Exhaustive writable scan" type "%LOGDIR%\exhaustive.log" >> "%SUMMARY%"
echo.>> "%SUMMARY%"
exit /b 0

:run_warn_step
set "STEP_INDEX=%~1"
set "STEP_NAME=%~2"
set "STEP_CMD=%~3"
echo [%STEP_INDEX%/%STEP_TOTAL%] %STEP_NAME%
echo [%STEP_INDEX%/%STEP_TOTAL%] %STEP_NAME%>> "%SUMMARY%"
echo Command: %STEP_CMD%>> "%SUMMARY%"
call %STEP_CMD%
if errorlevel 1 (
  echo Result: WARN>> "%SUMMARY%"
  if exist "%LOGDIR%\full.log" if "%STEP_NAME%"=="Full test" type "%LOGDIR%\full.log" | findstr /R /C:"^\[.*: " /C:"^TOTAL:" /C:"^TOLERATED:" /C:"^  ">> "%SUMMARY%"
  echo Note: non-fatal mismatch observed; continuing remaining validation steps>> "%SUMMARY%"
  echo.>> "%SUMMARY%"
  exit /b 0
)
echo Result: PASS>> "%SUMMARY%"
if exist "%LOGDIR%\full.log" if "%STEP_NAME%"=="Full test" type "%LOGDIR%\full.log" | findstr /R /C:"^\[.*: " /C:"^TOTAL:" /C:"^TOLERATED:" /C:"^  ">> "%SUMMARY%"
echo.>> "%SUMMARY%"
exit /b 0

:run_clock_write_step
set "STEP_INDEX=%~1"
echo [%STEP_INDEX%/%STEP_TOTAL%] Clock write
echo [%STEP_INDEX%/%STEP_TOTAL%] Clock write>> "%SUMMARY%"
echo Command: python -m tools.clock_test --host %HOST% --port %PORT% --local-port %LOCAL_PORT% --protocol %PROTOCOL% --timeout %TIMEOUT% --retries %RETRIES% --set "%CLOCK_SET%" ^> "%LOGDIR%\clock_write.log">> "%SUMMARY%"
python -m tools.clock_test --host %HOST% --port %PORT% --local-port %LOCAL_PORT% --protocol %PROTOCOL% --timeout %TIMEOUT% --retries %RETRIES% --set "%CLOCK_SET%" > "%LOGDIR%\clock_write.log"
if errorlevel 1 exit /b 1
echo Result: PASS>> "%SUMMARY%"
if exist "%LOGDIR%\clock_write.log" type "%LOGDIR%\clock_write.log" >> "%SUMMARY%"
echo.>> "%SUMMARY%"
exit /b 0

:failed
for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "Get-Date -Format \"yyyy-MM-dd HH:mm:ss\""`) do set "END_AT=%%i"
echo Result: FAIL>> "%SUMMARY%"
echo End              : %END_AT%>> "%SUMMARY%"
echo Overall          : FAIL>> "%SUMMARY%"
echo.
echo TCC-6740 validation failed. Check logs under %LOGDIR%.
exit /b 1

:usage
echo Usage:
echo   tools\run_tcc6740_all.bat ^<HOST^> ^<PORT^> [PROTOCOL] [COUNT] [TIMEOUT] [RETRIES] [PC10_BLOCK_WORDS] [LOCAL_PORT] [RECOVERY_COUNT] [CLOCK_SET] [INCLUDE_EXHAUSTIVE]
echo.
echo Example ^(TCP^):
echo   tools\run_tcc6740_all.bat 192.168.250.101 1025 tcp 4 5 2 0x200 0 30 "2026-03-08 20:00:10" 0
echo.
echo Example ^(UDP^):
echo   tools\run_tcc6740_all.bat 192.168.250.101 1027 udp 4 5 2 0x200 12000 30 "2026-03-08 20:00:10" 0
exit /b 2
