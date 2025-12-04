from pydantic import BaseModel
from typing import List, Optional, Dict

class StockScore(BaseModel):
    ticker: str
    company_name: str
    current_price: float
    fusion_score: float
    d1_macro: float
    d2_fundamental: float
    d3_quant: float
    d4_timing: float
    sector: str
    macro_regime: str

class ForecastData(BaseModel):
    dates: List[str]
    historical: List[float]
    forecast: List[float]
    lower_bound: List[float]
    upper_bound: List[float]

class AnalysisResult(BaseModel):
    status: str
    progress: int
    top_stocks: List[StockScore] = []