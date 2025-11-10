@echo off
python -m venv .venv
call .venv\Scripts\activate
pip install -U pip
pip install -r requirements.txt
python -m playwright install chromium
echo Done.
