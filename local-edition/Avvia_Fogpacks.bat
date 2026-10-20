@echo off
setlocal
cd /d "%~dp0"

rem Preferisci Python 3.13, poi ripiega su python nel PATH.
py -3.13 --version >nul 2>nul
if not errorlevel 1 goto use_py_launcher

python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
if not errorlevel 1 goto use_python

echo Python non trovato. Installa Python 3.13 e riprova.
echo Download ufficiale: https://www.python.org/downloads/windows/
echo Se durante l'installazione disponibile, abilita l'opzione per aggiungere Python al PATH.
pause
exit /b 1

:use_py_launcher
py -3.13 fogpacks.py
goto finished

:use_python
python fogpacks.py

:finished
if errorlevel 1 (
  echo.
  echo Fogpacks non e' riuscito ad avviarsi. Controlla il messaggio sopra.
  pause
)
endlocal
