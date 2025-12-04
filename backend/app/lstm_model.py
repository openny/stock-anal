import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, Input
from sklearn.preprocessing import MinMaxScaler

class LSTMForecaster:
    def __init__(self, lookback=60, forecast_days=100):
        """
        lookback:  학습할 때 사용하는 과거 일수 (시퀀스 길이)
        forecast_days: 미래 예측할 일수
        """
        self.lookback = lookback
        self.forecast_days = forecast_days
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        self.model = None

    def create_model(self, input_shape):
        """
        LSTM 모델 구성
        """
        print(f"[LSTM] Creating model with input_shape={input_shape}", flush=True)

        model = Sequential()
        model.add(Input(shape=input_shape))
        model.add(LSTM(50, return_sequences=True))
        model.add(Dropout(0.2))
        model.add(LSTM(50, return_sequences=False))
        model.add(Dropout(0.2))
        model.add(Dense(25))
        model.add(Dense(1))

        model.compile(optimizer='adam', loss='mean_squared_error')

        print("[LSTM] Model created successfully", flush=True)
        return model

    def prepare_data(self, data):
        """
        LSTM 입력 데이터를 생성:
        - MinMaxScaler로 정규화
        - lookback 길이 만큼 X 시퀀스 생성
        - 다음날 가격을 y로 설정
        """
        print(f"[LSTM] Preparing data... raw_length={len(data)}", flush=True)

        # (N,) → (N, 1) 로 reshape 후 scaling
        scaled_data = self.scaler.fit_transform(data.reshape(-1, 1))
        print(f"[LSTM] Scaled data shape={scaled_data.shape}", flush=True)

        x_train, y_train = [], []

        # lookback 길이로 sliding window 생성
        for i in range(self.lookback, len(scaled_data)):
            x_train.append(scaled_data[i - self.lookback:i, 0])  # 과거 60일
            y_train.append(scaled_data[i, 0])                   # 해당 날짜의 가격

        x_train = np.array(x_train)
        y_train = np.array(y_train)

        print(f"[LSTM] x_train shape={x_train.shape}, y_train shape={y_train.shape}", flush=True)
        return x_train, y_train, scaled_data

    def train_and_predict(self, prices):
        """
        LSTM 학습 + 100일 재귀 예측
        """
        print(f"[LSTM] ====== train_and_predict START ======", flush=True)
        print(f"[LSTM] Received price data length={len(prices)}", flush=True)

        # 1) 데이터 준비
        x_train, y_train, scaled_data = self.prepare_data(prices.values)

        # LSTM 입력형태로 변환: (samples, lookback, feature=1)
        x_train = x_train.reshape(x_train.shape[0], x_train.shape[1], 1)
        print(f"[LSTM] x_train reshaped={x_train.shape}", flush=True)

        # 2) 모델 생성
        self.model = self.create_model((x_train.shape[1], 1))

        # 3) 학습
        print("[LSTM] Training model... (epochs=5)", flush=True)
        self.model.fit(x_train, y_train, batch_size=32, epochs=5, verbose=0)
        print("[LSTM] Training finished", flush=True)

        # 4) 재귀적 예측 준비
        last_sequence = scaled_data[-self.lookback:]       # 최근 60일
        current_batch = last_sequence.reshape((1, self.lookback, 1))

        print(f"[LSTM] Starting recursive forecast... days={self.forecast_days}", flush=True)
        predicted = []

        # 5) 미래 예측 (recursive prediction)
        for step in range(self.forecast_days):
            current_pred = self.model.predict(current_batch, verbose=0)
            pred_value = current_pred[0, 0]
            predicted.append(pred_value)

            # 로그 출력
            if step < 5 or step % 20 == 0:
                print(f"[LSTM] Step {step}: scaled_pred={pred_value}", flush=True)

            # 다음 input을 위해 예측값을 시퀀스 뒤에 추가
            pred_reshaped = current_pred.reshape(1, 1, 1)
            current_batch = np.append(current_batch[:, 1:, :], pred_reshaped, axis=1)

        # 6) 스케일 되돌리기
        predicted_array = np.array(predicted).reshape(-1, 1)
        final_predictions = self.scaler.inverse_transform(predicted_array).flatten()

        print(f"[LSTM] Forecast completed. Output length={len(final_predictions)}", flush=True)
        print("[LSTM] ====== train_and_predict END ======\n", flush=True)

        return final_predictions