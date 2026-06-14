@echo off
setlocal EnableDelayedExpansion
set PUBLISH_DIR=.\publish
set "PYTHONPATH=%CD%;%PYTHONPATH%"

echo ===================================================
echo [CI] Starting Python checks and CLI EXE build...
echo ===================================================

echo [1/6] Running Ruff (lint)...
python -m ruff check toyopuc tests scripts samples
if %errorlevel% neq 0 (
    echo [ERROR] Ruff check failed.
    exit /b %errorlevel%
)

echo [2/6] Running Ruff (format check)...
python -m ruff format --check toyopuc tests scripts samples
if %errorlevel% neq 0 (
    echo [ERROR] Code is not formatted.
    exit /b %errorlevel%
)

echo [3/6] Running Mypy...
python -m mypy toyopuc
if %errorlevel% neq 0 (
    echo [ERROR] Mypy type check failed.
    exit /b %errorlevel%
)

echo [4/6] Compiling scripts and samples...
for %%F in (scripts\*.py samples\*.py) do (
    python -m py_compile "%%F"
    if !errorlevel! neq 0 (
        echo [ERROR] Python compile check failed for %%F.
        exit /b !errorlevel!
    )
)

echo [5/6] Running tests...
python -m pytest tests
if %errorlevel% neq 0 (
    echo [ERROR] Tests failed.
    exit /b %errorlevel%
)

echo [6/6] Building CLI tool with PyInstaller...
python -m PyInstaller --onefile --noconfirm --distpath "%PUBLISH_DIR%" --name toyopuc scripts/interactive_cli.py
if %errorlevel% neq 0 (
    echo [ERROR] PyInstaller build failed.
    exit /b %errorlevel%
)

echo ===================================================
echo [SUCCESS] CI passed and CLI EXE published to:
echo %cd%\publish
echo ===================================================
