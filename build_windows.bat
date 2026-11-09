@echo off
setlocal enabledelayedexpansion

echo ====================================================================
echo     BUILD CLOUDFLARE REDIRECT MANAGER - WINDOWS STANDALONE EXE
echo ====================================================================
echo.

REM 1. Periksa ketersediaan Python
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python tidak terdeteksi di sistem PATH!
    echo Silakan instal Python 3.12 atau yang lebih baru dari https://www.python.org/
    echo Pastikan opsi "Add Python to PATH" dicentang saat instalasi.
    pause
    exit /b 1
)

echo [1/6] Memeriksa versi Python...
python --version

REM 2. Menyiapkan Virtual Environment
echo.
echo [2/6] Menyiapkan Virtual Environment (venv)...
if not exist "venv" (
    echo Membuat virtual environment baru di .\venv...
    python -m venv venv
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Gagal membuat virtual environment.
        pause
        exit /b 1
    )
) else (
    echo Virtual environment venv sudah ada.
)

REM Aktifkan venv
call venv\Scripts\activate.bat

REM 3. Instal dependensi
echo.
echo [3/6] Menginstal dan memperbarui dependensi (requirements-dev.txt)...
python -m pip install --upgrade pip --quiet
if exist "requirements-dev.txt" (
    pip install -r requirements-dev.txt --quiet
) else (
    pip install -r requirements.txt --quiet
)
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Gagal menginstal dependencies.
    pause
    exit /b 1
)
echo Dependensi berhasil diverifikasi.

REM 4. Pemeriksaan Sintaks dan Import
echo.
echo [4/6] Memeriksa sintaks kode dan modul...
python -c "import PySide6, httpx, pytest, PyInstaller; print('Semua dependensi inti terinstal dengan benar.')"
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Gagal memverifikasi modul impor inti.
    pause
    exit /b 1
)

REM 5. Menjalankan Unit Tests
echo.
echo [5/6] Menjalankan Unit Tests (pytest)...
pytest -v
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Pengujian unit tests gagal! Build EXE dibatalkan demi keamanan kode.
    pause
    exit /b 1
)
echo Semua pengujian unit tests BERHASIL!

REM 6. Build Executable menggunakan PyInstaller
echo.
echo [6/6] Membangun file mandiri EXE menggunakan PyInstaller...
echo Mode: Windowed (noconsole), Onefile, Clean...

pyinstaller --noconsole --onefile --name "CloudflareRedirectManager" --clean src\main.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ====================================================================
    echo [ERROR] Proses PyInstaller GAGAL!
    echo ====================================================================
    echo Periksa pesan log di atas untuk informasi kesalahan.
    pause
    exit /b 1
)

echo.
if exist "dist\CloudflareRedirectManager.exe" (
    echo ====================================================================
    echo [SUKSES] BUILD BERHASIL DISELESAIKAN!
    echo ====================================================================
    echo File Executable Mandiri:
    echo %CD%\dist\CloudflareRedirectManager.exe
    echo.
    echo CATATAN PENTING:
    echo - File EXE ini adalah aplikasi mandiri untuk Windows 10/11 64-bit.
    echo - Token API TIDAK ditanam di dalam executable ini.
    echo - Executable ini belum ditandatangani secara digital (Self/Unsigned).
    echo   Jika Windows SmartScreen muncul, klik "More info" -> "Run anyway".
    echo ====================================================================
) else (
    echo [ERROR] File dist\CloudflareRedirectManager.exe tidak ditemukan setelah build.
    pause
    exit /b 1
)

echo.
pause
