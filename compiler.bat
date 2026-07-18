@echo off
REM ======================================================================
REM  LAVAGE MECKHE - Compilation de l'application
REM  A executer sous Windows apres avoir installe Python 3.10+ et Flet.
REM ======================================================================
echo.
echo === Installation des dependances ===
pip install -r requirements.txt

echo.
echo === Que voulez-vous generer ? ===
echo   1. Application Windows (.exe)
echo   2. Application Android (.apk)  [necessite Flutter + Android SDK]
echo   3. Les deux
set /p choix="Votre choix (1/2/3) : "

if "%choix%"=="1" goto windows
if "%choix%"=="2" goto android
if "%choix%"=="3" goto windows

:windows
echo.
echo === Generation de l'executable Windows ===
flet build windows --project "Lavage Meckhe" --description "Gestion station de lavage"
echo.
echo Executable genere dans : build\windows\
if "%choix%"=="3" goto android
goto fin

:android
echo.
echo === Generation de l'APK Android ===
flet build apk --project "Lavage Meckhe" --description "Gestion station de lavage"
echo.
echo APK genere dans : build\apk\
goto fin

:fin
echo.
echo === Termine ===
pause
