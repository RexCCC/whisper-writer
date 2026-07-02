@echo off
cd /d "%~dp0"
call venv\Scripts\activate
python run.py
if errorlevel 1 (
    echo.
    echo WhisperWriter exited with an error.
    pause
)
