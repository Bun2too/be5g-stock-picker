from fastapi import FastAPI, HTTPException, Request, Response, Security
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, List
import hmac
import secrets
import pandas as pd

from .config import settings
from .models import (
    MarketSnapshotRequest, ScreenRequest, ScreenResponse, CandidateOut,
    ExplainRequest, ExplainResponse, PaperOrderRequest, SymbolSearchResponse,
    PortfolioRequest, PortfolioResponse
)
from .universe import get_universe
from .symbol_store import catalog_meta, get_portfolio, save_portfolio, search_symbols, symbols_for_screen
from .alpaca_client import AlpacaAdapter
from .scoring import score_snapshot, diversify_by_correlation
from .explainer import explain

from cachetools import TTLCache

app = FastAPI(title="Portfolio Screening Backend (Alpaca-first)", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response: Response = await call_next(request)
    # Prevent browsers from MIME-sniffing a response away from the declared content-type
    response.headers["X-Content-Type-Options"] = "nosniff"
    # Prevent clickjacking by denying iframe embedding
    response.headers["X-Frame-Options"] = "DENY"
    # Enable XSS protection filter
    response.headers["X-XSS-Protection"] = "1; mode=block"
    # Strict Transport Security (HSTS)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    # Disallow content that doesn't originate from the site itself
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    # Referrer Policy
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

snapshot_cache = TTLCache(maxsize=128, ttl=settings.snapshot_cache_ttl_seconds)
guest_usage_cache = TTLCache(maxsize=10000, ttl=settings.guest_quota_ttl_seconds)

# ── API Key authentication ────────────────────────────────────────────────────
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_api_key(api_key: str = Security(_api_key_header)) -> None:
    """Dependency: reject requests whose X-API-Key doesn't match API_KEY env var.
    If API_KEY is not configured the check is skipped (dev / first-boot grace)."""
    if not settings.api_key:
        return  # Not configured — allow through (warn in logs)
    if not api_key or not hmac.compare_digest(api_key, settings.api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")

def _client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"

def _has_bypass_cookie(request: Request) -> bool:
    if not settings.bypass_cookie_value:
        return False

    cookie_value = request.cookies.get(settings.bypass_cookie_name)
    if not cookie_value:
        return False

    return hmac.compare_digest(cookie_value, settings.bypass_cookie_value)

def _get_or_set_guest_session(request: Request, response: Response) -> str:
    session_id = request.cookies.get(settings.guest_session_cookie_name)
    if session_id:
        return session_id

    session_id = secrets.token_urlsafe(24)
    response.set_cookie(
        key=settings.guest_session_cookie_name,
        value=session_id,
        max_age=settings.guest_quota_ttl_seconds,
        httponly=True,
        secure=settings.guest_session_cookie_secure,
        samesite=settings.guest_session_cookie_samesite,
    )
    return session_id

def _quota_key(request: Request, response: Response) -> str:
    ip = _client_ip(request)
    session_id = _get_or_set_guest_session(request, response)
    return f"{ip}:{session_id}"

def _quota_status(request: Request, response: Response) -> Dict[str, Any]:
    ip = _client_ip(request)
    exempt = settings.is_whitelisted_ip(ip) or _has_bypass_cookie(request)
    if exempt:
        return {
            "limit": settings.guest_screen_limit,
            "used": 0,
            "remaining": None,
            "exempt": True,
        }

    key = _quota_key(request, response)
    used = int(guest_usage_cache.get(key, 0))
    remaining = max(settings.guest_screen_limit - used, 0)
    return {
        "limit": settings.guest_screen_limit,
        "used": used,
        "remaining": remaining,
        "exempt": False,
    }

def _enforce_guest_quota(request: Request, response: Response) -> Dict[str, Any]:
    quota = _quota_status(request, response)
    if quota["exempt"] or quota["remaining"] > 0:
        return quota

    raise HTTPException(
        status_code=429,
        detail={
            "message": "You have used your free guest screens. Sign up for a subscription to unlock more usage.",
            "quota": quota,
        },
    )

def _record_guest_screen(request: Request, response: Response) -> Dict[str, Any]:
    quota = _quota_status(request, response)
    if quota["exempt"]:
        return quota

    key = _quota_key(request, response)
    used = int(guest_usage_cache.get(key, 0)) + 1
    guest_usage_cache[key] = used
    quota["used"] = used
    quota["remaining"] = max(settings.guest_screen_limit - used, 0)
    return quota

@app.get("/healthz")
def healthz(request: Request, response: Response):
    return {
        "ok": True,
        "alpacaConfigured": settings.alpaca_configured,
        "auth0Configured": settings.auth0_configured,
        "stripeConfigured": settings.stripe_configured,
        "missingAlpacaFields": settings.missing_alpaca_fields,
        "mode": "paper" if settings.alpaca_paper else "live",
        "feed": settings.alpaca_data_feed,
        "alpacaBaseUrl": settings.alpaca_base_url,
        "paperTradingEnabled": settings.paper_trading_enabled,
        "guestQuota": _quota_status(request, response),
    }

@app.get("/api/plans")
def plans():
    return {
        "plans": [
            {
                "id": "free",
                "name": "Observer",
                "price": "$0",
                "period": "launch",
                "highlight": False,
                "limits": {
                    "screensPerDay": settings.guest_screen_limit,
                    "universes": ["mega_caps", "mixed_portfolio"],
                    "savedScreens": 0,
                },
                "features": [
                    "3 guest screens per day",
                    "Mega-cap universe",
                    "Multi-factor momentum & volatility scoring",
                    "Custom portfolio symbol builder",
                ],
                "checkoutUrl": None,
            },
            {
                "id": "level_1",
                "name": "Catalyst",
                "price": "$10",
                "period": "month",
                "highlight": True,
                "limits": {
                    "screensPerDay": 100,
                    "universes": ["mega_caps", "nasdaq100_like", "sp500_like", "us_most_traded", "mixed_portfolio"],
                    "savedScreens": 25,
                },
                "features": [
                    "100 screens per day",
                    "All US universes (S&P 500, Nasdaq-100, US 1000)",
                    "Saved watchlists & portfolio tracking",
                    "Email summary workflows",
                    "Priority screening jobs",
                ],
                "checkoutUrl": settings.stripe_level1_checkout_url or "https://buy.stripe.com/dRm6oH2zxduG2Yc8Drds400",
            },
            {
                "id": "level_2",
                "name": "Alpha",
                "price": "$29",
                "period": "month",
                "highlight": False,
                "limits": {
                    "screensPerDay": 500,
                    "universes": ["mega_caps", "nasdaq100_like", "sp500_like", "us_most_traded", "tw_popular", "mixed_portfolio"],
                    "savedScreens": 100,
                },
                "features": [
                    "500 screens per day",
                    "Full US + Taiwan market catalog",
                    "Advanced correlation & factor analytics",
                    "Unlimited portfolio exports",
                    "Custom alert workflows & priority support",
                ],
                "checkoutUrl": settings.stripe_level2_checkout_url or "https://buy.stripe.com/bJe9AT1vt62ebuI8Drds401",
            },
        ],
        "billingPortalUrl": settings.stripe_billing_portal_url,
    }

@app.get("/api/symbols", response_model=SymbolSearchResponse, dependencies=[Security(verify_api_key)])
def symbols(q: str = "", market: str = "", limit: int = 50):
    markets = [part.strip().upper() for part in market.split(",") if part.strip()]
    return SymbolSearchResponse(
        symbols=search_symbols(query=q, markets=markets, limit=limit),
        meta=catalog_meta(),
    )

@app.get("/api/portfolio", response_model=PortfolioResponse, dependencies=[Security(verify_api_key)])
def get_saved_portfolio(request: Request, response: Response):
    owner_key = _quota_key(request, response)
    return PortfolioResponse(**get_portfolio(owner_key))

@app.put("/api/portfolio", response_model=PortfolioResponse, dependencies=[Security(verify_api_key)])
def put_saved_portfolio(req: PortfolioRequest, request: Request, response: Response):
    owner_key = _quota_key(request, response)
    return PortfolioResponse(**save_portfolio(owner_key, req.symbols))

def get_alpaca() -> AlpacaAdapter:
    if not settings.alpaca_configured:
        raise HTTPException(
            status_code=503,
            detail=f"Alpaca credentials are not configured. Missing: {', '.join(settings.missing_alpaca_fields)}.",
        )
    return AlpacaAdapter()

def _cache_key(tickers: List[str], lookback: int, feed: str) -> str:
    t = ",".join(sorted(set([x.upper() for x in tickers])))
    return f"{feed}:{lookback}:{t}"

@app.post("/api/market/snapshot", dependencies=[Security(verify_api_key)])
def market_snapshot(req: MarketSnapshotRequest) -> Dict[str, Any]:
    alpaca = get_alpaca()
    tickers = [t.upper().strip() for t in req.tickers if t.strip()]
    if not tickers:
        raise HTTPException(status_code=400, detail="No tickers provided.")

    key = _cache_key(tickers, req.lookbackDays, settings.alpaca_data_feed)
    if key in snapshot_cache:
        return {"feed": settings.alpaca_data_feed, "snapshots": snapshot_cache[key], "cached": True}

    snaps = alpaca.compute_snapshots(tickers, lookback_days=req.lookbackDays)
    out = {k: vars(v) for k, v in snaps.items()}
    snapshot_cache[key] = out
    return {"feed": settings.alpaca_data_feed, "snapshots": out, "cached": False}

@app.post("/api/screen", response_model=ScreenResponse, dependencies=[Security(verify_api_key)])
def screen(req: ScreenRequest, request: Request, response: Response):
    _enforce_guest_quota(request, response)
    alpaca = get_alpaca()
    symbol_meta = symbols_for_screen(req.universe, req.selectedSymbols)
    if symbol_meta:
        skipped = [item for item in symbol_meta if item.get("market") != "US"]
        tickers = [item["providerSymbol"] for item in symbol_meta if item.get("market") == "US"]
        meta_by_provider = {item["providerSymbol"].upper(): item for item in symbol_meta}
    else:
        skipped = []
        tickers = get_universe(req.universe)
        meta_by_provider = {}
    notes: List[str] = []
    if skipped:
        notes.append(
            f"Skipped {len(skipped)} Taiwan symbols because this deployment's live screener uses Alpaca US equities. Add a Taiwan market data adapter to score TWSE names."
        )
    if not tickers:
        raise HTTPException(status_code=400, detail="No US-screenable tickers selected. Pick US symbols or configure a Taiwan data provider.")
    bars = alpaca.fetch_daily_bars(tickers, lookback_days=260)
    if bars.empty:
        raise HTTPException(status_code=502, detail="No market data returned. Check Alpaca credentials/feed/subscription.")

    snapshots = alpaca.compute_snapshots(tickers, lookback_days=260)

    returns_by_ticker: Dict[str, pd.Series] = {}
    for t, g in bars.groupby("ticker"):
        g = g.sort_values("ts")
        closes = g["close"].astype(float)
        returns_by_ticker[t] = closes.pct_change()

    ranked = []
    for t, snap in snapshots.items():
        scored = score_snapshot(
            snap=snap,
            horizon=req.horizon,
            risk=req.risk,
            strategy=req.strategy,
            planned_volume_usd=req.plannedVolumeUsd,
        )
        ranked.append((snap, scored))

    ranked.sort(key=lambda x: x[1].score, reverse=True)

    if req.diversification == "balanced":
        picked = diversify_by_correlation(ranked, returns_by_ticker, n=req.portfolioSize)
        notes.append("Balanced diversification uses a correlation-aware greedy selection (technical-only).")
    else:
        picked = ranked[: req.portfolioSize]

    out: List[CandidateOut] = []
    for snap, sc in picked:
        out.append(CandidateOut(
            ticker=snap.ticker,
            name=meta_by_provider.get(snap.ticker.upper(), {}).get("name"),
            sector=None,
            price=snap.price,
            advUsd=snap.adv_usd,
            vol30=snap.vol30,
            drawdown1y=snap.drawdown1y,
            momentum3m=snap.momentum3m,
            momentum1y=snap.momentum1y,
            dividendYield=0.0,
            valueScore=0.0,
            qualityScore=0.0,
            score=sc.score,
            flags=sc.flags,
            rationale=sc.rationale,
        ))

    if req.strategy in ("quality_value","dividend"):
        notes.append("This Alpaca-only prototype does not fetch fundamentals (PE/FCF/dividend yield). Add a fundamentals provider for true value/dividend scoring.")

    quota = _record_guest_screen(request, response)
    return ScreenResponse(settings={**req.model_dump(), "guestQuota": quota}, candidates=out, notes=notes)

@app.post("/api/explain", response_model=ExplainResponse, dependencies=[Security(verify_api_key)])
def explain_screen(req: ExplainRequest):
    payload = explain(req.settings, req.candidates)
    return ExplainResponse(**payload)

@app.post("/api/trading/paper/order", dependencies=[Security(verify_api_key)])
def paper_order(req: PaperOrderRequest):
    if not settings.paper_trading_enabled:
        raise HTTPException(
            status_code=403,
            detail="Paper trading is disabled for launch. Enable PAPER_TRADING_ENABLED=true only after auth and audit logging are enforced.",
        )

    try:
        alpaca = get_alpaca()
        order = alpaca.place_paper_order(
            symbol=req.symbol.upper().strip(),
            side=req.side,
            qty=req.qty,
            order_type=req.type,
            limit_price=req.limit_price,
            tif=req.time_in_force,
        )
        return {"ok": True, "order": order.model_dump() if hasattr(order, "model_dump") else str(order)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
