from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import asyncio
from .data_loader import DataLoader
from .fusion_engine import FusionEngine
from .lstm_model import LSTMForecaster
from .models import AnalysisResult, StockScore, ForecastData
import pandas as pd
import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 전역 상태 저장소
analysis_state = {
    "status": "IDLE",
    "progress": 0,
    "results": []
}


@app.post("/api/analyze", response_model=AnalysisResult)
async def start_analysis(
    background_tasks: BackgroundTasks,   # ⬅️ 기본값 없는 파라미터 먼저
    top_n: int = 5                       # ⬅️ 기본값 있는 파라미터 뒤
):
    if analysis_state["status"] == "RUNNING":
        return {
            "status": analysis_state["status"],
            "progress": analysis_state["progress"],
            "top_stocks": analysis_state["results"],
        }

    analysis_state["status"] = "RUNNING"
    analysis_state["progress"] = 0
    analysis_state["results"] = []

    print(f"[start_analysis] REQUEST top_n={top_n}", flush=True)

    background_tasks.add_task(run_full_analysis, top_n)

    return {
        "status": analysis_state["status"],
        "progress": analysis_state["progress"],
        "top_stocks": analysis_state["results"],
    }

@app.get("/api/status", response_model=AnalysisResult)
def get_status():
    return {
        "status": analysis_state["status"],
        "progress": analysis_state["progress"],
        "top_stocks": analysis_state["results"]
    }


@app.get("/api/forecast/{ticker}", response_model=ForecastData)
def get_forecast(ticker: str):
    loader = DataLoader()
    data = loader.get_batch_stock_data([ticker])

    # DataFrame 컬럼 처리 (yfinance 업데이트 대응)
    if isinstance(data.columns, pd.MultiIndex):
        df = data.xs(ticker, axis=1, level=1)
    else:
        df = data

    closes = df['Close'].dropna()

    forecaster = LSTMForecaster()
    predictions = forecaster.train_and_predict(closes)
    last_date = closes.index[-1]

    # 미래 날짜 생성 로직 추가 (예측 기간만큼 날짜 생성)
    future_dates = [
        (last_date + datetime.timedelta(days=i + 1)).strftime("%Y-%m-%d")
        for i in range(len(predictions))
    ]

    # 신뢰구간 (단순화를 위해 표준편차 기반 계산)
    std_dev = closes.pct_change().std() * closes.iloc[-1]
    upper = [p + (std_dev * (i ** 0.5)) for i, p in enumerate(predictions)]
    lower = [p - (std_dev * (i ** 0.5)) for i, p in enumerate(predictions)]

    return {
        "dates": future_dates,
        "historical": closes.values[-100:].tolist(),  # 최근 100일만 전송
        "forecast": predictions.tolist(),
        "lower_bound": lower,
        "upper_bound": upper
    }
@app.get("/api/analyze_single/{ticker}", response_model=StockScore)
def analyze_single(ticker: str):
    """
    단일 티커에 대해 4D Fusion 점수와 매크로 레짐 등을 바로 계산해서 반환
    """
    print(f"[analyze_single] ticker={ticker}", flush=True)

    loader = DataLoader()

    # 1) 매크로 데이터 로드 + FusionEngine 생성
    macro_df = loader.get_macro_data()
    engine = FusionEngine(macro_df)

    # 2) 가격 데이터 로드
    data = loader.get_batch_stock_data([ticker])

    # MultiIndex → 단일 DF 추출 (이미 main.py 어딘가에 있는 helper 재사용)
    from .main import extract_ticker_df  # 같은 파일이면 import 말고 그냥 호출만

    df = extract_ticker_df(data, ticker)
    if df is None or df.empty:
        raise HTTPException(status_code=400, detail=f"{ticker} price data not found")

    # 3) 펀더멘털 데이터 로드
    info = loader.get_fundamentals(ticker)

    # 4) 점수 계산
    score_obj = engine.calculate_scores(ticker, df, info)
    if not score_obj:
        raise HTTPException(status_code=400, detail=f"{ticker} score calculation failed")

    print(f"[analyze_single] done: {ticker}, fusion={score_obj['fusion_score']}", flush=True)
    return score_obj

def extract_ticker_df(data: pd.DataFrame, ticker: str) -> pd.DataFrame | None:
    """
    get_batch_stock_data([ticker]) 결과에서 해당 ticker의 OHLCV DataFrame을 추출.
    MultiIndex 구조(level 0/1 어떤 쪽에 ticker가 있든지 대응).
    """
    if data is None or data.empty:
        print(f"[extract_ticker_df] data is empty for {ticker}", flush=True)
        return None

    # 단일 인덱스 컬럼이면 그대로 사용
    if not isinstance(data.columns, pd.MultiIndex):
        print(f"[extract_ticker_df] non-MultiIndex for {ticker}, using data as-is", flush=True)
        return data

    lvl0 = data.columns.get_level_values(0)
    lvl1 = data.columns.get_level_values(1)

    print(
        f"[extract_ticker_df] ticker={ticker}, "
        f"lvl0_sample={list(lvl0.unique())[:5]}, "
        f"lvl1_sample={list(lvl1.unique())[:5]}",
        flush=True,
    )

    # 정확 매칭 먼저 시도
    if ticker in lvl0:
        print(f"[extract_ticker_df] {ticker} found in level 0", flush=True)
        return data.xs(ticker, axis=1, level=0)
    if ticker in lvl1:
        print(f"[extract_ticker_df] {ticker} found in level 1", flush=True)
        return data.xs(ticker, axis=1, level=1)

    # 정확 매칭이 없으면, prefix 기준으로 느슨하게 한번 더 시도 (예: 'CI US Equity' 같은 경우)
    lvl0_str = [str(v) for v in lvl0.unique()]
    lvl1_str = [str(v) for v in lvl1.unique()]

    match0 = [v for v in lvl0_str if v.startswith(ticker)]
    match1 = [v for v in lvl1_str if v.startswith(ticker)]

    if match0:
        key = match0[0]
        print(f"[extract_ticker_df] {ticker} matched (prefix) in level 0: {key}", flush=True)
        return data.xs(key, axis=1, level=0)
    if match1:
        key = match1[0]
        print(f"[extract_ticker_df] {ticker} matched (prefix) in level 1: {key}", flush=True)
        return data.xs(key, axis=1, level=1)

    print(f"[extract_ticker_df] {ticker} not found in MultiIndex levels", flush=True)
    return None


def run_full_analysis(top_n: int):
    print("[run_full_analysis] started", flush=True)
    try:
        loader = DataLoader()

        # 1. Macro Data (D1)
        macro_df = loader.get_macro_data()
        engine = FusionEngine(macro_df)
        analysis_state["progress"] = 10
        print("[run_full_analysis] macro loaded", flush=True)

        # 2. Get Tickers
        tickers = loader.get_sp500_tickers()
        tickers = tickers[:10]  # 샘플링
        total = len(tickers) or 1
        print(f"[run_full_analysis] tickers={len(tickers)}", flush=True)

        scored_stocks: list[StockScore] = []

        # 3. 각 티커별로 개별 다운로드 + 스코어 계산
        for idx, ticker in enumerate(tickers):
            try:
                print(f"[run_full_analysis] processing {ticker}", flush=True)

                data = loader.get_batch_stock_data([ticker])

                df = extract_ticker_df(data, ticker)
                if df is None or df.empty:
                    print(f"[run_full_analysis] {ticker} df empty or not found", flush=True)
                    continue

                # Fundamentals (D2)
                info = loader.get_fundamentals(ticker)

                score_obj = engine.calculate_scores(ticker, df, info)
                if score_obj:
                    scored_stocks.append(StockScore(**score_obj))

                # 진행률 업데이트 (10 ~ 100 사이)
                analysis_state["progress"] = 10 + int((idx + 1) / total * 90)

            except Exception as e:
                print(f"[run_full_analysis] Error analyzing {ticker}: {e}", flush=True)
                continue

        # 4. Sort & Select Top N
        scored_stocks.sort(key=lambda x: x.fusion_score, reverse=True)
        analysis_state["results"] = scored_stocks[:top_n]
        analysis_state["status"] = "COMPLETED"
        analysis_state["progress"] = 100

        print(
            f"[run_full_analysis] completed, results={len(analysis_state['results'])}",
            flush=True,
        )

    except Exception as e:
        print(f"[run_full_analysis] FATAL ERROR: {e}", flush=True)
        analysis_state["status"] = "FAILED"
        analysis_state["progress"] = 0
        analysis_state["results"] = []