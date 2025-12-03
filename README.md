통합 금융 시계열 예측 시스템 (Financial Time Series Forecasting System)
개요
본 시스템은 거시경제 지표(연준 자산, 금리 등)와 개별 주식 데이터를 통합하여, 딥러닝(LSTM Encoder-Decoder) 모델을 기반으로 주가의 미래 경로를 예측하고 불확실성을 Fan Chart로 시각화하는 도구입니다.

주요 기능
자동화된 데이터 수집: FRED API와 yfinance를 연동하여 최신 데이터를 자동으로 가져옵니다.

순유동성(Net Liquidity) 분석: 연준 대차대조표 항목을 기반으로 시장 유동성을 계산하여 예측 변수로 활용합니다.

다중 시점 예측 (Multi-step Forecasting): 미래 30일(설정 가능)의 주가 흐름을 한 번에 예측합니다.

불확실성 시각화: 예측 결과의 확률 분포를 Fan Chart 형태로 제공하여 리스크 관리를 돕습니다.

설치 방법
터미널에서 다음 명령어를 실행하십시오:bash chmod +x setup.sh run.sh ./setup.sh


## 사용 방법
기본 설정(AAPL)으로 실행:
```bash
./run.sh
특정 티커(예: NVDA)로 실행:

Bash
./run.sh NVDA
테스트 실행 (TDD)
코드 변경 후 안정성을 검증하기 위해 테스트를 수행하십시오:

Bash
source venv/bin/activate
pytest tests/
디렉토리 구조
data/: 데이터 로더 및 전처리 로직

models/: Keras LSTM 모델 정의

visualization/: 차트 시각화 모듈

main.py: 프로그램 실행 진입점

라이선스
MIT License