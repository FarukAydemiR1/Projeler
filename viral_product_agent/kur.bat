@echo off
REM ==== Viral Urun Ajani - Windows tek seferlik kurulum ====
REM Bu dosyaya CIFT TIKLAYIN. Python'un kurulu olmasi gerekir (python.org).
cd /d "%~dp0"

echo.
echo === Python kontrol ediliyor ===
py --version >nul 2>&1
if errorlevel 1 (
  python --version >nul 2>&1
  if errorlevel 1 (
    echo HATA: Python bulunamadi.
    echo python.org/downloads adresinden Python kurun ve kurulumda
    echo "Add python.exe to PATH" kutusunu ISARETLEYIN, sonra tekrar deneyin.
    pause
    exit /b 1
  )
  set PY=python
) else (
  set PY=py
)

echo.
echo === Sanal ortam olusturuluyor (.venv) ===
%PY% -m venv .venv

echo.
echo === Paketler kuruluyor (birkac dakika surebilir) ===
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

echo.
echo === .env dosyasi hazirlaniyor ===
if not exist .env copy .env.example .env >nul

echo.
echo ================================================================
echo  KURULUM TAMAM.
echo  1) .env dosyasini Not Defteri ile acin.
echo  2) TELEGRAM_BOT_TOKEN=... satirina BotFather token'inizi yapistirin.
echo  3) Kaydedin, sonra baslat.bat dosyasina cift tiklayin.
echo ================================================================
pause
