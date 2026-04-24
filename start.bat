@echo off
echo 起動中... http://localhost:8501 をブラウザで開いてください
call .venv\Scripts\activate
streamlit run app.py
