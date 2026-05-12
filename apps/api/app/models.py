from pydantic import BaseModel, Field
from typing import List, Literal, Optional, Dict, Any

InvestHorizon = Literal["daytrade","weekly","monthly","3m","1y","5y"]
RiskProfile = Literal["low","medium","high"]
Strategy = Literal["quality_value","momentum","low_vol","dividend","mean_reversion"]
Universe = Literal["mega_caps","nasdaq100_like","sp500_like"]
Diversification = Literal["balanced","concentrated"]

class MarketSnapshotRequest(BaseModel):
    tickers: List[str] = Field(..., min_length=1)
    lookbackDays: int = Field(260, ge=30, le=1000)

class CandidateOut(BaseModel):
    ticker: str
    name: Optional[str] = None
    sector: Optional[str] = None
    price: float
    advUsd: float
    vol30: float
    drawdown1y: float
    momentum3m: float
    momentum1y: float
    dividendYield: float = 0.0
    valueScore: float = 0.0
    qualityScore: float = 0.0
    score: float
    flags: List[str] = []
    rationale: str

class ScreenRequest(BaseModel):
    horizon: InvestHorizon = "1y"
    risk: RiskProfile = "medium"
    strategy: Strategy = "quality_value"
    universe: Universe = "mega_caps"
    plannedVolumeUsd: float = Field(5000, ge=0)
    portfolioSize: int = Field(8, ge=1, le=30)
    diversification: Diversification = "balanced"

class ScreenResponse(BaseModel):
    settings: Dict[str, Any]
    candidates: List[CandidateOut]
    notes: List[str] = []

class ExplainRequest(BaseModel):
    settings: Dict[str, Any]
    candidates: List[CandidateOut]

class ExplainResponse(BaseModel):
    summary: str
    bullets: List[str]

class PaperOrderRequest(BaseModel):
    symbol: str
    side: Literal["buy","sell"]
    qty: float = Field(..., gt=0)
    type: Literal["market","limit"] = "market"
    limit_price: Optional[float] = None
    time_in_force: Literal["day","gtc"] = "day"
