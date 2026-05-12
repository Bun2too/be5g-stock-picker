from typing import List, Dict, Any
from .models import CandidateOut

def explain(settings: Dict[str, Any], candidates: List[CandidateOut]) -> Dict[str, Any]:
    if not candidates:
        return {"summary": "No candidates returned for the current screen settings.", "bullets": ["Try expanding the universe or relaxing risk/liquidity constraints."]}

    top = candidates[0]
    horizon = settings.get("horizon", "unknown horizon")
    risk = settings.get("risk", "unknown risk")
    strategy = settings.get("strategy", "unknown strategy")

    bullets = [
        f"Top candidate by score: {top.ticker} (score {round(top.score*100)}).",
        f"Screen settings: horizon={horizon}, risk={risk}, strategy={strategy}.",
        "Ranking is based on simplified technical metrics (momentum, volatility, drawdown) and liquidity screens.",
        "Use this as a shortlist for deeper research (business fundamentals, valuation, and news).",
    ]
    if top.flags:
        bullets.append(f"Watch-outs for the top name: {', '.join(top.flags)}")

    return {
        "summary": f"Screen complete for a {horizon} horizon and {risk} risk profile. Results reflect a simplified, explainable factor model and do not constitute investment advice.",
        "bullets": bullets
    }
