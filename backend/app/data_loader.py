import yfinance as yf
import pandas_datareader.data as web
import pandas as pd
import datetime
import requests
from concurrent.futures import ThreadPoolExecutor


class DataLoader:
    def __init__(self):
        self.start_date = (datetime.datetime.now() - datetime.timedelta(days=365 * 2)).strftime('%Y-%m-%d')

    def get_sp500_tickers(self):
        """Wikipedia에서 S&P 500 티커 목록 스크래핑"""
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'

        # 수정: 403 Forbidden 방지를 위해 User-Agent 헤더 추가
        tables = pd.read_html(
            url,
            storage_options={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        )

        # 수정: 반환된 리스트의 첫 번째 테이블 선택 및 'Symbol' 컬럼 추출
        df = tables[0]
        tickers = df['Symbol'].tolist()
        return [t.replace('.', '-') for t in tickers]

    def get_macro_data(self):
        """FRED에서 거시경제 지표 수집 (D1)"""
        try:
            # M2, 10년-2년 금리차, 하이일드 스프레드 등
            indicators = {
                'M2SL': 'M2',
                'T10Y2Y': 'YieldCurve',
                'WALCL': 'FedAssets',  # 연준 총자산 (유동성 대리지표)
                'WTREGEN': 'TGA',  # 재무부 계정
                'RRPONTSYD': 'RRP'  # 역레포
            }
            end = datetime.datetime.now()
            start = end - datetime.timedelta(days=365)

            df = web.DataReader(list(indicators.keys()), 'fred', start, end)
            df.rename(columns=indicators, inplace=True)

            # Net Liquidity = FedAssets - TGA - RRP
            df['NetLiquidity'] = df['FedAssets'].ffill() - \
                                 df['TGA'].ffill() - \
                                 df['RRP'].ffill()
            return df
        except Exception as e:
            print(f"Macro data error: {e}")

    def get_batch_stock_data(self, tickers):
        """yfinance로 대량의 주가 데이터 다운로드"""
        data = yf.download(tickers, start=self.start_date, group_by='column', progress=False, threads=True,
                           auto_adjust=False)
        return data

    def get_fundamentals(self, ticker):
        """개별 종목 펀더멘털 (D2) - API 호출 제한 고려하여 필요시 호출"""
        try:
            stock = yf.Ticker(ticker)
            return stock.info
        except:
            return {}