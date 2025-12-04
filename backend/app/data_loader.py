import yfinance as yf
import pandas_datareader.data as web
import pandas as pd
import datetime
from pandas_datareader.fred import FredReader


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
            fred_api_key = os.getenv("FRED_API_KEY")
            if not fred_api_key:
                print("[Macro] WARN: FRED_API_KEY not set; returning empty macro_df")
                return pd.DataFrame()

            # FRED API Key 설정
            FredReader.api_key = fred_api_key

            # 주요 지표들
            indicators = {
                "M2SL": "M2",               # 통화량
                "T10Y2Y": "YieldSpread",    # 10Y-2Y 금리차
                "WALCL": "FedAssets",       # 연준 대차대조표
                "WTREGEN": "TGA",           # 재무부 일반계정
                "RRPONTSYD": "RRP",         # 역레포 잔액
                "UNRATE": "Unemployment",   # 실업률
                "BAMLH0A0HYM2": "HYSpread", # 하이일드 스프레드
            }

            end = datetime.datetime.now()
            start = end - datetime.timedelta(days=365)

            df = web.DataReader(list(indicators.keys()), "fred", start, end)
            df.rename(columns=indicators, inplace=True)

            # Net Liquidity = FedAssets - TGA - RRP
            df["NetLiquidity"] = (
                df["FedAssets"].ffill()
                - df["TGA"].ffill()
                - df["RRP"].ffill()
            )

            print(f"[Macro] Loaded macro_df with columns={list(df.columns)}", flush=True)
            return df

        except Exception as e:
            print(f"[Macro data error] {e}")
            return pd.DataFrame()

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