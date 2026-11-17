@echo off
rem Build CollectFilesPlus.exe sendiri (hasil: dist\CollectFilesPlus\).
setlocal
cd /d "%~dp0"
set "VENV=%~dp0.venv"
if not exist "%VENV%\Scripts\python.exe" (
    where py >nul 2>nul
    if errorlevel 1 (
        python -m venv "%VENV%"
    ) else (
        py -3 -m venv "%VENV%"
    )
)
if not exist "%VENV%\Scripts\python.exe" (
    echo Python 3.10+ belum terinstall: https://www.python.org/downloads/
    pause
    exit /b 1
)
"%VENV%\Scripts\python.exe" -m pip install --upgrade pip || goto gagal
"%VENV%\Scripts\python.exe" -m pip install -e .[build] || goto gagal
"%VENV%\Scripts\python.exe" -m PyInstaller --noconfirm --clean packaging\CollectFilesPlus.spec || goto gagal
echo ok> "%VENV%\.siap"
echo.
echo Selesai: dist\CollectFilesPlus\CollectFilesPlus.exe
pause
exit /b 0

:gagal
echo.
echo Build gagal, lihat pesan di atas.
pause
exit /b 1
