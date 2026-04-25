@echo off
chcp 65001 > nul
echo.
echo  ╔════════════════════════════════════╗
echo  ║         HÜsim v1.0                ║
echo  ║  Maden Simülasyon Kontrol Sistemi ║
echo  ╚════════════════════════════════════╝
echo.

REM --- Backend ---
echo  [1/3] Backend baslatiliyor...
cd /d "%~dp0backend"

set PYTHON=%LocalAppData%\Programs\Python\Python310\python.exe

if not exist "venv" (
    echo  Python sanal ortam olusturuluyor...
    "%PYTHON%" -m venv venv
)

call venv\Scripts\activate.bat
pip install -r requirements.txt -q 2>nul

start "HUsim-Backend" cmd /k "call venv\Scripts\activate.bat && uvicorn main:app --reload --port 8002 --host 0.0.0.0"
echo  Backend baslatildi: http://localhost:8002

timeout /t 3 /nobreak > nul

REM --- Frontend ---
echo  [2/3] Frontend baslatiliyor...
cd /d "%~dp0frontend"

if not exist "node_modules" (
    echo  npm bagimliliklar yukleniyor...
    npm install --silent
)

start "HUsim-Frontend" cmd /k "npm run dev"
echo  Frontend baslatildi: http://localhost:5173

REM --- Tarayici ---
echo  [3/3] Tarayici aciliyor...
timeout /t 5 /nobreak > nul
start http://localhost:5173

echo.
echo  ════════════════════════════════════
echo    HUsim Hazir!
echo    http://localhost:5173
echo    API: http://localhost:8002/docs
echo    Kalibrasyon: http://localhost:8002/api/dataset/calibration
echo  ════════════════════════════════════
echo.
echo  Kapatmak icin bu pencereyi ve backend/frontend pencerelerini kapatin.
pause
