@echo off
cd /d "%~dp0"
title Sarrafiye Canli sunucusu
echo Sarrafiye Canli calisiyor. Yayin sayfasi: http://localhost:8000/yayin.html
echo Bu pencereyi kapatmayin.
:loop
python app.py
echo Sunucu durdu, 5 sn sonra yeniden baslatiliyor...
timeout /t 5 /nobreak >nul
goto loop
