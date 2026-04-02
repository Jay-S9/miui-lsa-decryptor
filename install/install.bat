@echo off
:: ============================================================
:: MIUI LSA Decryptor — Windows Context Menu Installer
:: ============================================================
:: This script adds "Decrypt with LSA Decryptor" to the
:: right-click context menu for .lsa and .lsav files.
::
:: Run as Administrator (right-click → "Run as administrator")
:: ============================================================

setlocal EnableDelayedExpansion
title MIUI LSA Decryptor — Context Menu Installer

:: Check for admin rights
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo.
    echo  [ERROR] This script must be run as Administrator.
    echo  Right-click install.bat and choose "Run as administrator"
    echo.
    pause
    exit /b 1
)

:: ─────────────────────────────────────────────────────────────
:: Detect Python
:: ─────────────────────────────────────────────────────────────
where python >nul 2>&1
if %errorLevel% neq 0 (
    echo.
    echo  [ERROR] Python not found in PATH.
    echo  Please install Python 3.8+ from https://python.org
    echo  Make sure "Add Python to PATH" is checked during install.
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo.
echo  Detected: %PYVER%

:: ─────────────────────────────────────────────────────────────
:: Detect script location (same folder as this .bat)
:: ─────────────────────────────────────────────────────────────
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "GUI_SCRIPT=%SCRIPT_DIR%\..\src\gui.py"
set "CLI_SCRIPT=%SCRIPT_DIR%\..\src\cli.py"

:: Resolve to absolute path
for %%i in ("%GUI_SCRIPT%") do set "GUI_ABS=%%~fi"
for %%i in ("%CLI_SCRIPT%") do set "CLI_ABS=%%~fi"

:: Check scripts exist
if not exist "%GUI_ABS%" (
    echo.
    echo  [ERROR] Cannot find gui.py at: %GUI_ABS%
    echo  Make sure this installer is in the install\ folder of the project.
    echo.
    pause
    exit /b 1
)

:: ─────────────────────────────────────────────────────────────
:: Install pycryptodome if not present
:: ─────────────────────────────────────────────────────────────
echo.
echo  Checking dependencies...
python -c "from Crypto.Cipher import AES" >nul 2>&1
if %errorLevel% neq 0 (
    echo  Installing pycryptodome...
    python -m pip install pycryptodome --quiet
    if %errorLevel% neq 0 (
        echo  [ERROR] Failed to install pycryptodome.
        pause
        exit /b 1
    )
    echo  pycryptodome installed OK
) else (
    echo  pycryptodome already installed
)

python -c "import customtkinter" >nul 2>&1
if %errorLevel% neq 0 (
    echo  Installing customtkinter...
    python -m pip install customtkinter --quiet
    if %errorLevel% neq 0 (
        echo  [ERROR] Failed to install customtkinter.
        pause
        exit /b 1
    )
    echo  customtkinter installed OK
) else (
    echo  customtkinter already installed
)

:: ─────────────────────────────────────────────────────────────
:: Register .lsa file type
:: ─────────────────────────────────────────────────────────────
echo.
echo  Registering context menu for .lsa files...

:: Associate extension with our progID
reg add "HKEY_CLASSES_ROOT\.lsa"                                                   /ve /d "MIUI.LSAFile"           /f >nul
reg add "HKEY_CLASSES_ROOT\MIUI.LSAFile"                                           /ve /d "MIUI Encrypted Photo"   /f >nul
reg add "HKEY_CLASSES_ROOT\MIUI.LSAFile\DefaultIcon"                               /ve /d "shell32.dll,22"         /f >nul
reg add "HKEY_CLASSES_ROOT\MIUI.LSAFile\shell\DecryptLSA"                          /ve /d "Decrypt with LSA Decryptor" /f >nul
reg add "HKEY_CLASSES_ROOT\MIUI.LSAFile\shell\DecryptLSA"                          /v "Icon" /d "shell32.dll,47"   /f >nul
reg add "HKEY_CLASSES_ROOT\MIUI.LSAFile\shell\DecryptLSA\command"                  /ve /d "pythonw.exe \"%GUI_ABS%\" \"%%1\"" /f >nul

:: ─────────────────────────────────────────────────────────────
:: Register .lsav file type
:: ─────────────────────────────────────────────────────────────
echo  Registering context menu for .lsav files...

reg add "HKEY_CLASSES_ROOT\.lsav"                                                  /ve /d "MIUI.LSAVFile"          /f >nul
reg add "HKEY_CLASSES_ROOT\MIUI.LSAVFile"                                          /ve /d "MIUI Encrypted Video"   /f >nul
reg add "HKEY_CLASSES_ROOT\MIUI.LSAVFile\DefaultIcon"                              /ve /d "shell32.dll,116"        /f >nul
reg add "HKEY_CLASSES_ROOT\MIUI.LSAVFile\shell\DecryptLSAV"                        /ve /d "Decrypt with LSA Decryptor" /f >nul
reg add "HKEY_CLASSES_ROOT\MIUI.LSAVFile\shell\DecryptLSAV"                        /v "Icon" /d "shell32.dll,47"   /f >nul
reg add "HKEY_CLASSES_ROOT\MIUI.LSAVFile\shell\DecryptLSAV\command"                /ve /d "pythonw.exe \"%GUI_ABS%\" \"%%1\"" /f >nul

:: ─────────────────────────────────────────────────────────────
:: Also register for folder background (right-click inside a folder)
:: ─────────────────────────────────────────────────────────────
echo  Registering folder background menu...

reg add "HKEY_CLASSES_ROOT\Directory\Background\shell\DecryptLSA"                  /ve /d "Decrypt .lsa/.lsav files here" /f >nul
reg add "HKEY_CLASSES_ROOT\Directory\Background\shell\DecryptLSA"                  /v "Icon" /d "shell32.dll,47" /f >nul
reg add "HKEY_CLASSES_ROOT\Directory\Background\shell\DecryptLSA\command"          /ve /d "pythonw.exe \"%GUI_ABS%\" \"%%V\"" /f >nul

:: ─────────────────────────────────────────────────────────────
:: Notify Windows shell to refresh file type associations
:: ─────────────────────────────────────────────────────────────
ie4uinit.exe -show >nul 2>&1

echo.
echo  ══════════════════════════════════════════════
echo   Installation complete!
echo  ══════════════════════════════════════════════
echo.
echo   Right-click any .lsa or .lsav file and choose:
echo   "Decrypt with LSA Decryptor"
echo.
echo   Or right-click inside a folder containing those
echo   files and choose "Decrypt .lsa/.lsav files here"
echo.
pause
exit /b 0
