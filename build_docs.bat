@echo off
set SITE_DIR=.\publish\docs
echo [DOCS] Building Toyopuc Python Docs...
python -m pip install --quiet mkdocs mkdocs-material mkdocstrings[python]
python -m mkdocs build --clean --site-dir "%SITE_DIR%"
echo [SUCCESS] Docs ready at %cd%\publish\docs\index.html
pause

