#!/bin/bash
echo ">>> Starting 4D Fusion System..."

# Backend 실행 (Background)
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000 &

# Frontend 실행
cd ../frontend
npm run dev &

wait