@echo off
echo Streamlit を再起動します...

rem 既存のプロセスを停止
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8501') do (
    echo PID %%a を終了します
    taskkill /PID %%a /F >nul 2>&1
)

echo 再起動中... http://localhost:8501 をブラウザで開いてください
call .venv\Scripts\activate
streamlit run app.py
