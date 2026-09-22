@echo off
REM ==== Nemotron Sohbet - baslat ====
REM Once bir kez kur.bat calistirilmis ve .env doldurulmus olmalidir.
cd /d "%~dp0"
chcp 65001 >nul 2>&1

if not exist .venv\Scripts\activate.bat (
  echo HATA: Once kur.bat dosyasina cift tiklayin (kurulum yapilmamis).
  pause
  exit /b 1
)

call .venv\Scripts\activate.bat
python sohbet.py %*
echo.
pause
