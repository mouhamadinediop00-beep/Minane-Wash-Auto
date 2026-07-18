@echo off
REM Lancement de l'application en mode bureau (developpement / usage direct)
pip install -r requirements.txt >nul 2>&1
python main.py
