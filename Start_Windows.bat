@echo off
REM ============================================================================
REM Code Launcher - Start-Skript fuer Windows (BOOTSTRAP)
REM ============================================================================
REM Diese kleine Datei holt sich die neueste Version aus dem Git-Repo
REM und startet sie. Sie selbst aendert sich praktisch nie - die ganze
REM Update-Logik lebt im Repo (siehe run.bat).
REM ============================================================================

setlocal EnableDelayedExpansion
cd /d "%~dp0"

REM === KONFIGURATION =====================================================
REM Trage hier die HTTPS-URL deines Code-Launcher-Repos ein.
REM Beispiel: https://github.com/max-kirchhoff/code-launcher.git
set "REPO_URL=https://github.com/revoic/code-launcher.git"
set "BRANCH=main"
REM =======================================================================

set "APP_HOME=%USERPROFILE%\.code-launcher-app"

echo.
echo ================================================
echo   Code Launcher
echo ================================================
echo.

REM --- Platzhalter-Check ------------------------------------------------
echo %REPO_URL% | findstr /C:"CHANGE-ME" >nul
if not errorlevel 1 (
    echo [!] Im Start-Skript ist noch keine Repo-URL eingetragen.
    echo     Oeffne 'Start_Windows.bat' im Texteditor und ersetze
    echo     die REPO_URL durch deine GitHub-Adresse.
    echo.
    pause
    exit /b 1
)

REM --- 1) Git pruefen ---------------------------------------------------
where git >nul 2>nul
if errorlevel 1 (
    echo [!] Git ist nicht installiert.
    echo.
    echo Bitte installiere "Git for Windows":
    echo   https://git-scm.com/download/win
    echo.
    start https://git-scm.com/download/win
    pause
    exit /b 1
)

REM --- 2) Repo klonen oder updaten -------------------------------------
if not exist "%APP_HOME%\.git" (
    echo - Erstinstallation: lade Code Launcher herunter ...
    if exist "%APP_HOME%" rmdir /s /q "%APP_HOME%"
    git clone --depth 1 -b %BRANCH% "%REPO_URL%" "%APP_HOME%"
    if errorlevel 1 (
        echo.
        echo [!] Download fehlgeschlagen.
        echo     Pruefe die Internetverbindung oder die Repo-URL.
        pause
        exit /b 1
    )
) else (
    echo - Suche nach Updates ...
    git -C "%APP_HOME%" fetch --depth 1 origin %BRANCH% >nul 2>nul
    if errorlevel 1 (
        echo   ^(offline - fahre mit lokal vorhandener Version fort^)
    ) else (
        for /f %%H in ('git -C "%APP_HOME%" rev-parse HEAD') do set "BEFORE=%%H"
        git -C "%APP_HOME%" reset --hard origin/%BRANCH% >nul
        for /f %%H in ('git -C "%APP_HOME%" rev-parse HEAD') do set "AFTER=%%H"
        if "!BEFORE!"=="!AFTER!" (
            echo   Schon auf der neuesten Version.
        ) else (
            echo   Neue Version installiert.
        )
    )
)

REM --- Version fuer die App weitergeben --------------------------------
for /f %%H in ('git -C "%APP_HOME%" rev-parse --short HEAD 2^>nul') do set "CODE_LAUNCHER_VERSION=%%H"
if "%CODE_LAUNCHER_VERSION%"=="" set "CODE_LAUNCHER_VERSION=unknown"
set "CODE_LAUNCHER_VERSION=%CODE_LAUNCHER_VERSION%"

REM --- 3) An run.bat uebergeben ----------------------------------------
call "%APP_HOME%\run.bat"
endlocal
