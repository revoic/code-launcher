@echo off
REM ============================================================================
REM Code Launcher - Runner (Windows)
REM Wird vom Bootstrap (Start_Windows.bat) aufgerufen, nachdem das Repo
REM auf den neuesten Stand gebracht wurde. Kuemmert sich um venv, Pakete
REM und das Starten von Streamlit.
REM ============================================================================

setlocal
set "APP_DIR=%~dp0"
if "%APP_DIR:~-1%"=="\" set "APP_DIR=%APP_DIR:~0,-1%"
set "VENV_DIR=%USERPROFILE%\.code-launcher-venv"

REM --- Python suchen ---------------------------------------------------
set "PY_BIN="
for %%P in (python py) do (
    where %%P >nul 2>nul
    if not errorlevel 1 (
        set "PY_BIN=%%P"
        goto :found
    )
)

echo [!] Python 3 wurde nicht gefunden.
echo     Installiere Python von https://www.python.org/downloads/
echo     WICHTIG: Beim Installer das Haekchen "Add Python to PATH" setzen!
start https://www.python.org/downloads/
pause
exit /b 1

:found
echo [OK] Python: %PY_BIN%

REM --- venv anlegen ----------------------------------------------------
if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo - Lege virtuelle Umgebung an ^(einmalig^) ...
    %PY_BIN% -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [!] venv konnte nicht erstellt werden.
        pause
        exit /b 1
    )
)
call "%VENV_DIR%\Scripts\activate.bat"

REM --- Pakete installieren (nur wenn requirements.txt sich geaendert hat) ---
set "REQ_FILE=%APP_DIR%\requirements.txt"
set "REQ_HASH_FILE=%VENV_DIR%\.requirements.hash"

for /f "delims=" %%H in ('certutil -hashfile "%REQ_FILE%" SHA256 ^| findstr /R "^[0-9a-f]"') do (
    set "NEW_HASH=%%H"
    goto :got_hash
)
:got_hash
set "NEW_HASH=%NEW_HASH: =%"

set "OLD_HASH="
if exist "%REQ_HASH_FILE%" set /p OLD_HASH=<"%REQ_HASH_FILE%"

if not "%NEW_HASH%"=="%OLD_HASH%" (
    echo - Aktualisiere Pakete ...
    python -m pip install --quiet --upgrade pip
    python -m pip install --quiet -r "%REQ_FILE%"
    if errorlevel 1 (
        echo [!] Paket-Installation fehlgeschlagen.
        pause
        exit /b 1
    )
    > "%REQ_HASH_FILE%" echo %NEW_HASH%
) else (
    echo [OK] Pakete aktuell.
)

echo.
echo ================================================
echo   Oeffne den Code Launcher im Browser ...
echo   Zum Beenden dieses Fenster schliessen.
echo ================================================
echo.

python -m streamlit run "%APP_DIR%\app.py" --server.headless false --browser.gatherUsageStats false
endlocal
