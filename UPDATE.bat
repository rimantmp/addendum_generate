@echo off
title Pembaruan Sistem dari GitHub - CV. Subur Anugerah Sejahtera
cd /d "%~dp0"

echo ======================================================================
echo    MEMPERBARUI SISTEM DARI GITHUB RESMI
echo    CV. SUBUR ANUGERAH SEJAHTERA - KABUPATEN TANA TORAJA
echo ======================================================================
echo.

where git >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Git belum terpasang di komputer ini.
    echo Silakan unduh dan pasang Git terlebih dahulu dari: https://git-scm.com/
    pause
    exit /b 1
)

echo Mengambil pembaruan terbaru dari GitHub (git pull origin main)...
git pull origin main
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [PERHATIAN] Terjadi kendala saat melakukan git pull.
    echo Pastikan komputer terhubung ke internet dan tidak ada file yang bentrok.
    pause
    exit /b 1
)

echo.
echo Memeriksa dan memperbarui dependensi pustaka jika ada versi baru...
if exist "venv\Scripts\python.exe" (
    venv\Scripts\pip.exe install -r requirements.txt --quiet
)

echo.
echo ======================================================================
echo    PEMBARUAN BERHASIL 100%! 
echo    Silakan jalankan aplikasi dengan: START_APP.bat
echo ======================================================================
echo.
pause

