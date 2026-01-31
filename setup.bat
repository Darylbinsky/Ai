@echo off
echo ========================================
echo Stock Screener & Backtester Setup
echo ========================================
echo.

REM Try to find Python and use python -m pip instead of pip directly
REM This works even when pip is not in the PATH

echo Checking for Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Python is not installed or not in PATH.
    echo.
    echo Please install Python from https://www.python.org/downloads/
    echo During installation, make sure to check "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

echo Python found!
echo.
echo Installing dependencies...
echo.

python -m pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Failed to install dependencies.
    echo.
    echo Try running this script as Administrator, or manually run:
    echo     python -m pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo Setup completed successfully!
echo ========================================
echo.
echo You can now run the application with:
echo     python main.py
echo.
pause
