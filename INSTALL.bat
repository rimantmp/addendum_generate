@echo off
setlocal enabledelayedexpansion
title Pemasang Sistem Generator Addendum & SPJB Pupuk
cd /d "%~dp0"

echo ======================================================================
echo    MEMULAI PEMASANGAN SISTEM GENERATOR ADDENDUM & SPJB
echo    CV. SUBUR ANUGERAH SEJAHTERA - KABUPATEN TANA TORAJA
echo ======================================================================
echo.

:: Coba jalankan via PowerShell installer otomatis (disertai auto-download Python)
powershell -ExecutionPolicy Bypass -NoProfile -File "%~dp0install.ps1"
if %ERRORLEVEL% EQU 0 (
    echo.
    echo Tekan tombol apa saja untuk keluar atau jalankan START_APP.bat sekarang.
    pause
    exit /b 0
)

:: Jika powershell gagal atau dibatasi, fallback ke batch installer langsung
echo.
echo [INFO] Berpindah ke mode instalasi fallback langsung (CMD)...
echo.

:: 1. Cek Python
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [PERHATIAN] Python belum terdeteksi di PATH.
    echo Mengunduh installer Python 3.12 dari python.org...
    curl -L -o "%TEMP%\python-installer.exe" "https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe"
    if exist "%TEMP%\python-installer.exe" (
        echo Memasang Python 3.12...
        "%TEMP%\python-installer.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0 SimpleInstall=1
        del "%TEMP%\python-installer.exe"
        set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%PATH%"
    ) else (
        echo [ERROR] Gagal mengunduh Python. Silakan pasang Python 3.10+ secara manual dari python.org.
        pause
        exit /b 1
    )
)

:: 2. Buat venv
echo Membuat Virtual Environment (venv)...
python -m venv venv
if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Gagal membuat virtual environment.
    pause
    exit /b 1
)

:: 3. Install Dependensi
echo Mengupgrade pip dan memasang dependensi...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

:: 4. Verifikasi
python -c "import app; print('Aplikasi siap digunakan!')"

echo.
echo ======================================================================
echo    INSTALASI SELESAI! SILAKAN JALANKAN: START_APP.bat
echo ======================================================================
echo.
pause
