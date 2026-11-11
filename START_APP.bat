@echo off
title Sistem Generator Addendum - CV. Subur Anugerah Sejahtera
cd /d "%~dp0"

echo ======================================================================
echo    MEMULAI SISTEM GENERATOR ADDENDUM & SPJB PUPUK BERSUBSIDI
echo    CV. SUBUR ANUGERAH SEJAHTERA - KABUPATEN TANA TORAJA
echo ======================================================================
echo.

:: Periksa apakah venv sudah ada
if not exist "venv\Scripts\python.exe" (
    echo [PERHATIAN] Lingkungan virtual (venv) belum ditemukan.
    echo Menjalankan instalasi awal otomatis sekarang...
    call INSTALL.bat
    if not exist "venv\Scripts\python.exe" (
        echo [ERROR] Instalasi belum selesai. Silakan periksa koneksi dan coba lagi.
        pause
        exit /b 1
    )
)

echo Membuka browser web di http://127.0.0.1:5000 ...
start "" "http://127.0.0.1:5000"

echo Menjalankan server aplikasi...
echo Tekan CTRL+C pada jendela ini jika ingin menghentikan aplikasi.
echo.
venv\Scripts\python.exe app.py

pause
