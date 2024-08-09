@echo off

echo Loading Privatools...
git pull --all
if not exist .venv python -m venv .venv
call .venv\Scripts\activate
pip install -r requirements.txt

python update.py