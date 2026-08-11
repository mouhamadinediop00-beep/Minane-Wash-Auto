@echo off
chcp 65001 >nul
title MINAN WASH AUTO - Application de gestion
cd /d "%~dp0"

REM Se placer dans le dossier contenant main.py
if not exist "main.py" if exist "lavage_meckhe\main.py" cd lavage_meckhe
if not exist "main.py" for /d %%D in (*) do if exist "%%D\main.py" cd "%%D"

if not exist "main.py" (
    echo [ERREUR] Fichier main.py introuvable.
    echo Placez ce fichier DEMARRER.bat dans le dossier de l'application.
    echo.
    pause
    exit /b 1
)

echo ============================================================
echo   MINAN WASH AUTO
echo ============================================================
echo.

REM Verifier Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python n'est pas installe ou pas dans le PATH.
    echo Installez Python 3.12 depuis https://www.python.org/downloads/
    echo en cochant "Add Python to PATH" au debut de l'installation.
    echo.
    pause
    exit /b 1
)

echo Verification des composants (au premier lancement seulement)...
python -c "import flet" >nul 2>&1
if errorlevel 1 (
    echo Installation des composants necessaires, patientez...
    python -m pip install --upgrade pip >nul 2>&1
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [ERREUR] L'installation des composants a echoue.
        echo Verifiez votre connexion Internet puis relancez.
        echo.
        pause
        exit /b 1
    )
)

echo Demarrage de l'application...
echo.
python main.py

if errorlevel 1 (
    echo.
    echo [ERREUR] L'application s'est arretee suite a une erreur.
    echo Notez le message ci-dessus et transmettez-le au support.
    echo.
)
pause
