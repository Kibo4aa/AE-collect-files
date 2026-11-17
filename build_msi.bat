@echo off
rem Buat installer .msi sendiri, hasilnya di folder dist.
rem Butuh: hasil build_exe.bat dan .NET SDK 8 (https://dotnet.microsoft.com/download).
setlocal
cd /d "%~dp0"
if not exist "dist\CollectFilesPlus\CollectFilesPlus.exe" (
    echo Jalankan build_exe.bat dulu.
    pause
    exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0packaging\build_msi.ps1" || goto gagal
echo.
pause
exit /b 0

:gagal
echo.
echo Build .msi gagal, lihat pesan di atas.
pause
exit /b 1
