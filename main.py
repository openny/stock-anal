import argparse
import pandas as pd
import numpy as np
from data.data_loader import DataLoader
from data.processor import DataProcessor
from models.lstm_forecaster import LSTMForecaster
from visualization.plotter import Visualizer
import logging
import sys


def main():
    # 명령행 인자 파싱
    parser = argparse.ArgumentParser(description="Financial Time Series Forecasting System")
    parser.add_argument('--ticker', type=str, default='AAPL', help='Stock Ticker Symbol (e.g., AAPL, SPY)')
    parser.add_argument('--start_date', type=str, default='2018-01-01', help='Start Date (YYYY-MM-DD)')
    parser.add_argument('--epochs', type=int, default=50, help='Training Epochs')
    args = parser.parse_args()

    # 로깅 설정
    logging.info(f"=== 시스템 시작: {args.ticker} 예측 프로세스 ===")

    try:
        # 1. 데이터 수집 단계
        loader = DataLoader(args.start_date)

        # FRED 데이터 수집 (거시경제 지표)
        # WALCL: 연준 총자산, WTREGEN: TGA, RRPONTSYD: 역레포, DGS10: 10년물 국채금리, FEDTARMD: 점도표 중간값
        logging.info("거시경제 데이터 수집 중...")
        # 참고: FEDTARMD는 연간 데이터이므로 ffill로 일간 변환됨
        series_ids = ['WALCL', 'WTREGEN', 'RRPONTSYD', 'DGS10', 'FEDTARMD']
        fred_data = loader.get_fred_data(series_ids)

        # 주식 데이터 수집
        logging.info(f"주식 데이터 수집 중 ({args.ticker})...")
        stock_data = loader.get_stock_data(args.ticker)

        # 2. 데이터 전처리 단계
        processor = DataProcessor()

        # Net Liquidity (순유동성) 계산
        net_liquidity = processor.calculate_net_liquidity(fred_data)

        # 데이터 병합 (Inner Join으로 날짜 교집합만 사용)
        # 주가(종가) + 순유동성 + 10년물 금리 + 점도표
        merged_df = stock_data[['Close']].join(net_liquidity).dropna()
        logging.info(f"데이터 병합 완료. Shape: {merged_df.shape}")

        if len(merged_df) < 200:
            logging.warning("데이터 샘플 수가 너무 적습니다. 예측 신뢰도가 낮을 수 있습니다.")

        # LSTM 데이터셋 준비
        # 과거 60일(약 3달)의 데이터를 보고, 향후 30일(약 1달)을 예측
        n_past = 60
        n_future = 30
        target_col = 'Close'

        X, y, scaler = processor.prepare_lstm_dataset(merged_df, target_col, n_past, n_future)

        # 학습/테스트 데이터 분할 (80:20)
        split_idx = int(len(X) * 0.8)
        X_train, y_train = X[:split_idx], y[:split_idx]
        X_test, y_test = X[split_idx:], y[split_idx:]

        logging.info(f"학습 데이터: {X_train.shape}, 테스트 데이터: {X_test.shape}")

        # 3. 모델 학습 단계
        # X shape: (samples, n_past, features) 이므로 features는 index 2입니다.
        n_features = X_train.shape[2]
        forecaster = LSTMForecaster(n_past, n_future, n_features)

        history = forecaster.train(X_train, y_train, epochs=args.epochs)
        Visualizer.plot_training_history(history)

        # 4. 예측 및 시각화 단계
        # Fan Chart 생성을 위해 Monte Carlo Dropout 등을 사용할 수 있으나,
        # 여기서는 테스트 셋의 잔차(Residual) 분포를 활용하여 불확실성을 시뮬레이션함.

        # 가장 최근 데이터 시퀀스 가져오기 (실제 미래 예측용)
        last_sequence = X[-1:]
        base_forecast = forecaster.predict(last_sequence)  # Shape: (1, 30, 1)

        # 스케일링 역변환 함수 정의
        target_idx = merged_df.columns.get_loc(target_col)
        data_min = scaler.data_min_[target_idx]
        data_max = scaler.data_max_[target_idx]

        def inverse_transform_target(scaled_val):
            return scaled_val * (data_max - data_min) + data_min

        # 기준 예측값 역변환
        base_forecast_vals = inverse_transform_target(base_forecast.reshape(-1))

        # 불확실성 추정 (잔차 기반 시뮬레이션)
        # 테스트 셋에서의 예측 오차 표준편차 계산
        test_pred = forecaster.predict(X_test)
        residuals = y_test[:, :, 0] - test_pred[:, :, 0]  # 단순 차이
        std_dev = np.std(residuals)

        # 1000번의 시뮬레이션 수행 (Random Walk Noise 추가)
        simulations = []
        for _ in range(1000):
            # 시간에 따라 불확실성이 증가하도록 노이즈 스케일링 (Square Root of Time Rule)
            noise = np.random.normal(0, std_dev, size=n_future) * np.sqrt(np.arange(1, n_future + 1))
            # 정규화된 상태에서의 노이즈 추가 후 역변환
            sim_path_scaled = base_forecast.reshape(-1) + noise
            sim_path = inverse_transform_target(sim_path_scaled)
            simulations.append(sim_path)

        forecast_matrix = np.array(simulations)

        # 날짜 생성
        last_date = merged_df.index[-1]
        forecast_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=n_future)

        # 시각화를 위한 과거 데이터 (최근 120일)
        hist_days = 120
        hist_dates = merged_df.index[-hist_days:]
        hist_vals = merged_df[target_col].values[-hist_days:]

        Visualizer.plot_fan_chart(
            hist_dates, hist_vals,
            forecast_dates, forecast_matrix,
            title=f"{args.ticker} Price Forecast (30 Days)"
        )

        logging.info("=== 모든 프로세스가 성공적으로 완료되었습니다. Output 이미지를 확인하세요. ===")

    except Exception as e:
        logging.error(f"시스템 실행 중 오류 발생: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()