4D Fusion Stock Predictor
S&P 500 종목을 대상으로 Macro, Fundamental, Quant, Timing 4가지 차원을 분석하고 LSTM으로 100일 주가를 예측하는 시스템입니다.

Features
4D Fusion Model: 거시경제(Fed Liquidity), 재무제표, 기술적 지표를 결합한 랭킹 시스템.

LSTM Forecasting: TensorFlow 기반의 재귀적(Recursive) 100일 주가 예측.

Batch Processing: Python ThreadPoolExecutor를 사용한 고성능 데이터 수집.

Interactive UI: React & Recharts 기반의 실시간 대시보드.

Quick Start
chmod +x setup.sh run.sh

./setup.sh (최초 1회)

./run.sh

브라우저에서 http://localhost:5173 접속

Technology
Backend: FastAPI, TensorFlow(Keras), yfinance, Pandas

Frontend: React, Vite, Recharts, TailwindCSS