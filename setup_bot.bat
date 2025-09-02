@echo off
echo ==========================================
echo Discord Ticket Bot - Windows Setup
echo ==========================================

echo.
echo Step 1: Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please download Python from https://python.org
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
) else (
    echo SUCCESS: Python is installed
    python --version
)

echo.
echo Step 2: Installing bot dependencies...
pip install discord.py>=2.3.2 python-dotenv>=1.0.0 openai>=0.28.0
if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
) else (
    echo SUCCESS: All dependencies installed
)

echo.
echo Step 3: Checking configuration file...
if exist .env (
    echo SUCCESS: .env file found
) else (
    echo ERROR: .env file not found!
    echo Please make sure .env file is in this folder
    pause
    exit /b 1
)

echo.
echo ==========================================
echo Setup completed successfully!
echo ==========================================
echo.
echo Next steps:
echo 1. Make sure you've enabled privileged intents in Discord Developer Portal
echo 2. Run: start_bot.bat
echo 3. Use /setup command in Discord to create ticket panel
echo.
pause