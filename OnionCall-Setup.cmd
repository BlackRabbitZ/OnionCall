@echo off
setlocal
cd /d "%~dp0"
where pyw >nul 2>&1
if not errorlevel 1 (
    start "" pyw -3 "%~dp0OnionCall-Setup.pyw"
    exit /b 0
)
where pythonw >nul 2>&1
if not errorlevel 1 (
    start "" pythonw "%~dp0OnionCall-Setup.pyw"
    exit /b 0
)
echo Python wurde nicht gefunden. Installiere Python 3.10 oder neuer und starte diese Datei erneut.
pause
exit /b 1
