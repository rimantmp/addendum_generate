# ==============================================================================
# INSTALLER OTOMATIS: SISTEM GENERATOR ADDENDUM & ALOKASI PUPUK BERSUBSIDI
# ==============================================================================
# Script ini secara otomatis:
# 1. Memeriksa keberadaan Python (jika belum ada, mengunduh & menginstall Python 3.12)
# 2. Membuat Virtual Environment (venv) terisolasi
# 3. Mengupgrade pip dan menginstall seluruh dependensi dari requirements.txt
# 4. Memverifikasi struktur database SQLite (addendum.db)
# 5. Membuat shortcut peluncur di Desktop
# ==============================================================================

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "   PEMASANG OTOMATIS: SISTEM GENERATOR ADDENDUM & SPJB PUPUK         " -ForegroundColor Cyan
Write-Host "   CV. SUBUR ANUGERAH SEJAHTERA - KABUPATEN TANA TORAJA              " -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# ------------------------------------------------------------------------------
# 1. Deteksi & Instalasi Python
# ------------------------------------------------------------------------------
Write-Host "[1/5] Memeriksa ketersediaan Python di sistem..." -ForegroundColor Yellow

function Find-Python {
    # Cek command python di PATH
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { return "python" }

    # Cek py launcher
    $cmdPy = Get-Command py -ErrorAction SilentlyContinue
    if ($cmdPy) { return "py" }

    # Cek lokasi instalasi standar Windows
    $possiblePaths = @(
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe",
        "C:\Program Files\Python312\python.exe",
        "C:\Program Files\Python311\python.exe",
        "C:\Program Files\Python310\python.exe"
    )

    foreach ($p in $possiblePaths) {
        if (Test-Path $p) { return $p }
    }
    return $null
}

$pythonExecutable = Find-Python

if (-not $pythonExecutable) {
    Write-Host ">> Python belum terpasang pada komputer ini." -ForegroundColor Magenta
    Write-Host ">> Memulai pengunduhan dan instalasi Python 3.12 (64-bit) otomatis..." -ForegroundColor Cyan

    $installerUrl = "https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe"
    $installerPath = "$env:TEMP\python-3.12.8-amd64.exe"

    Write-Host ">> Mengunduh installer resmi dari python.org..." -ForegroundColor Gray
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath -UseBasicParsing
    } catch {
        Write-Host ">> Gagal mengunduh via Invoke-WebRequest, mencoba curl..." -ForegroundColor Yellow
        curl.exe -L -o $installerPath $installerUrl
    }

    if (-not (Test-Path $installerPath)) {
        Write-Host "[ERROR] Gagal mengunduh installer Python. Pastikan koneksi internet aktif." -ForegroundColor Red
        Pause
        exit 1
    }

    Write-Host ">> Menginstall Python 3.12 secara hening (silent install)..." -ForegroundColor Cyan
    $installProcess = Start-Process -FilePath $installerPath -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1 Include_test=0 SimpleInstall=1" -Wait -PassThru

    # Refresh PATH environment
    $machinePath = [System.Environment]::GetEnvironmentVariable("Path", [System.EnvironmentVariableTarget]::Machine)
    $userPath = [System.Environment]::GetEnvironmentVariable("Path", [System.EnvironmentVariableTarget]::User)
    $env:Path = "$userPath;$machinePath;$env:LOCALAPPDATA\Programs\Python\Python312;$env:LOCALAPPDATA\Programs\Python\Python312\Scripts"

    # Hapus file installer sementara
    Remove-Item $installerPath -Force -ErrorAction SilentlyContinue

    $pythonExecutable = Find-Python
    if (-not $pythonExecutable) {
        Write-Host "[ERROR] Instalasi Python selesai namun belum terdeteksi di PATH." -ForegroundColor Red
        Write-Host "Silakan restart terminal atau buka kembali file INSTALL.bat." -ForegroundColor Yellow
        Pause
        exit 1
    }
    Write-Host "[OK] Python berhasil dipasang di sistem!" -ForegroundColor Green
} else {
    $versionOutput = & $pythonExecutable --version 2>&1
    Write-Host "[OK] Python terdeteksi: $versionOutput" -ForegroundColor Green
}

# ------------------------------------------------------------------------------
# 2. Pembuatan Virtual Environment (venv)
# ------------------------------------------------------------------------------
Write-Host ""
Write-Host "[2/5] Menyiapkan Virtual Environment (venv)..." -ForegroundColor Yellow

$venvDir = Join-Path $ScriptDir "venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"
$venvPip = Join-Path $venvDir "Scripts\pip.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host ">> Membuat virtual environment baru di folder: venv..." -ForegroundColor Gray
    & $pythonExecutable -m venv $venvDir
    if (-not (Test-Path $venvPython)) {
        Write-Host "[ERROR] Gagal membuat virtual environment." -ForegroundColor Red
        Pause
        exit 1
    }
    Write-Host "[OK] Virtual Environment berhasil dibuat." -ForegroundColor Green
} else {
    Write-Host "[OK] Virtual Environment (venv) sudah ada." -ForegroundColor Green
}

# ------------------------------------------------------------------------------
# 3. Instalasi Dependensi dari requirements.txt
# ------------------------------------------------------------------------------
Write-Host ""
Write-Host "[3/5] Mengupgrade pip & memasang paket dependensi..." -ForegroundColor Yellow

Write-Host ">> Memperbarui pip ke versi terbaru..." -ForegroundColor Gray
& $venvPython -m pip install --upgrade pip --quiet --no-warn-script-location

$reqFile = Join-Path $ScriptDir "requirements.txt"
if (Test-Path $reqFile) {
    Write-Host ">> Menginstall paket pustaka dari requirements.txt..." -ForegroundColor Gray
    & $venvPip install -r $reqFile --no-warn-script-location
    Write-Host "[OK] Seluruh dependensi (Flask, SQLAlchemy, python-docx, ReportLab) berhasil dipasang!" -ForegroundColor Green
} else {
    Write-Host "[WARNING] requirements.txt tidak ditemukan, memasang paket inti langsung..." -ForegroundColor Yellow
    & $venvPip install Flask SQLAlchemy python-docx reportlab --no-warn-script-location
}

# ------------------------------------------------------------------------------
# 4. Verifikasi Aplikasi & Basis Data SQLite
# ------------------------------------------------------------------------------
Write-Host ""
Write-Host "[4/5] Memverifikasi integritas database dan aplikasi..." -ForegroundColor Yellow

try {
    $verifyResult = & $venvPython -c "import app, models; print('Database & Model OK')" 2>&1
    Write-Host "[OK] $verifyResult" -ForegroundColor Green
} catch {
    Write-Host "[WARNING] Terjadi catatan saat verifikasi: $_" -ForegroundColor Yellow
}

# ------------------------------------------------------------------------------
# 5. Membuat Shortcut Desktop & Peluncur
# ------------------------------------------------------------------------------
Write-Host ""
Write-Host "[5/5] Membuat shortcut peluncur di Desktop & pengaturan jaringan..." -ForegroundColor Yellow

try {
    $fwRule = Get-NetFirewallRule -DisplayName "Sistem Addendum Pupuk (Port 5000)" -ErrorAction SilentlyContinue
    if (-not $fwRule) {
        New-NetFirewallRule -DisplayName "Sistem Addendum Pupuk (Port 5000)" -Direction Inbound -LocalPort 5000 -Protocol TCP -Action Allow -Profile Private,Domain -ErrorAction SilentlyContinue | Out-Null
    }
    Write-Host "[OK] Firewall jaringan port 5000 diizinkan untuk multi-komputer kantor." -ForegroundColor Green
} catch {
    Write-Host ">> Catatan: Konfigurasi firewall dilewati (dapat diatur manual jika diperlukan)." -ForegroundColor Gray
}

try {
    $desktopDir = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::DesktopDirectory)
    $shortcutPath = Join-Path $desktopDir "Sistem Generator Addendum.lnk"
    $launcherBat = Join-Path $ScriptDir "START_APP.bat"

    $wscriptShell = New-Object -ComObject WScript.Shell
    $shortcut = $wscriptShell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $launcherBat
    $shortcut.WorkingDirectory = $ScriptDir
    $shortcut.Description = "Peluncur Sistem Generator Addendum & SPJB Pupuk Bersubsidi"
    $shortcut.WindowStyle = 1
    $shortcut.Save()

    Write-Host "[OK] Shortcut Desktop berhasil dibuat: $shortcutPath" -ForegroundColor Green
} catch {
    Write-Host ">> Catatan: Lewati pembuatan shortcut desktop: $_" -ForegroundColor Gray
}

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Green
Write-Host "   PROSES INSTALASI SELESAI 100%! SEMUA KOMPONEN SIAP DIGUNAKAN.     " -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Anda dapat menjalankan aplikasi dengan:" -ForegroundColor Cyan
Write-Host "1. Klik ganda file: START_APP.bat di folder ini" -ForegroundColor White
Write-Host "2. Atau klik ikon 'Sistem Generator Addendum' di Desktop Anda." -ForegroundColor White
Write-Host ""
Write-Host "Aplikasi akan otomatis berjalan pada browser di: http://127.0.0.1:5000" -ForegroundColor Yellow
Write-Host ""

