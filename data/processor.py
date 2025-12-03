import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import logging


class DataProcessor:
    """
    데이터 전처리, 파생변수 생성, 정규화를 담당하는 클래스.
    """

    def __init__(self):
        # 데이터 정규화를 위한 Scaler 초기화 (0~1 사이 값으로 변환)
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        self.scaler_fitted = False

    def calculate_net_liquidity(self, fred_df: pd.DataFrame) -> pd.DataFrame:
        """
        연준의 순유동성(Net Liquidity)을 계산한다.
        공식: Net Liquidity = WALCL (연준 총자산) - WTREGEN (재무부 일반계정 TGA) - RRPONTSYD (역레포)

        Args:
            fred_df (pd.DataFrame): FRED 데이터프레임

        Returns:
            pd.DataFrame: Net_Liquidity 컬럼이 포함된 데이터프레임
        """
        required_cols = ['WALCL', 'WTREGEN', 'RRPONTSYD']

        # 필수 컬럼 존재 여부 확인
        missing_cols = [col for col in required_cols if col not in fred_df.columns]
        if missing_cols:
            raise ValueError(f"순유동성 계산을 위한 필수 컬럼이 누락되었습니다: {missing_cols}")

        df = fred_df.copy()

        # FRED 데이터 단위 조정
        # WALCL, WTREGEN: 백만 달러 (Millions of U.S. Dollars)
        # RRPONTSYD: 십억 달러 (Billions of U.S. Dollars) -> 단위 통일 필요
        # 참고: RRPONTSYD의 단위는 수집 시점에 따라 다를 수 있으므로 FRED 메타데이터 확인 필요.
        # 여기서는 FRED 기본 단위인 Billions를 Millions로 변환하여 계산한다고 가정.
        # WALCL(Mil) - WTREGEN(Mil) - RRPONTSYD(Bil * 1000)

        # 실제 데이터 값을 확인해보고 단위를 맞춰야 하지만, 통상적으로 FRED API는 메타데이터 단위를 따름.
        # RRPONTSYD가 Billions라면 1000을 곱해야 Millions가 됨.

        df['Net_Liquidity'] = df['WALCL'] - df['WTREGEN'] - (df['RRPONTSYD'] * 1000)

        logging.info("순유동성 지표 계산 완료")
        return df

    def prepare_lstm_dataset(self, data: pd.DataFrame, target_col: str, n_past: int, n_future: int):
        """
        LSTM 학습을 위한 시계열 데이터셋 생성 (Sliding Window 방식).

        Args:
            data (pd.DataFrame): 전체 시계열 데이터
            target_col (str): 예측 대상 컬럼명 (예: 'Close')
            n_past (int): 과거 참조 기간 (Input Sequence Length)
            n_future (int): 미래 예측 기간 (Output Sequence Length)

        Returns:
            X (np.array): 입력 데이터 (samples, n_past, features)
            y (np.array): 타겟 데이터 (samples, n_future, 1)
            scaler (MinMaxScaler): 역변환을 위한 스케일러 객체
        """
        # 데이터 스케일링
        if not self.scaler_fitted:
            scaled_data = self.scaler.fit_transform(data)
            self.scaler_fitted = True
        else:
            scaled_data = self.scaler.transform(data)

        target_idx = data.columns.get_loc(target_col)

        X, y = [], []

        # 슬라이딩 윈도우 적용
        for i in range(n_past, len(scaled_data) - n_future + 1):
            X.append(scaled_data[i - n_past:i, :])  # 과거 n_past 만큼의 모든 피처
            y.append(scaled_data[i:i + n_future, target_idx])  # 미래 n_future 만큼의 타겟 변수

        X = np.array(X)
        y = np.array(y)

        # 타겟 데이터 차원 확장: (Samples, Steps) -> (Samples, Steps, 1)
        # main.py에서 y_test[:, :, 0]으로 접근하기 위해 3차원으로 맞춤
        if y.ndim == 2:
            y = np.expand_dims(y, axis=-1)

        return X, y, self.scaler