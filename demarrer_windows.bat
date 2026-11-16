@echo off
chcp 65001 >nul
title Tolerie Facade - PDF vers DXF / STEP
cd /d "%~dp0"

echo ============================================================
echo   TOLERIE FACADE  -  demarrage
echo ============================================================
echo.

REM --- verifier que Python est installe ---
python --version >nul 2>&1
if errorlevel 1 (
  echo [ERREUR] Python n'est pas installe ou pas dans le PATH.
  echo.
  echo   1. Telecharge Python sur https://www.python.org/downloads/
  echo   2. A l'installation, COCHE "Add Python to PATH"
  echo   3. Relance ce fichier.
  echo.
  pause
  exit /b 1
)

REM --- installer les dependances (seulement la 1ere fois, ~quelques minutes) ---
if not exist ".deps_ok" (
  echo Installation des composants ^(premiere fois seulement, patiente^)...
  python -m pip install --upgrade pip >nul 2>&1
  python -m pip install -r requirements.txt
  if errorlevel 1 (
    echo [ERREUR] L'installation des composants a echoue. Verifie ta connexion internet.
    pause
    exit /b 1
  )
  echo ok> .deps_ok
)

echo.
echo Demarrage du programme... La fenetre du navigateur va s'ouvrir.
echo  (Laisse CETTE fenetre noire ouverte pendant que tu travailles.)
echo  Pour arreter : ferme cette fenetre, ou appuie sur Ctrl+C.
echo.

REM --- ouvrir le navigateur puis lancer le serveur ---
start "" http://127.0.0.1:5000
python -m app.serveur

pause
