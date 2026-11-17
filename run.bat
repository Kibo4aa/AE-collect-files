@echo off
rem Jalankan Collect Files Plus dari source (butuh Python 3.10+ dari python.org).
rem Pertama kali: otomatis membuat .venv dan install dependency (butuh internet).
rem Bisa juga drag file .aep ke run.bat.
setlocal
cd /d "%~dp0"
set "VENV=%~dp0.venv"
if not exist "%VENV%\.siap" (
    echo Menyiapkan Collect Files Plus untuk pertama kali...
    if not exist "%VENV%\Scripts\python.exe" (
        where py >nul 2>nul
        if errorlevel 1 (
            python -m venv "%VENV%"
        ) else (
            py -3 -m venv "%VENV%"
        )
    )
    if not exist "%VENV%\Scripts\python.exe" (
        echo.
        echo Python 3.10+ belum terinstall. Download di https://www.python.org/downloads/
        echo Saat install, centang "Add python.exe to PATH", lalu jalankan run.bat lagi.
        pause
        exit /b 1
    )
    "%VENV%\Scripts\python.exe" -m pip install --upgrade pip
    "%VENV%\Scripts\python.exe" -m pip install -e .
    if errorlevel 1 (
        echo.
        echo Gagal install dependency. Cek koneksi internet lalu jalankan run.bat lagi.
        pause
        exit /b 1
    )
    echo ok> "%VENV%\.siap"
)
start "" "%VENV%\Scripts\pythonw.exe" -m collect_files_plus %*
