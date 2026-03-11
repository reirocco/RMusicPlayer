@echo off
setlocal
title RMusicPlayer Installer

echo ==========================================
echo      RMusicPlayer Installer (Windows)
echo ==========================================
echo.

:: 1. Controllo Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRORE] Python non trovato!
    echo Per favore installa Python 3.8+ dal Microsoft Store o da python.org
    echo Assicurati di selezionare "Add Python to PATH" durante l'installazione.
    pause
    exit /b
)

:: 2. Controllo Cartella
set "WORK_DIR=%~dp0"
cd /d "%WORK_DIR%"
echo [INFO] Cartella di lavoro: %WORK_DIR%

:: 3. Creazione Virtual Environment
if not exist ".venv" (
    echo [INFO] Creazione ambiente virtuale (.venv)...
    python -m venv .venv
) else (
    echo [INFO] Ambiente virtuale gia' esistente.
)

:: 4. Attivazione e Installazione Dipendenze
echo [INFO] Installazione dipendenze...
call .venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt

:: 5. Controllo FFmpeg (opzionale ma consigliato)
ffmpeg -version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [ATTENZIONE] FFmpeg non trovato nel PATH!
    echo L'Automix richiede FFmpeg per funzionare correttamente.
    echo Scaricalo da https://ffmpeg.org/download.html e aggiungilo al PATH,
    echo oppure estrai ffmpeg.exe nella cartella: %WORK_DIR%
    echo.
)

:: 6. Creazione Launcher (run.bat)
echo [INFO] Creazione script di avvio (run.bat)...
(
echo @echo off
echo cd /d "%%~dp0"
echo call .venv\Scripts\activate.bat
echo echo Avvio RMusicPlayer...
echo start http://localhost:5000
echo python app.py
echo pause
) > run.bat

:: 7. Richiesta Avvio Automatico
echo.
set /p AUTOSTART="Vuoi avviare RMusicPlayer automaticamente all'accensione del PC? (S/N): "
if /i "%AUTOSTART%"=="S" (
    echo [INFO] Creazione collegamento in Esecuzione Automatica...
    set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"

    :: Crea un VBScript temporaneo per creare il collegamento (shortcut)
    echo Set oWS = WScript.CreateObject("WScript.Shell") > CreateShortcut.vbs
    echo sLinkFile = "%STARTUP_FOLDER%\RMusicPlayer.lnk" >> CreateShortcut.vbs
    echo Set oLink = oWS.CreateShortcut(sLinkFile) >> CreateShortcut.vbs
    echo oLink.TargetPath = "%WORK_DIR%run.bat" >> CreateShortcut.vbs
    echo oLink.WorkingDirectory = "%WORK_DIR%" >> CreateShortcut.vbs
    echo oLink.Description = "RMusicPlayer Automix Server" >> CreateShortcut.vbs
    echo oLink.Save >> CreateShortcut.vbs

    cscript CreateShortcut.vbs
    del CreateShortcut.vbs
    echo [OK] Collegamento creato!
)

echo.
echo ==========================================
echo      Installazione Completata!
echo ==========================================
echo.
echo Per avviare il player, fai doppio click su 'run.bat'.
echo.
pause