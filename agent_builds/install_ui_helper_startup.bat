@echo off
REM Ten skrypt musi być uruchomiony jako Administrator.
REM Dodaje program ui_helper.exe do autostartu dla wszystkich użytkowników.
REM Zakłada, że ui_helper.exe znajduje się w tym samym folderze co ten skrypt.

set "INSTALL_PATH=%~dp0ui_helper.exe"

echo Dodawanie do autostartu: %INSTALL_PATH%
reg add "HKLM\Software\Microsoft\Windows\CurrentVersion\Run" /v "WingetAgentUIHelper" /t REG_SZ /d "%INSTALL_PATH%" /f

if %errorlevel% equ 0 (
    echo.
    echo Sukces! Pomocnik UI zostanie uruchomiony przy następnym logowaniu użytkownika.
) else (
    echo.
    echo BŁĄD! Nie udało się dodać wpisu do rejestru. Upewnij się, że skrypt został uruchomiony z uprawnieniami administratora.
)

echo.
pause