@echo off
echo Streamlit を停止します...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8501') do (
    echo PID %%a を終了します
    taskkill /PID %%a /F >nul 2>&1
)
echo 停止しました。
pause
