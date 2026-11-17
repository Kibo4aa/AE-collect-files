<#
  Membuat installer .msi dari hasil PyInstaller (dist\CollectFilesPlus) dengan WiX Toolset v5.
  Dipakai oleh build_msi.bat (di komputer sendiri) dan oleh GitHub Actions (release.yml).

    powershell -ExecutionPolicy Bypass -File packaging\build_msi.ps1 [-Version 1.1.0] [-OutDir dist] [-Name ...]

  Butuh .NET SDK 6 atau lebih baru (https://dotnet.microsoft.com/download). WiX dipasang otomatis
  sebagai .NET tool (versi 5.0.2, lisensi MS-RL) kalau belum ada.
#>
param(
    [string]$AppDir = "dist\CollectFilesPlus",
    [string]$OutDir = "dist",
    [string]$Version = "",
    [string]$Name = ""
)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)          # folder utama repo

if (-not $Version) {
    $m = Select-String -Path "src\collect_files_plus\__init__.py" -Pattern '__version__ = "([^"]+)"'
    $Version = $m.Matches[0].Groups[1].Value
}
if (-not $Name) { $Name = "CollectFilesPlus-v$Version-windows-x64" }
if (-not (Test-Path (Join-Path $AppDir "CollectFilesPlus.exe"))) {
    throw "$AppDir\CollectFilesPlus.exe belum ada. Jalankan build_exe.bat dulu."
}

# 1. WiX Toolset v5
$wix = Join-Path $env:USERPROFILE ".dotnet\tools\wix.exe"
if (-not (Test-Path $wix)) {
    if (-not (Get-Command dotnet -ErrorAction SilentlyContinue)) {
        throw ".NET SDK belum terpasang. Download: https://dotnet.microsoft.com/download (pilih .NET SDK 8)."
    }
    dotnet tool install --global wix --version 5.0.2
    if ($LASTEXITCODE -ne 0) { throw "Gagal memasang WiX (dotnet tool install)." }
}
& $wix extension add -g WixToolset.UI.wixext/5.0.2 | Out-Host   # sudah ada pun tidak apa-apa

# 2. isi installer: aplikasi + panduan + lisensi + script JSX + penanda "msi" (dipakai update otomatis)
$stageRoot = Join-Path ([IO.Path]::GetTempPath()) "CollectFilesPlus-msi"
$stage = Join-Path $stageRoot "CollectFilesPlus"
if (Test-Path $stageRoot) { Remove-Item -Recurse -Force $stageRoot }
New-Item -ItemType Directory -Force $stageRoot | Out-Null
Copy-Item -Recurse $AppDir $stage
foreach ($l in "en", "id", "ja") {
    Copy-Item "src\collect_files_plus\docs\README_$l.txt" (Join-Path $stage "README_$($l.ToUpper()).txt")
}
Copy-Item LICENSE, NOTICE.md $stage
New-Item -ItemType Directory -Force (Join-Path $stage "jsx") | Out-Null
Copy-Item jsx\CollectFilesPlus.jsx (Join-Path $stage "jsx")
Set-Content -LiteralPath (Join-Path $stage "install-type.txt") -Value "msi" -Encoding ascii

# 3. build
New-Item -ItemType Directory -Force $OutDir | Out-Null
$out = Join-Path $OutDir "$Name.msi"
& $wix build packaging\installer.wxs -arch x64 -ext WixToolset.UI.wixext `
    -d "Version=$Version" -d "IconFile=packaging\icon.ico" -d "LicenseRtf=packaging\License.rtf" `
    -bindpath "app=$stage" -o $out
if ($LASTEXITCODE -ne 0) { throw "wix build gagal." }
Remove-Item -Recurse -Force $stageRoot
Write-Host "Selesai: $out"
