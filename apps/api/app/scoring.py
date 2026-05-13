from dataclasses import dataclass
from typing import Dict, List, Tuple, Literal
import numpy as np
import pandas as pd

from .alpaca_client import Snapshot

RiskProfile = Literal["low", "medium", "high"]
InvestHorizon = Literal["daytrade", "weekly", "monthly", "3m", "1y", "5y"]
Strategy = Literal["quality_value", "momentum", "low_vol", "dividend", "mean_reversion"]


def clamp01(x: float) -> float:
    return float(max(0.0, min(1.0, x)))


def log_norm(x: float, min_v: float, max_v: float) -> float:
    x = max(1.0, x)
    lx = np.log10(x)
    lmin = np.log10(max(1.0, min_v))
    lmax = np.log10(max(1.0, max_v))
    if lmax <= lmin:
        return 0.0
    return clamp01((lx - lmin) / (lmax - lmin))


def risk_penalty(vol30: float, drawdown1y: float, risk: RiskProfile) -> float:
    base = 0.55 * clamp01(vol30 / 0.6) + 0.45 * clamp01(drawdown1y / 0.6)
    if risk == "low":
        return 0.9 * base
    if risk == "medium":
        return 0.6 * base
    return 0.35 * base  # high risk: lighter penalty


def horizon_weights(h: InvestHorizon) -> Tuple[float, float]:
    """Return (weight_3m_momentum, weight_1y_momentum)."""
    if h == "daytrade":
        return (0.40, 0.02)
    if h == "weekly":
        return (0.32, 0.08)
    if h == "monthly":
        return (0.25, 0.10)
    if h == "3m":
        return (0.20, 0.15)
    if h == "1y":
        return (0.10, 0.28)
    return (0.05, 0.25)   # 5y: heavily 1Y momentum, lower short-term noise


def strategy_weights(s: Strategy) -> Dict[str, float]:
    """
    Return a weight dict for each scoring component.
    All weights must sum to 1.0 to keep scores comparable across strategies.
    Components: momentum, lowvol, liquidity, mean_rev
    """
    if s == "momentum":
        # Aggressive trend-following: momentum dominates
        return {"momentum": 0.60, "lowvol": 0.10, "liquidity": 0.20, "mean_rev": 0.10}
    if s == "low_vol":
        # Defensive: punish high-vol names hard, reward stability
        return {"momentum": 0.15, "lowvol": 0.55, "liquidity": 0.15, "mean_rev": 0.15}
    if s == "quality_value":
        # Balanced: momentum + stability, penalise excessive drawdown
        return {"momentum": 0.30, "lowvol": 0.25, "liquidity": 0.25, "mean_rev": 0.20}
    if s == "dividend":
        # Low-vol proxy (no fundamental yield data available via Alpaca)
        return {"momentum": 0.10, "lowvol": 0.45, "liquidity": 0.25, "mean_rev": 0.20}
    # mean_reversion: buy recent losers with good liquidity
    return {"momentum": 0.05, "lowvol": 0.20, "liquidity": 0.30, "mean_rev": 0.45}


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
    planned_volume_usd: float,
) -> Scored:
    hw_m3, hw_m1y = horizon_weights(horizon)
    sw = strategy_weights(strategy)

    # ── Liquidity score (log-normalised against the universe range) ─────────
    liquidity_n = log_norm(snap.adv_usd, 5_000_000, 15_000_000_000)

    # ── Momentum scores ──────────────────────────────────────────────────────
    # 3-month momentum: normalise so 0 % = 0.4, +50 % = 1.0, -20 % = 0
    m3_n = clamp01((snap.momentum3m + 0.20) / 0.70)
    # 1-year momentum: normalise so 0 % = 0.32, +100 % = 1.0, -35 % = 0
    m1y_n = clamp01((snap.momentum1y + 0.35) / 1.45)
    # Blend 3m & 1y based on horizon, the remainder goes to a neutral 0.5
    remainder = max(0.0, 1.0 - hw_m3 - hw_m1y)
    momentum_n = clamp01(hw_m3 * m3_n + hw_m1y * m1y_n + remainder * 0.5)

    # ── Low-volatility score ─────────────────────────────────────────────────
    lowvol_n = 1.0 - clamp01(snap.vol30 / 0.65)

    # ── Mean-reversion score ─────────────────────────────────────────────────
    # Reward stocks that have fallen hard from peak (deep drawdown = buying opportunity)
    mean_rev_n = clamp01(snap.drawdown1y / 0.50)

    # ── Liquidity fit for planned trade size ────────────────────────────────
    liq_need = planned_volume_usd * 50.0 if planned_volume_usd > 0 else 0.0
    liquidity_fit = 1.0 if liq_need <= 0 else clamp01(snap.adv_usd / liq_need)

    # ── Risk penalty ─────────────────────────────────────────────────────────
    risk_p = risk_penalty(snap.vol30, snap.drawdown1y, risk)

    # ── Composite raw score ──────────────────────────────────────────────────
    raw = (
        sw["momentum"] * momentum_n
        + sw["lowvol"] * lowvol_n
        + sw["liquidity"] * liquidity_n
        + sw["mean_rev"] * mean_rev_n
    )

    # Liquidity fit scales the score down when the position size is too large
    # relative to average daily volume. Risk penalty reduces score further.
    score = clamp01(raw * max(0.5, liquidity_fit) - 0.30 * risk_p)

    # ── Flags ─────────────────────────────────────────────────────────────────
    flags: List[str] = []
    if liquidity_fit < 0.5:
        flags.append("Low liquidity for planned trade size")
    if snap.vol30 > 0.40 and risk == "low":
        flags.append("High volatility vs low-risk profile")
    if snap.drawdown1y > 0.40 and risk == "low":
        flags.append("Large 1Y drawdown — consider risk profile")
    if horizon in ("daytrade", "weekly") and snap.adv_usd < 200_000_000:
        flags.append("Thin intraday liquidity")
    if strategy == "mean_reversion" and snap.momentum3m > 0.15:
        flags.append("3M momentum still positive — reversion signal weak")
    if strategy == "momentum" and snap.momentum3m < 0:
        flags.append("Negative 3M momentum — weak momentum signal")

    # ── Rationale string ──────────────────────────────────────────────────────
    rationale = (
        f"3M {snap.momentum3m*100:+.1f}% • "
        f"1Y {snap.momentum1y*100:+.1f}% • "
        f"Vol {snap.vol30*100:.0f}% • "
        f"1Y DD {snap.drawdown1y*100:.0f}% • "
        f"ADV ${snap.adv_usd/1e6:.0f}M"
    )
    return Scored(ticker=snap.ticker, score=score, flags=flags, rationale=rationale)


def diversify_by_correlation(
    ranked: List[tuple],
    returns_by_ticker: Dict[str, pd.Series],
    n: int,
) -> List[tuple]:
    """Greedy correlation-aware selection: prefer high-score AND low-correlation pairs."""
    if not ranked:
        return []
    picked: List[tuple] = [ranked[0]]
    remaining = list(ranked[1:])

    def corr(a: str, b: str) -> float:
        ra = returns_by_ticker.get(a)
        rb = returns_by_ticker.get(b)
        if ra is None or rb is None:
            return 0.5
        df = pd.concat([ra, rb], axis=1).dropna()
        if df.shape[0] < 20:
            return 0.5
        return float(df.corr().iloc[0, 1])

    while len(picked) < n and remaining:
        best_idx = 0
        best_obj = 1e9
        scan = remaining[: max(80, n * 12)]
        for i, (s, sc) in enumerate(scan):
            cs = [corr(s.ticker, ps.ticker) for ps, _ in picked]
            avg_corr = float(np.mean(cs)) if cs else 0.0
            max_corr = float(np.max(cs)) if cs else 0.0
            # Objective: minimise correlation while maximising score
            obj = 1.3 * avg_corr + 0.7 * max_corr - 1.5 * sc.score
            if obj < best_obj:
                best_obj = obj
                best_idx = i
        picked.append(remaining.pop(best_idx))
    return picked
