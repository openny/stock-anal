#!/bin/bash

# 색상 정의

GREEN='\033[0;32m'
NC='\033[0m' # No Color

# 1. 가상환경 생성 확인
if [ ! -d "venv" ]; then
    echo "가상환경(venv)을 생성합니다..."
    python3 -m venv venv
else
    echo "기존 가상환경을 감지했습니다."
fi

# 2. 가상환경 활성화
source venv/bin/activate

# 3. pip 업그레이드
echo "pip를 최신 버전으로 업그레이드합니다..."
pip install --upgrade pip

# 4. 의존성 패키지 설치
if [ -f "requirements.txt" ]; then
    echo "의존성 패키지를 설치합니다..."
    pip install -r requirements.txt
else
    echo "오류: requirements.txt 파일을 찾을 수 없습니다."
    exit 1
fi

# 5. 디렉토리 구조 생성 (필요한 경우)
mkdir -p data models visualization tests

echo -e "${GREEN}=== 설치 완료../run.sh 스크립트로 실행하세요. ===${NC}"