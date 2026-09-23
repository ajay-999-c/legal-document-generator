@echo off
setlocal
cd /d "%~dp0"
if not "%OS%"=="Windows_NT" (
  echo ERROR: Build this executable on Windows.
  exit /b 1
)
set "PROJECT_PYTHON=%CD%\.venv\Scripts\python.exe"
if not exist "%PROJECT_PYTHON%" (
  echo ERROR: Create the project .venv and install requirements-build.txt first.
  exit /b 1
)
"%PROJECT_PYTHON%" -c "import sys; print(sys.executable); print(sys.version); sys.exit(0 if sys.version_info[:2] in ((3, 11), (3, 14)) else 'Use Python 3.11 or 3.14 for this build')"
if errorlevel 1 exit /b 1
"%PROJECT_PYTHON%" -m pip check
if errorlevel 1 exit /b 1
"%PROJECT_PYTHON%" -m pytest tests -q
if errorlevel 1 (
  echo ERROR: Tests failed. No executable was built.
  exit /b 1
)
"%PROJECT_PYTHON%" -m PyInstaller --clean --noconfirm legal_document_generator.spec
if errorlevel 1 exit /b 1
if not exist "dist\Legal Document Generator.exe" exit /b 1
echo Build complete: "%CD%\dist\Legal Document Generator.exe"
echo Distribute with install_windows.ps1 and config.example.yaml. Never include office secrets.
endlocal
