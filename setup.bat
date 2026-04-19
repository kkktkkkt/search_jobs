@echo off
echo [1/2] Installing Python packages...
call .venv\Scripts\pip install -r requirements.txt

echo [2/2] Installing Playwright browsers...
call .venv\Scripts\playwright install chromium

echo Done! Run "run.bat" to start the app.
pause
