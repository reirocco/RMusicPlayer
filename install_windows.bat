@echo off
setlocal enabledelayedexpansion
title 🎵 RMusicPlayer - Advanced Windows Installer

echo ==========================================
echo      RMusicPlayer Installer (Windows)
echo ==========================================
echo.

:: 1. Controllo Python
echo [INFO] Verifica installazione Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRORE] Python non trovato!
    echo Per favore installa Python 3.9+ dal Microsoft Store o da python.org
    echo Assicurati di selezionare "Add Python to PATH" durante l'installazione.
    pause
    exit /b
)

set "WORK_DIR=%~dp0"
cd /d "%WORK_DIR%"

:: 2. Creazione Virtual Environment
if not exist ".venv" (
    echo [INFO] Creazione ambiente virtuale (.venv)...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [ERRORE] Impossibile creare il virtualenv. Assicurati che Python sia installato correttamente.
        pause
        exit /b
    )
) else (
    echo [OK] Ambiente virtuale gia' esistente.
)

:: 3. Upgrade Pip e Installazione Dipendenze
echo [INFO] Installazione dipendenze (Flask, Librosa, Pygame)...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip

echo [INFO] Sto scaricando le librerie audio...
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo [ERRORE] Impossibile installare tutte le dipendenze automaticamente.
    echo Spesso questo accade se mancano i "Microsoft C++ Build Tools" per 'librosa'.
    echo Se vedi errori relativi a 'numba' o 'llvmlite', scarica i Build Tools qui:
    echo https://visualstudio.microsoft.com/visual-cpp-build-tools/
    echo Seleziona "Sviluppo di desktop con C++".
    pause
    exit /b
)

:: 4. Controllo FFmpeg
echo [INFO] Controllo FFmpeg...
ffmpeg -version >nul 2>&1
if %errorlevel% neq 0 (
    if exist "ffmpeg.exe" (
        echo [OK] FFmpeg trovato nella cartella locale.
    ) else (
        echo.
        echo [ATTENZIONE] FFmpeg non trovato!
        echo L'Automix richiede FFmpeg per leggere gli MP3 tramite Pydub.
        echo Scaricalo da https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip 
        echo ed estrai 'ffmpeg.exe' in questa cartella: "%WORK_DIR%"
        echo.
    )
) else (
    echo [OK] FFmpeg trovato nel PATH di sistema.
)

:: 5. Creazione Launcher (run.bat)
echo [INFO] Rigenerazione script di avvio (run.bat)...
(
echo @echo off
echo cd /d "%%~dp0"
echo if not exist ".venv" (
echo     echo [ERRORE] Ambiente virtuale non trovato! Esegui prima l'installer.
echo     pause
echo     exit /b
echo )
echo echo [System] Attivazione ambiente...
echo call .venv\Scripts\activate.bat
echo echo [System] Avvio server RMusicPlayer su http://localhost:5000
echo start http://localhost:5000
echo python app.py
echo if %%errorlevel%% neq 0 (
echo     echo [ERRORE] Il server si e' fermato in modo anomalo. Controlla i log sopra.
echo     pause
echo )
) > run.bat

echo.
echo ==========================================
echo      INSTALLAZIONE COMPLETATA!
echo ==========================================
echo.
echo Ora puoi avviare il player in qualsiasi momento usando 'run.bat'.
echo.
pause