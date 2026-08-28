@echo off
setlocal
cd /d "%~dp0"

choice /c YN /m "Install Python requirements"
if errorlevel 2 (
    echo Skipped Python requirements.
    goto config
)
py -m pip install -r requirements.txt
if errorlevel 1 goto error

:config
if exist config.toml (
    echo Skipped config.toml creation because it already exists.
    goto setup
)
choice /c YN /m "Copy config.toml.example to config.toml"
if errorlevel 2 (
    echo Skipped config.toml creation.
    goto setup
)
copy /y config.toml.example config.toml >nul
if errorlevel 1 goto error

:setup
echo Starting Strava setup...
py setup_strava.py
if errorlevel 1 goto error
echo Starting Garmin setup...
py setup_garmin.py
if errorlevel 1 goto error

choice /c YN /m "Set up automatic startup now"
if errorlevel 2 (
    echo Skipped automatic startup setup.
    goto done
)
echo Setting up automatic startup...
powershell -ExecutionPolicy Bypass -File .\setup_startup.ps1
if errorlevel 1 goto error

:done
echo Setup complete.
exit /b 0

:error
echo Setup failed.
exit /b 1
