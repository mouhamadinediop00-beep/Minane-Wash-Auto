@echo off
chcp 65001 >nul
title Lavage Meckhe - Mode reseau (acces a distance)
cd /d "%~dp0"
if exist "lavage_meckhe\main.py" cd lavage_meckhe
if not exist "main.py" for /d %%D in (*) do if exist "%%D\main.py" cd "%%D"

echo Installation des composants si necessaire...
python -m pip install -r requirements.txt >nul 2>&1

echo.
echo Demarrage du serveur reseau...
echo (Laissez cette fenetre ouverte pendant l'utilisation)
echo.
python serveur_reseau.py
pause
