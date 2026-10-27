@echo off
cd /d "%~dp0"
where uv >nul 2>nul
if errorlevel 1 (
  echo uv is missing. Open START_HERE.md for the installation command.
  pause
  exit /b 1
)
uv sync --frozen
if errorlevel 1 (
  pause
  exit /b 1
)
uv run streamlit run src/app.py
pause
