import tensorflow as tf
from tensorflow.keras.models import Sequential, Model
from tensorflow.keras.layers import LSTM, Dense, RepeatVector, TimeDistributed, Input, Dropout
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
import logging


class LSTMForecaster:
    """
    LSTM Encoder-Decoder 기반의 시계열 예측 모델 클래스.
    """

    def __init__(self, n_past, n_future, n_features):
        """
        모델 초기화 및 빌드.

        Args:
            n_past (int): 과거 참조 윈도우 크기
            n_future (int): 미래 예측 윈도우 크기
            n_features (int): 입력 피처의 개수
        """
        self.n_past = n_past
        self.n_future = n_future
        self.n_features = n_features
        self.model = self._build_model()

    def _build_model(self):
        """
        Encoder-Decoder LSTM 아키텍처를 구축한다.

        Returns:
            model (tf.keras.Model): 컴파일된 Keras 모델
        """
        logging.info("LSTM Encoder-Decoder 모델 빌드 시작")

        # 인코더 (Encoder)
        # return_state=True를 통해 은닉 상태(h)와 셀 상태(c)를 반환받음
        encoder_inputs = Input(shape=(self.n_past, self.n_features))
        encoder_lstm = LSTM(128, activation='tanh', return_state=True, dropout=0.2)
        encoder_outputs, state_h, state_c = encoder_lstm(encoder_inputs)

        # 인코더의 상태를 디코더의 초기 상태로 전달 (Context Vector)
        encoder_states = [state_h, state_c]

        # 디코더 (Decoder)
        # RepeatVector: 인코더의 출력을 미래 타임스텝 수만큼 반복하여 디코더 입력으로 사용
        decoder_inputs = RepeatVector(self.n_future)(encoder_outputs)

        # 디코더 LSTM
        # return_sequences=True: 각 타임스텝마다 출력을 반환해야 함
        decoder_lstm = LSTM(128, activation='tanh', return_sequences=True, dropout=0.2)
        decoder_outputs = decoder_lstm(decoder_inputs, initial_state=encoder_states)

        # 출력층 (TimeDistributed)
        # 각 타임스텝의 출력에 대해 개별적으로 Dense Layer를 적용
        decoder_dense = TimeDistributed(Dense(1))  # 1은 단변량 타겟(종가)을 의미
        decoder_outputs = decoder_dense(decoder_outputs)

        model = Model(encoder_inputs, decoder_outputs)

        # 손실 함수로는 MSE(Mean Squared Error)를 사용, 옵티마이저는 Adam 채택
        model.compile(optimizer='adam', loss='mse', metrics=['mae'])

        model.summary(print_fn=logging.info)
        return model

    def train(self, X_train, y_train, epochs=50, batch_size=32, validation_split=0.1):
        """
        모델을 학습시킨다. Early Stopping을 적용하여 과적합을 방지한다.
        """
        early_stopping = EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)

        logging.info(f"모델 학습 시작 (Epochs: {epochs}, Batch Size: {batch_size})")
        history = self.model.fit(
            X_train, y_train,
            epochs=epochs,
            batch_size=batch_size,
            validation_split=validation_split,
            callbacks=[early_stopping],
            verbose=1
        )
        return history

    def predict(self, X_input):
        """
        미래 경로를 예측한다.
        """
        return self.model.predict(X_input)