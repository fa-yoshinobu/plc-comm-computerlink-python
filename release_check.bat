@echo off
setlocal

echo ===================================================
echo [RELEASE] Toyopuc Python release check
echo ===================================================

echo [1/3] Checking registry version...
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\check_registry_duplicate.ps1 -Registry pypi -Package toyopuc-computerlink -VersionSource pyproject -ManifestPath pyproject.toml
if %errorlevel% neq 0 (
    echo [ERROR] Release version check failed.
    exit /b %errorlevel%
)

echo [2/3] Checking canonical ComputerLink profile fixtures...
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\update_computerlink_profile_jsons.ps1 -FailIfChanged
if %errorlevel% neq 0 (
    echo [ERROR] Canonical ComputerLink profile JSON check failed.
    exit /b %errorlevel%
)

echo [3/3] Running CI...
call run_ci.bat
if %errorlevel% neq 0 (
    echo [ERROR] CI failed.
    exit /b %errorlevel%
)

echo ===================================================
echo [SUCCESS] Release check passed.
echo ===================================================
endlocal
