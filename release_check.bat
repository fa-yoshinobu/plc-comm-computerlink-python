@echo off
setlocal

echo ===================================================
echo [RELEASE] Toyopuc Python release check
echo ===================================================

echo [1/2] Checking registry version...
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\check_registry_duplicate.ps1 -Registry pypi -Package toyopuc-computerlink -VersionSource pyproject -ManifestPath pyproject.toml
if %errorlevel% neq 0 (
    echo [ERROR] Release version check failed.
    exit /b %errorlevel%
)

echo [2/2] Running CI...
call run_ci.bat
if %errorlevel% neq 0 (
    echo [ERROR] CI failed.
    exit /b %errorlevel%
)

echo ===================================================
echo [SUCCESS] Release check passed.
echo ===================================================
endlocal
