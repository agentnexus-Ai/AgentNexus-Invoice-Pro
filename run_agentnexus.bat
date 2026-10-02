@echo off
title AgentNexus Invoice Pro — Commercial Server
cd /d "%~dp0"

echo ===================================================================
echo   AGENTNEXUS INVOICE PRO — COMMERCIAL SOFTWARE v1.0
echo   Standalone Business Management, Invoicing & Dispatch System
echo ===================================================================
echo.
echo Starting Localhost Server...
echo.

python app.py
if errorlevel 1 (
    echo.
    echo Python was not found or failed to start.
    echo Please ensure Python 3.8+ is installed on your computer.
    echo.
    pause
)
