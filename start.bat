@echo off
REM =====================================
REM Lobster Quant - Startup Script
REM =====================================

echo.
echo ====================================
echo   Lobster Quant - Quantitative Trading
echo ====================================
echo.
echo Please select version to start:
echo   [1] v2.0 (Recommended) - New modular architecture
echo   [2] v1.0 (Legacy) - Legacy architecture
echo   [3] Exit
echo.

set /p CHOICE="Enter option (1-3): "

if "%CHOICE%"=="1" (
    echo.
    echo Starting Lobster Quant v2.0...
    cd /d "%~dp0lobster_quant" 2>nul
    if errorlevel 1 (
        echo Error: Cannot enter project directory
        pause
        exit /b 1
    )
    where streamlit >nul 2>&1
    if errorlevel 1 (
        echo Error: streamlit not found. Install with: pip install streamlit
        pause
        exit /b 1
    )
    echo Starting Streamlit server...
    echo URL: http://localhost:8501
    echo Press Ctrl+C to stop.
    echo.
    streamlit run app_v2.py
    echo.
    echo Streamlit has stopped.
    pause
    exit /b 0
)

if "%CHOICE%"=="2" (
    echo.
    echo Starting Lobster Quant v1.0 (legacy)...
    cd /d "%~dp0lobster_quant" 2>nul
    if errorlevel 1 (
        echo Error: Cannot enter project directory
        pause
        exit /b 1
    )
    where streamlit >nul 2>&1
    if errorlevel 1 (
        echo Error: streamlit not found. Install with: pip install streamlit
        pause
        exit /b 1
    )
    echo Starting Streamlit server...
    echo URL: http://localhost:8501
    echo Press Ctrl+C to stop.
    echo.
    streamlit run app.py
    echo.
    echo Streamlit has stopped.
    pause
    exit /b 0
)

if "%CHOICE%"=="3" (
    echo.
    echo Cancelled.
    exit /b 0
)

echo.
echo Invalid option.
pause
exit /b 1
