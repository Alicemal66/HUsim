#!/bin/bash
set -e

echo ""
echo "  ============================================="
echo "   HÜsim — Maden Simülasyon Kontrol Sistemi"
echo "  ============================================="
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- Backend ---
echo "[1/2] Backend başlatılıyor..."
cd "$SCRIPT_DIR/backend"

if [ ! -d "venv" ]; then
    echo "  Python sanal ortam oluşturuluyor..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt -q
uvicorn main:app --reload --port 8002 --host 0.0.0.0 &
BACKEND_PID=$!
echo "  ✅ Backend hazır: http://localhost:8002"

# --- Bekleme ---
sleep 2

# --- Frontend ---
echo "[2/2] Frontend başlatılıyor..."
cd "$SCRIPT_DIR/frontend"

if [ ! -d "node_modules" ]; then
    echo "  npm bağımlılıklar yükleniyor..."
    npm install --silent
fi

npm run dev &
FRONTEND_PID=$!
echo "  ✅ Frontend hazır: http://localhost:5173"

echo ""
echo "  ============================================="
echo "   🎯 HÜsim açık: http://localhost:5173"
echo "   📡 API Docs: http://localhost:8002/docs"
echo "   Kapatmak için Ctrl+C"
echo "  ============================================="
echo ""

cleanup() {
    echo "HÜsim kapatılıyor..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM
wait
