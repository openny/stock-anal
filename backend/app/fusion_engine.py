import pandas as pd
import pandas_ta as ta
import numpy as np


class FusionEngine:
    def __init__(self, macro_df):
        self.macro_df = macro_df
        self.macro_score = self._calculate_d1_macro()

    def _calculate_d1_macro(self):
        """D1: Macro Score 계산 (0-100)"""
        if self.macro_df.empty: return 50

        # 최근 유동성 추세 확인
        recent_liq = self.macro_df['NetLiquidity'].iloc[-30:]
        slope = (recent_liq.iloc[-1] - recent_liq.iloc[0]) / recent_liq.iloc[0]

        score = 50
        if slope > 0:
            score += 20  # 유동성 증가
        else:
            score -= 20  # 유동성 감소

        # 금리차 역전 여부
        # [수정] 전체 행(.iloc[-1])이 아닌 특정 '금리차' 컬럼의 값을 가져와야 합니다.
        # 확인 필요: 실제 데이터에 존재하는 금리차 컬럼명(예: 'YieldSpread', '10Y-2Y')으로 변경해주세요.
        target_col = 'YieldSpread'  # 여기에 실제 컬럼명을 입력하세요

        if target_col in self.macro_df.columns:
            spread = self.macro_df[target_col].iloc[-1]
        else:
            # 컬럼을 찾지 못할 경우 에러 방지를 위해 첫 번째 컬럼 사용 혹은 0 처리
            spread = self.macro_df.iloc[-1].iloc[0]

        if spread < 0:
            score -= 20  # 경기 침체 신호
        else:
            score += 10

        return np.clip(score, 0, 100)

    def calculate_scores(self, ticker, df, info):
        """개별 종목 4D 점수 계산"""
        if len(df) < 200: return None

        # --- D2: Fundamental (35%) ---
        # 실제로는 info에서 매출 성장률 등을 가져와야 함. 데이터가 없으면 중간값
        growth_score = 50
        if info.get('revenueGrowth'): growth_score += info['revenueGrowth'] * 100
        d2 = np.clip(growth_score, 0, 100)

        # --- D3: Quant (25%) ---
        # 모멘텀 및 가치
        rsi = df.ta.rsi(length=14).iloc[-1]
        pe_ratio = info.get('trailingPE', 20)

        d3 = 50
        if rsi > 50: d3 += 10
        if pe_ratio < 25: d3 += 10
        d3 = np.clip(d3, 0, 100)

        # --- D4: Timing (15%) ---
        # 기술적 지표
        sma_20 = df['Close'].rolling(20).mean().iloc[-1]
        sma_50 = df['Close'].rolling(50).mean().iloc[-1]
        current_price = df['Close'].iloc[-1]

        d4 = 40
        if current_price > sma_20: d4 += 20
        if sma_20 > sma_50: d4 += 20
        d4 = np.clip(d4, 0, 100)

        # 최종 Fusion Score
        # 가중치: Macro(0.25) + Fund(0.35) + Quant(0.25) + Timing(0.15)
        final_score = (self.macro_score * 0.25) + \
                      (d2 * 0.35) + \
                      (d3 * 0.25) + \
                      (d4 * 0.15)

        return {
            "ticker": ticker,
            "company_name": info.get('shortName', ticker),
            "current_price": current_price,
            "fusion_score": round(final_score, 1),
            "d1_macro": round(self.macro_score, 1),
            "d2_fundamental": round(d2, 1),
            "d3_quant": round(d3, 1),
            "d4_timing": round(d4, 1),
            "sector": info.get('sector', 'Unknown')
        }