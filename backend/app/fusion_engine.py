import pandas as pd
import pandas_ta as ta
import numpy as np


class FusionEngine:
    def __init__(self, macro_df):
        self.macro_df = macro_df
        self.macro_regime = "중립 (Neutral)"  # 기본값
        self.macro_score = self._calculate_d1_macro()

    def _classify_macro_regime(self, score: float) -> str:
        """
        매크로 레짐 텍스트 라벨링
        - < 40  : 위험 모드 (Risk-Off)
        - 40~60 : 중립 (Neutral)
        - > 60  : 리스크온 (Risk-On)
        """
        if score < 40:
            return "위험 모드 (Risk-Off)"
        elif score < 60:
            return "중립 (Neutral)"
        else:
            return "리스크온 (Risk-On)"

    def _z_score(self, series: pd.Series):
        """표준화된 z-score (최근 1년 평균 대비 위치)"""
        series = series.dropna()
        if len(series) < 30:
            return 0.0

        mean = series.mean()
        std = series.std()
        latest = series.iloc[-1]

        if std == 0 or np.isnan(std):
            return 0.0

        return float((latest - mean) / std)

    def _scale_to_score(self, z, direction="positive", max_impact=30):
        """
        z-score를 0~100 점수로 매핑
        - direction='positive'  : z가 클수록 좋은 지표 (예: NetLiquidity, YieldSpread)
        - direction='negative'  : z가 클수록 나쁜 지표 (예: Unemployment, HYSpread)
        - max_impact            : z=±2~3 근처에서 최대 ±max_impact 정도로 영향
        """
        # -3 ~ +3 사이로 클리핑
        z = np.clip(z, -3, 3)

        # positive 지표는 z가 +면 가산, negative 지표는 z가 +면 감점
        if direction == "positive":
            delta = z * (max_impact / 2.0)
        else:  # negative
            delta = -z * (max_impact / 2.0)

        base = 50.0
        return float(np.clip(base + delta, 0, 100))

    def _calculate_d1_macro(self) -> float:
        """
        D1: Macro Score (0~100)
        - 유동성(NetLiquidity)          : 35%
        - 금리커브(YieldSpread)        : 25%
        - 고용(UNRATE)                 : 20%
        - 크레딧 스프레드(HY Spread)   : 20%
        """

        if self.macro_df is None or self.macro_df.empty:
            self.macro_regime = "중립 (Neutral)"
            return 50.0

        df = self.macro_df

        # 유동성 (Net Liquidity)
        liq_score = 50.0
        if "NetLiquidity" in df.columns:
            z_liq = self._z_score(df["NetLiquidity"])
            liq_score = self._scale_to_score(z_liq, direction="positive", max_impact=40)
        else:
            print("[Macro] NetLiquidity column missing; using neutral score 50", flush=True)

        # 금리 커브 (10Y-2Y 스프레드)
        curve_score = 50.0
        # YieldSpread 컬럼 또는 이전 이름들 대응
        curve_col = None
        for c in ["YieldSpread", "YieldCurve", "T10Y2Y"]:
            if c in df.columns:
                curve_col = c
                break

        if curve_col:
            z_curve = self._z_score(df[curve_col])
            curve_score = self._scale_to_score(z_curve, direction="positive", max_impact=30)
        else:
            print("[Macro] YieldSpread column missing; using neutral score 50", flush=True)

        # 고용 (실업률 UNRATE)
        emp_score = 50.0
        if "Unemployment" in df.columns:
            z_unemp = self._z_score(df["Unemployment"])
            # 실업률은 높을수록 나쁨 → direction='negative'
            emp_score = self._scale_to_score(z_unemp, direction="negative", max_impact=30)
        else:
            print("[Macro] Unemployment column missing; using neutral score 50", flush=True)

        # 크레딧 스프레드 (하이일드 스프레드)
        credit_score = 50.0
        if "HYSpread" in df.columns:
            z_hy = self._z_score(df["HYSpread"])
            # 스프레드는 높을수록 위험 ↑ → direction='negative'
            credit_score = self._scale_to_score(z_hy, direction="negative", max_impact=35)
        else:
            print("[Macro] HYSpread column missing; using neutral score 50", flush=True)

        # 각 요소의 가중치
        weights = {
            "liq": 0.35,
            "curve": 0.25,
            "emp": 0.20,
            "credit": 0.20,
        }

        # 실제 사용 가능한 항목만으로 가중치 재정규화
        components = {
            "liq": liq_score,
            "curve": curve_score,
            "emp": emp_score,
            "credit": credit_score,
        }
        available = {k: v for k, v in components.items() if v is not None}

        if not available:
            return 50.0

        weight_sum = sum(weights[k] for k in available.keys())
        normalized_weights = {k: weights[k] / weight_sum for k in available.keys()}

        macro_score = 0.0
        for k, score in available.items():
            macro_score += score * normalized_weights[k]

        macro_score = float(np.clip(macro_score, 0, 100))
        print(
            f"[Macro] liq={liq_score:.1f}, curve={curve_score:.1f}, "
            f"emp={emp_score:.1f}, credit={credit_score:.1f} -> macro={macro_score:.1f}",
            flush=True,
        )
        self.macro_regime = self._classify_macro_regime(macro_score)
        return macro_score

    def _safe_get(self, d: dict, key: str, default=None):
        """dict에서 key 안전하게 가져오기"""
        v = d.get(key, default)
        return default if v is None or (isinstance(v, float) and np.isnan(v)) else v

    def _scale_01(self, x, lo, hi):
        """lo~hi 구간을 0~1로 스케일 (클리핑 포함)"""
        if x is None or np.isnan(x):
            return 0.5
        return float(np.clip((x - lo) / (hi - lo), 0, 1))

    def calculate_scores(self, ticker, df: pd.DataFrame, info: dict):
        """개별 종목 4D 점수 계산 (Macro + Fundamental + Quant + Timing)"""
        # 데이터 최소 길이 체크
        if df is None or len(df) < 200:
            print(f"[Fusion] {ticker}: insufficient price data (len={len(df) if df is not None else 0})", flush=True)
            return None

        df = df.copy()
        df = df.sort_index()
        df = df.dropna(subset=["Close"])

        # ------------------------
        # D2: Fundamental (35%)
        # ------------------------
        # revenueGrowth: -20% ~ +40% 사이에 주로 분포한다고 가정
        rev_growth = self._safe_get(info, "revenueGrowth", 0.0)  # 예: 0.12 = 12%
        rev_score = self._scale_01(rev_growth, -0.2, 0.4) * 100  # -20% → 0점, +40% → 100점 근처

        # PER: 5~40 구간을 "무난"한 영역으로 보고, 15~25 근처를 가장 높게 평가하는 식의 보정
        pe = self._safe_get(info, "trailingPE", 20.0)

        if pe is None or pe <= 0 or np.isnan(pe):
            pe_score = 50.0
        else:
            # 너무 싼(PE<5), 너무 비싼(PE>60) 구간은 감점
            if pe < 5:
                pe_score = 60
            elif pe > 60:
                pe_score = 30
            else:
                # 15~25 근처를 가장 선호 (벨 커브 느낌)
                center = 20
                spread = 10  # ±10
                dist = abs(pe - center)
                # dist=0 → 100점, dist=spread → 60점, 더 나가면 점점 떨어짐
                pe_score = max(30, 100 - (dist / spread) * 40)

        # 두 요소를 합쳐 Fundamental 점수
        d2 = 0.6 * rev_score + 0.4 * pe_score
        d2 = float(np.clip(d2, 0, 100))

        # ------------------------
        # D3: Quant (25%)
        # ------------------------
        # 1) 중기 모멘텀 (60일 수익률)
        close = df["Close"]
        if len(close) < 60:
            print(f"[Fusion] {ticker}: insufficient history for quant (len={len(close)})", flush=True)
            return None

        ret_60 = (close.iloc[-1] / close.iloc[-60]) - 1.0  # 최근 60거래일 수익률
        # -30% ~ +50% 구간 스케일링
        mom_score = self._scale_01(ret_60, -0.3, 0.5) * 100

        # 2) 변동성 (최근 60일). 낮을수록 점수↑
        daily_ret = close.pct_change().dropna()
        vol_60 = daily_ret.iloc[-60:].std() if len(daily_ret) >= 60 else daily_ret.std()
        # vol 10% ~ 60% 기준으로 스케일 (높을수록 위험)
        vol_norm = self._scale_01(vol_60, 0.1, 0.6)  # 0~1 (높을수록 리스크↑)
        vol_score = (1.0 - vol_norm) * 100

        # 3) RSI(14) (과매수/과매도 상태)
        try:
            rsi_series = df.ta.rsi(length=14)
            rsi = float(rsi_series.iloc[-1])
        except Exception:
            rsi = 50.0

        # RSI 30~70 구간을 건강한 범위로 보고, 50 근처가 가장 안정적 → 점수 높게
        if np.isnan(rsi):
            rsi_score = 50.0
        else:
            dist_rsi = abs(rsi - 50)
            # 50에서 멀어질수록 점수 감소 (단, 과매도 구간은 약간 가점 줄 수도 있음 튜닝 가능)
            rsi_score = max(30, 100 - (dist_rsi / 50) * 50)

        # Quant 최종
        d3 = 0.5 * mom_score + 0.3 * vol_score + 0.2 * rsi_score
        d3 = float(np.clip(d3, 0, 100))

        # ------------------------
        # D4: Timing (15%)
        # ------------------------
        # 단기/중기 이동평균, 골든/데드크로스, 현재 위치를 종합해서 점수화
        sma_20 = close.rolling(20).mean()
        sma_50 = close.rolling(50).mean()
        if sma_20.isna().all() or sma_50.isna().all():
            d4 = 50.0
            current_price = float(close.iloc[-1])
        else:
            sma20_last = float(sma_20.iloc[-1])
            sma50_last = float(sma_50.iloc[-1])
            current_price = float(close.iloc[-1])

            # 가격이 20MA/50MA 대비 어느 위치에 있는지 (과하게 위에 있으면 과열, 너무 밑에 있으면 약세)
            # price / sma20, price / sma50 기준 0.8~1.2 구간을 건강한 범위로 본다
            ratio20 = current_price / sma20_last if sma20_last > 0 else 1.0
            ratio50 = current_price / sma50_last if sma50_last > 0 else 1.0

            def timing_score_from_ratio(r):
                # r=1일 때 100점, r이 0.8 또는 1.2일 때 70점, 더 멀어지면 최소 30점
                dist = abs(r - 1.0)
                base = 100 - dist * 150  # 대략 dist=0.2 → 70점
                return float(np.clip(base, 30, 100))

            score20 = timing_score_from_ratio(ratio20)
            score50 = timing_score_from_ratio(ratio50)

            # 골든크로스 가점
            cross_bonus = 0.0
            if sma_20.iloc[-1] > sma_50.iloc[-1]:
                cross_bonus += 5.0

            d4 = 0.5 * score20 + 0.5 * score50 + cross_bonus
            d4 = float(np.clip(d4, 0, 100))

        # ------------------------
        # Fusion Score (최종)
        # ------------------------
        # 가중치: Macro(0.25) + Fund(0.35) + Quant(0.25) + Timing(0.15)
        final_score = (
            self.macro_score * 0.25
            + d2 * 0.35
            + d3 * 0.25
            + d4 * 0.15
        )

        final_score = float(np.round(final_score, 1))

        print(
            f"[Fusion] {ticker}: macro={self.macro_score:.1f}, "
            f"D2={d2:.1f}, D3={d3:.1f}, D4={d4:.1f} -> fusion={final_score:.1f}",
            flush=True,
        )

        return {
            "ticker": ticker,
            "company_name": self._safe_get(info, "shortName", ticker),
            "current_price": current_price,
            "fusion_score": final_score,
            "d1_macro": float(np.round(self.macro_score, 1)),
            "d2_fundamental": float(np.round(d2, 1)),
            "d3_quant": float(np.round(d3, 1)),
            "d4_timing": float(np.round(d4, 1)),
            "sector": self._safe_get(info, "sector", "Unknown"),
            "macro_regime": getattr(self, "macro_regime", "중립 (Neutral)"),
        }