import pytest
import pandas as pd
import numpy as np
from data.processor import DataProcessor
from models.lstm_forecaster import LSTMForecaster


# Fixture: 테스트에 사용할 가상 데이터 생성
@pytest.fixture
def sample_fred_data():
    dates = pd.date_range(start='2023-01-01', periods=10)
    data = pd.DataFrame({
        'WALCL': np.linspace(8000, 9000, 10),
        'WTREGEN': np.linspace(500, 400, 10),
        'RRPONTSYD': np.linspace(2000, 1500, 10)
    }, index=dates)
    return data


@pytest.fixture
def sample_market_data():
    dates = pd.date_range(start='2023-01-01', periods=100)
    data = pd.DataFrame({
        'Close': np.random.rand(100) * 100 + 100,
        'Net_Liquidity': np.random.rand(100) * 5000,
        'DGS10': np.random.rand(100) * 4
    }, index=dates)
    return data


def test_net_liquidity_calculation(sample_fred_data):
    """
    순유동성(Net Liquidity) 계산 로직 검증.
    공식: WALCL - WTREGEN - RRPONTSYD 가 정확히 수행되는지 확인.
    """
    processor = DataProcessor()
    result = processor.calculate_net_liquidity(sample_fred_data)

    # 첫 번째 행 계산 검증 (가정: 단위가 이미 맞춰져 있다고 볼 때)
    # WALCL(8000) - WTREGEN(500) - RRPONTSYD(2000) = 5500
    # 주의: Processor 코드 내 단위 변환 로직에 따라 값이 달라질 수 있으므로,
    # 테스트 코드도 그 로직(Billions -> Millions)에 맞춰야 함.
    # 여기서는 processor.py의 로직이 raw calculation이라고 가정하고 검증

    expected_val = 8000 - 500 - 2000
    # Processor 구현에 따라 컬럼명이 다를 수 있음
    assert 'Net_Liquidity_Raw' in result.columns
    # 부동소수점 오차 고려하여 approx 사용
    assert result.iloc == pytest.approx(expected_val)


def test_lstm_dataset_shape(sample_market_data):
    """
    LSTM 입력 데이터셋의 차원(Shape) 검증.
    (Samples, TimeSteps, Features) 형태가 맞는지 확인.
    """
    processor = DataProcessor()
    n_past = 10
    n_future = 5
    target_col = 'Close'

    X, y, _ = processor.prepare_lstm_dataset(sample_market_data, target_col, n_past, n_future)

    # 예상 샘플 수: 전체 데이터 길이 - (과거참조 + 미래예측) + 1
    expected_samples = len(sample_market_data) - n_past - n_future + 1
    n_features = sample_market_data.shape[2]

    assert X.shape == (expected_samples, n_past, n_features)
    assert y.shape == (expected_samples, n_future)  # 단변량 타겟


def test_model_architecture():
    """
    LSTM 모델의 입출력 레이어 차원 검증.
    """
    n_past = 20
    n_future = 10
    n_features = 3

    forecaster = LSTMForecaster(n_past, n_future, n_features)
    model = forecaster.model

    # 입력 레이어 shape 확인 (None, n_past, n_features)
    input_shape = model.input_shape
    assert input_shape == (None, n_past, n_features)

    # 출력 레이어 shape 확인 (None, n_future, 1)
    output_shape = model.output_shape
    assert output_shape == (None, n_future, 1)