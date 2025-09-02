@echo off
echo ==========================================
echo Discord Bot - Quick Setup
echo ==========================================

echo Current directory: %cd%

echo.
echo Creating .env file...
(
echo DISCORD_TOKEN=MTQxMTY5MTQ4Mjc2NjY0MzIxMA.G3y0Yt.0GXm8Q7uE2Cn7KUVC1KpQPq7lpBr_3j1d3IX0g
echo MAIN_GUILD_ID=1411650187491016777
echo SUPPORT_GUILD_ID=1411760611364306956
echo STAFF_ROLE_ID=1411939464380416141
echo TICKET_CATEGORY_ID=1411650190175109173
echo OPENAI_API_KEY=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
) > .env

if exist .env (
    echo ✅ .env file created successfully!
) else (
    echo ❌ Failed to create .env file
    pause
    exit /b 1
)

echo.
echo Checking current directory contents:
dir *.py
dir .env

echo.
echo ==========================================
echo Setup complete! 
echo You can now run: python main_bot.py
echo ==========================================
pause
