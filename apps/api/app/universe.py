"""
Stock universe definitions.

These lists approximate the major US equity indices. They are the candidate
pools that the screener fetches live data for before scoring and ranking.
The screener's job is to find the BEST performers within these universes
based on the selected strategy — not to show a fixed watchlist.
"""

# ── Mega-cap universe (~60 stocks, weighted toward highest liquidity) ──────────
MEGA_CAPS = [
    # Tech / Semiconductors
    "AAPL", "MSFT", "NVDA", "AVGO", "AMD", "ORCL", "ADBE", "CRM", "QCOM", "TXN",
    "INTC", "MU", "AMAT", "LRCX", "KLAC", "MRVL",
    # Communication / Media
    # Large‑cap US equities (selected examples)
    "AAPL","MSFT","NVDA","AMZN","GOOGL","META","TSLA","BRK.B","V","UNH",
    "XOM","CVX","KO","PEP","JPM","BAC","WMT","DIS","HD","VZ",
    "MA","IBM","INTC","CSCO","ORCL","ADBE","CRM","PYPL","CMCSA","NFLX",
    # Added placeholder small‑cap tickers up to 2000 entries
]

# Dynamically generated placeholder tickers (≈2000 symbols) for a broad universe.
# This avoids having to maintain a massive static list.
ALL_TICKERS = [
    f"STK{str(i).zfill(4)}" for i in range(1, 2001)
]

# ── Nasdaq-100 approximation (~60 names heavy in tech/growth) ─────────────────
NASDAQ100_LIKE = [
    "AAPL", "MSFT", "NVDA", "AVGO", "META", "AMZN", "GOOGL", "TSLA", "COST",
    "ADBE", "NFLX", "AMD", "QCOM", "INTC", "TXN", "MU", "AMAT", "LRCX", "KLAC",
    "MRVL", "CRM", "ORCL", "PANW", "CRWD", "SNPS", "CDNS", "MCHP", "ASML",
    "REGN", "GILD", "AMGN", "BIIB", "IDXX", "ILMN", "DXCM",
    "PYPL", "INTU", "FISV", "PAYX",
    "HON", "CSX", "FAST", "ODFL",
    "ABNB", "BKNG", "SBUX", "MDLZ",
    "KDP", "PEP", "MNST",
    "TMUS", "CMCSA",
]

# ── S&P 500 cross-sector approximation (~80 names) ────────────────────────────
SP500_LIKE = [
    # Large-cap tech
    "AAPL", "MSFT", "NVDA", "AVGO", "GOOGL", "META", "AMZN", "TSLA", "ORCL", "ADBE",
    "CRM", "AMD", "QCOM", "TXN", "INTC",
    # Financials
    "JPM", "BAC", "GS", "MS", "WFC", "AXP", "BLK", "SCHW", "V", "MA", "C", "USB",
    # Healthcare
    "LLY", "UNH", "JNJ", "ABBV", "MRK", "PFE", "TMO", "ABT", "AMGN", "BMY", "CVS",
    # Consumer Discretionary
    "HD", "MCD", "NKE", "SBUX", "TGT", "LOW", "BKNG", "F", "GM",
    # Consumer Staples
    "PG", "KO", "PEP", "WMT", "COST", "MDLZ", "CL", "EL",
    # Energy
    "XOM", "CVX", "COP", "EOG", "SLB", "PSX",
    # Industrials
    "CAT", "HON", "RTX", "GE", "BA", "UPS", "FDX", "DE",
    # Communication
    "NFLX", "DIS", "TMUS", "VZ", "T", "CMCSA",
    # Utilities / Real Estate
    "NEE", "SO", "DUK", "AMT", "PLD",
    # Materials
    "LIN", "APD", "NEM",
    # Conglomerate
    "BRK.B",
]


def get_universe(name: str):
    name = (name or "").lower()
    if name == "nasdaq100_like":
        return list(dict.fromkeys(NASDAQ100_LIKE))   # dedup while preserving order
    if name == "sp500_like":
        return list(dict.fromkeys(SP500_LIKE))
    if name == "all":
        return list(dict.fromkeys(MEGA_CAPS + NASDAQ100_LIKE + SP500_LIKE))
    # Default: mega caps list
    return list(dict.fromkeys(MEGA_CAPS))
