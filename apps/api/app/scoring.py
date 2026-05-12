from dataclasses import dataclass
from typing import Dict, List, Tuple, Literal
import numpy as np
import pandas as pd

from .alpaca_client import Snapshot

RiskProfile = Literal["low","medium","high"]
InvestHorizon = Literal["daytrade","weekly","monthly","3m","1y","5y"]
Strategy = Literal["quality_value","momentum","low_vol","dividend","mean_reversion"]

def clamp01(x: float) -> float:
    return float(max(0.0, min(1.0, x)))

def log_norm(x: float, min_v: float, max_v: float) -> float:
    x = max(1.0, x)
    lx = np.log10(x)
    lmin = np.log10(max(1.0, min_v))
    lmax = np.log10(max(1.0, max_v))
    return clamp01((lx - lmin) / (lmax - lmin))

def risk_penalty(vol30: float, drawdown1y: float, risk: RiskProfile) -> float:
    base = 0.55 * clamp01(vol30 / 0.6) + 0.45 * clamp01(drawdown1y / 0.6)
    if risk == "low":
        return 0.9 * base
    if risk == "medium":
        return 0.6 * base
    return 0.35 * base

def horizon_weights(h: InvestHorizon) -> Tuple[float, float]:
    if h == "daytrade":
        return (0.35, 0.05)
    if h == "weekly":
        return (0.30, 0.10)
    if h == "monthly":
        return (0.25, 0.10)
    if h == "3m":
        return (0.20, 0.15)
    if h == "1y":
        return (0.12, 0.22)
    return (0.06, 0.18)

def strategy_weights(s: Strategy) -> Dict[str, float]:
    if s == "quality_value":
        return {"momentum": 0.25, "lowvol": 0.20, "liquidity": 0.20}
    if s == "momentum":
        return {"momentum": 0.55, "lowvol": 0.10, "liquidity": 0.20}
    if s == "low_vol":
        return {"momentum": 0.15, "lowvol": 0.50, "liquidity": 0.15}
    if s == "dividend":
        return {"momentum": 0.15, "lowvol": 0.20, "liquidity": 0.15}
    return {"momentum": 0.20, "lowvol": 0.25, "liquidity": 0.20}

@dataclass
class Scored:
    ticker: str
    score: float
    flags: List[str]
    rationale: str

def score_snapshot(
    snap: Snapshot,
    horizon: InvestHorizon,
    risk: RiskProfile,
    strategy: Strategy,
    planned_volume_usd: float
) -> Scored:
    hw_m3, hw_m1y = horizon_weights(horizon)
    sw = strategy_weights(strategy)

    liquidity_n = log_norm(snap.adv_usd, 200_000_000, 15_000_000_000)

    m3_n = clamp01((snap.momentum3m + 0.20) / 0.50)
    m1y_n = clamp01((snap.momentum1y + 0.35) / 1.10)
    momentum_n = clamp01(hw_m3 * m3_n + hw_m1y * m1y_n + (1 - hw_m3 - hw_m1y) * 0.5)

    lowvol_n = 1.0 - clamp01(snap.vol30 / 0.6)

    risk_p = risk_penalty(snap.vol30, snap.drawdown1y, risk)

    liq_need = planned_volume_usd * 100.0 if planned_volume_usd > 0 else 0.0
    liquidity_fit = 1.0 if liq_need <= 0 else clamp01(snap.adv_usd / liq_need)

    raw = sw["momentum"] * momentum_n + sw["lowvol"] * lowvol_n + sw["liquidity"] * liquidity_n
    score = clamp01(raw * liquidity_fit - 0.35 * risk_p)

    flags: List[str] = []
    if liquidity_fit < 0.6:
        flags.append("Liquidity risk for planned size")
    if snap.vol30 > 0.35 and risk == "low":
        flags.append("High volatility vs low-risk")
    if snap.drawdown1y > 0.35 and risk != "high":
        flags.append("Large 1Y drawdown")
    if horizon == "daytrade" and snap.adv_usd < 800_000_000:
        flags.append("Thin liquidity for intraday")

    rationale = f"Momentum 3M {snap.momentum3m*100:.1f}%, 1Y {snap.momentum1y*100:.1f}% • Vol {snap.vol30*100:.0f}% • 1Y DD {snap.drawdown1y*100:.0f}% • ADV$ ~{snap.adv_usd/1e6:.0f}M"
    return Scored(ticker=snap.ticker, score=score, flags=flags, rationale=rationale)

def diversify_by_correlation(
    ranked: List[tuple[Snapshot, Scored]],
    returns_by_ticker: Dict[str, pd.Series],
    n: int
) -> List[tuple[Snapshot, Scored]]:
    if not ranked:
        return []
    picked: List[tuple[Snapshot, Scored]] = [ranked[0]]
    remaining = ranked[1:]

    def corr(a: str, b: str) -> float:
        ra = returns_by_ticker.get(a)
        rb = returns_by_ticker.get(b)
        if ra is None or rb is None:
            return 0.5
        df = pd.concat([ra, rb], axis=1).dropna()
        if df.shape[0] < 30:
            return 0.5
        return float(df.corr().iloc[0, 1])

    while len(picked) < n and remaining:
        best_idx = 0
        best_obj = 1e9
        scan = remaining[: max(60, n * 10)]
        for i, (s, sc) in enumerate(scan):
            cs = [corr(s.ticker, ps.ticker) for ps, _ in picked]
            avg_corr = float(np.mean(cs)) if cs else 0.0
            max_corr = float(np.max(cs)) if cs else 0.0
            obj = 1.4 * avg_corr + 0.6 * max_corr - 1.2 * sc.score
            if obj < best_obj:
                best_obj = obj
                best_idx = i
        picked.append(remaining.pop(best_idx))
    return picked
