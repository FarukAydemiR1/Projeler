@echo off
REM ==== Viral Urun Ajani - Telegram botunu baslat ====
REM Once bir kez kur.bat calistirilmis ve .env doldurulmus olmalidir.
cd /d "%~dp0"

if not exist .venv\Scripts\activate.bat (
  echo HATA: Once kur.bat dosyasina cift tiklayin (kurulum yapilmamis).
  pause
  exit /b 1
)

call .venv\Scripts\activate.bat
echo Bot baslatiliyor... Durdurmak icin bu pencerede Ctrl+C.
echo.
python bot.py
echo.
echo Bot durdu. Kapatmak icin bir tusa basin.
pause
