import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import logging


class Visualizer:
    """
    예측 결과와 학습 과정을 시각화하는 클래스.
    """

    @staticmethod
    def plot_fan_chart(historical_dates, historical_values, forecast_dates, forecast_matrix,
                       title="Forecast Fan Chart"):
        """
        Fan Chart를 생성하여 저장한다.

        Args:
            historical_dates (list/array): 과거 데이터 날짜
            historical_values (list/array): 과거 실제 값
            forecast_dates (list/array): 예측 구간 날짜
            forecast_matrix (np.array): (simulations, n_future) 형태의 예측 분포 데이터
            title (str): 차트 제목
        """
        logging.info(f"Fan Chart 생성: {title}")

        # 예측값의 백분위수 계산 (5%, 20%, 50%, 80%, 95%)
        # 이는 예측 분포의 신뢰 구간을 형성함
        percentiles = [5, 20, 50, 80, 95]
        try:
            forecast_percentiles = np.percentile(forecast_matrix, percentiles, axis=0)
        except Exception as e:
            logging.error(f"백분위수 계산 실패: {e}")
            return

        p05, p20, p50, p80, p95 = forecast_percentiles

        plt.figure(figsize=(14, 7))

        # 스타일 설정
        plt.style.use('seaborn-v0_8-darkgrid')

        # 과거 데이터 플롯 (검정색 실선)
        plt.plot(historical_dates, historical_values, color='black', label='Historical Data', linewidth=1.5)

        # 예측 중앙값 (빨간색 실선) - 가장 가능성이 높은 경로
        plt.plot(forecast_dates, p50, color='firebrick', label='Median Forecast', linewidth=2)

        # Fan 영역 채우기 (불확실성 표현)
        # 20% ~ 80% 구간 (진한 영역, 60% 신뢰구간)
        plt.fill_between(forecast_dates, p20, p80, color='firebrick', alpha=0.4, label='60% Confidence Interval')

        # 5% ~ 95% 구간 (연한 영역, 90% 신뢰구간)
        plt.fill_between(forecast_dates, p05, p95, color='salmon', alpha=0.2, label='90% Confidence Interval')

        plt.title(title, fontsize=16, fontweight='bold')
        plt.xlabel('Date', fontsize=12)
        plt.ylabel('Price / Value', fontsize=12)
        plt.legend(loc='upper left')
        plt.grid(True, alpha=0.3)

        # 파일명 생성 및 저장
        filename = f"{title.replace(' ', '_')}_fan_chart.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()
        logging.info(f"차트 저장 완료: {filename}")

    @staticmethod
    def plot_training_history(history):
        """
        모델 학습 과정의 Loss 변화를 시각화한다.
        """
        plt.figure(figsize=(10, 5))
        plt.plot(history.history['loss'], label='Train Loss (MSE)')
        if 'val_loss' in history.history:
            plt.plot(history.history['val_loss'], label='Validation Loss (MSE)')

        plt.title('Model Training History', fontsize=14)
        plt.xlabel('Epoch')
        plt.ylabel('Loss')
        plt.legend()
        plt.grid(True)
        plt.savefig("training_history.png", dpi=300)
        plt.close()