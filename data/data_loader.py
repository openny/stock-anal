import yfinance as yf
import pandas_datareader.data as web
import pandas as pd
import datetime
import logging
import requests

# 로깅 설정: 디버깅과 운영 모니터링을 위해 로그 레벨과 포맷을 지정한다.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class DataLoader:
    """
    금융 데이터 수집을 담당하는 클래스.
    FRED(연준) 데이터와 Yahoo Finance 주식 데이터를 통합 관리한다.
    """

    def __init__(self, start_date: str, end_date: str = None):
        """
        초기화 메서드.

        Args:
            start_date (str): 데이터 수집 시작일 (YYYY-MM-DD)
            end_date (str, optional): 데이터 수집 종료일. 기본값은 오늘 날짜.
        """
        self.start_date = start_date
        self.end_date = end_date if end_date else datetime.datetime.now().strftime('%Y-%m-%d')

    def get_fred_data(self, series_ids: list) -> pd.DataFrame:
        """
        FRED에서 거시경제 지표를 다운로드한다.

        Args:
            series_ids (list): FRED 시리즈 ID 리스트 (예:)

        Returns:
            pd.DataFrame: 병합된 거시경제 데이터
        """
        logging.info(f"FRED 데이터 다운로드 시작: {series_ids}")
        try:
            # pandas_datareader를 통해 FRED 데이터 호출
            df = web.DataReader(series_ids, 'fred', self.start_date, self.end_date)

            # 결측치 처리: 거시경제 데이터는 발표 주기가 다르므로 (일간, 주간, 월간)
            # Forward Fill (직전 값으로 채우기)을 통해 일간 데이터로 맞춤.
            df = df.ffill().dropna()

            logging.info("FRED 데이터 다운로드 및 전처리 완료")
            return df
        except Exception as e:
            logging.error(f"FRED 데이터 다운로드 중 치명적 오류 발생: {e}")
            raise

    def get_stock_data(self, ticker: str) -> pd.DataFrame:
        """
        Yahoo Finance에서 특정 종목의 OHLCV 데이터를 다운로드한다.

        Args:
            ticker (str): 종목 티커 (예: 'AAPL', 'NVDA')

        Returns:
            pd.DataFrame: 주가 데이터 (Open, High, Low, Close, Volume)
        """
        logging.info(f"{ticker} 주가 데이터 다운로드 시작")
        try:
            # auto_adjust=True: 배당 및 분할이 조정된 수정 주가 사용
            data = yf.download(ticker, start=self.start_date, end=self.end_date, auto_adjust=True, progress=False)

            if data.empty:
                raise ValueError(f"데이터가 비어 있습니다: {ticker}. 티커를 확인하거나 날짜 범위를 변경하세요.")

            # MultiIndex 컬럼 처리 (yfinance 최신 버전의 경우 컬럼이 MultiIndex일 수 있음)
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)

            logging.info(f"{ticker} 주가 데이터 다운로드 완료 (행 수: {len(data)})")
            return data
        except Exception as e:
            logging.error(f"{ticker} 데이터 다운로드 실패: {e}")
            raise

    def get_ticker_fundamentals(self, ticker: str) -> dict:
        """
        종목의 펀더멘털 정보(재무 비율, 대차대조표 항목 등)를 가져온다.

        Args:
            ticker (str): 종목 티커

        Returns:
            dict: 주요 펀더멘털 지표가 담긴 딕셔너리
        """
        logging.info(f"{ticker} 펀더멘털 정보 조회")
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            # 핵심 펀더멘털 지표 추출
            # .get() 메서드를 사용하여 키가 없을 경우 None을 반환하도록 처리
            fundamentals = {
                'symbol': ticker,
                'market_cap': info.get('marketCap'),
                'forward_pe': info.get('forwardPE'),
                'trailing_pe': info.get('trailingPE'),
                'price_to_book': info.get('priceToBook'),
                'operating_margins': info.get('operatingMargins'),
                'ebitda_margins': info.get('ebitdaMargins'),
                'return_on_equity': info.get('returnOnEquity'),
                'debt_to_equity': info.get('debtToEquity'),
                'total_cash': info.get('totalCash'),
                'total_debt': info.get('totalDebt'),
                'free_cash_flow': info.get('freeCashflow'),
                'operating_cash_flow': info.get('operatingCashflow')
            }
            logging.info(f"{ticker} 펀더멘털 데이터 추출 완료")
            return fundamentals
        except Exception as e:
            logging.warning(f"펀더멘털 정보 조회 실패 (일부 데이터 누락 가능성): {e}")
            return {}

    def get_sp500_tickers(self) -> list:
        """
        Wikipedia에서 S&P 500 종목 리스트를 스크래핑한다.
        이는 시장 전체 분석이나 유니버스 구성 시 사용된다.
        """
        logging.info("S&P 500 티커 스크래핑 시작")
        try:
            url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
            tables = pd.read_html(url)
            df = tables
            tickers = df.tolist()

            # Yahoo Finance는 '.' 대신 '-'를 사용하는 경우가 있음 (예: BRK.B -> BRK-B)
            tickers = [t.replace('.', '-') for t in tickers]

            logging.info(f"S&P 500 티커 {len(tickers)}개 로드 완료")
            return tickers
        except Exception as e:
            logging.error(f"S&P 500 티커 스크래핑 실패: {e}")
            return