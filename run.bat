@echo off
title Cloudflare Redirect Manager
echo Menjalankan Cloudflare Redirect Manager...
py main.py
if errorlevel 1 (
    python main.py
)
pause
