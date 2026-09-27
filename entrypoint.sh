#!/bin/bash
set -e

# Port configuration (Streamlit will listen on $PORT if provided by cloud host, else default to 8501)
PORT=${PORT:-8501}
BACKEND_PORT=8000

echo "🚀 Starting DevHandoff backend on port $BACKEND_PORT..."
python -m uvicorn backend.main:app --host 127.0.0.1 --port $BACKEND_PORT &

# Wait for backend to be ready
echo "⏳ Waiting for backend health check..."
for i in {1..30}; do
    if curl -s "http://127.0.0.1:$BACKEND_PORT/health" > /dev/null 2>&1; then
        echo "✅ Backend is healthy and ready!"
        break
    fi
    sleep 1
done

echo "🌟 Launching DevHandoff Streamlit frontend on port $PORT..."
exec python -m streamlit run frontend/app.py \
    --server.port="$PORT" \
    --server.address="0.0.0.0" \
    --server.headless=true \
    --browser.gatherUsageStats=false
