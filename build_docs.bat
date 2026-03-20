@echo off
echo [DOCS] Building Toyopuc Python Docs with MkDocs...
set PYTHONPATH=src
python -m mkdocs build
if %errorlevel% neq 0 (
    echo [ERROR] set PYTHONPATH=src
python -m mkdocs build failed.
)
echo [SUCCESS] Documentation built to docs/



