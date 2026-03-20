@echo off
echo [DOCS] Building Toyopuc Python Docs with MkDocs...
mkdocs build
if %errorlevel% neq 0 (
    echo [ERROR] MkDocs build failed.
)
echo [SUCCESS] Documentation built to site/
