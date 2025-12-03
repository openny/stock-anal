#!/bin/bash

# 가상환경 활성화
source venv/bin/activate

# 실행 옵션 설정 (기본값)
TICKER="AAPL"
START_DATE="2019-01-01"
EPOCHS=30

# 사용자 입력 확인 ($1: Ticker)
if [! -z "$1" ]; then
    TICKER=$1
fi

echo "=== Financial Forecasting System 실행 ==="
echo "Target Ticker: $TICKER"
echo "Start Date: $START_DATE"
echo "Epochs: $EPOCHS"

# 메인 파이썬 스크립트 실행
python main.py --ticker "$TICKER" --start_date "$START_DATE" --epochs $EPOCHS

if [ $? -eq 0 ]; then
    echo "실행 성공. 결과 차트를 확인하세요."
else
    echo "실행 중 오류가 발생했습니다."
fi