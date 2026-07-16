@echo off
setlocal

echo ===================================================
echo [RELEASE] Toyopuc Python release check
echo ===================================================

echo [1/4] Checking registry version...
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\check_registry_duplicate.ps1 -Registry pypi -Package plc-comm-toyopuc -VersionSource pyproject -ManifestPath pyproject.toml
if %errorlevel% neq 0 (
    echo [ERROR] Release version check failed.
    exit /b %errorlevel%
)

echo [2/4] Checking canonical ComputerLink profile fixtures...
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\update_computerlink_profile_jsons.ps1 -FailIfChanged
if %errorlevel% neq 0 (
    echo [ERROR] Canonical ComputerLink profile JSON check failed.
    exit /b %errorlevel%
)

echo [3/4] Checking GitHub source archive contents...
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\check_source_archive.ps1
if %errorlevel% neq 0 (
    echo [ERROR] Source archive content check failed.
    exit /b %errorlevel%
)

echo [4/4] Running CI...
call run_ci.bat
if %errorlevel% neq 0 (
    echo [ERROR] CI failed.
    exit /b %errorlevel%
)

echo ===================================================
echo [SUCCESS] Release check passed.
echo ===================================================
endlocal
