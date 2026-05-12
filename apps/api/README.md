# Portfolio Screening Backend

This is a minimal FastAPI backend that:
- Pulls market data from **Alpaca Market Data API**
- Computes technical metrics (momentum, vol, drawdown, liquidity)
- Ranks candidates based on a simple, explainable scoring model
- Optionally places **paper** orders via Alpaca Trading API

> This is a *portfolio assistant / screener* prototype. It is **not** financial advice or a trade signal generator.

## 1) Prereqs
- Python 3.10+
- An Alpaca account + API keys
- (Optional) Alpaca **Algo Trader Plus** subscription for full real-time market data, especially if you plan to use it intraday.

## 2) Environment variables
Copy `.env.example` to `.env` in `apps/api/`:

```
cp .env.example .env
```

Then fill in:

```
ALPACA_API_KEY=...
ALPACA_API_SECRET=...
ALPACA_BASE_URL=https://paper-api.alpaca.markets/v2
ALPACA_PAPER=true              # true = paper trading
ALPACA_DATA_FEED=sip           # sip or iex (sip requires real-time entitlement/subscription)
ALLOWED_ORIGINS=http://localhost:3000
```

Notes:
- `ALPACA_DATA_FEED=iex` works on the free/basic plan but can be incomplete for live decisioning.
- `ALPACA_DATA_FEED=sip` is full consolidated feed and typically requires a subscription/entitlements.
- Local configuration lives in `apps/api/.env`. Production secrets should be set as Railway environment variables, not committed to the repo.
- Auth0 and subscription planning is documented in [../../docs/auth0-subscriptions-plan.md](../../docs/auth0-subscriptions-plan.md).

## 3) Run locally
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

uvicorn app.main:app --reload --port 8000
```

Open:
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/healthz

## 4) Try it (curl)
### Screen candidates
```
curl -s http://localhost:8000/api/screen \
  -H 'Content-Type: application/json' \
  -d '{
    "horizon":"1y",
    "risk":"medium",
    "strategy":"momentum",
    "universe":"mega_caps",
    "plannedVolumeUsd":5000,
    "portfolioSize":8,
    "diversification":"balanced"
  }'
```

### Market snapshot for tickers
```
curl -s http://localhost:8000/api/market/snapshot \
  -H 'Content-Type: application/json' \
  -d '{"tickers":["AAPL","MSFT","NVDA"], "lookbackDays":260}'
```

### Paper order (disabled unless you set ALPACA_PAPER=true)
```
curl -s http://localhost:8000/api/trading/paper/order \
  -H 'Content-Type: application/json' \
  -d '{"symbol":"AAPL","side":"buy","qty":1,"type":"market"}'
```

## 5) Frontend integration
Your React UI can call:
- POST /api/screen
- POST /api/market/snapshot
- POST /api/explain (optional narrative)

Set your frontend base URL to `http://localhost:8000`.

## 6) Next upgrades (recommended)
- Add a proper universe source (S&P 500 / Nasdaq-100 constituents)
- Add fundamentals (PE, FCF yield, dividend yield) via a fundamentals provider
- Add correlation-based diversification (already included) but scale it with caching/async jobs
- Add user accounts, watchlists, saved screens, and audit logs

## 7) Deployment

See [../DEPLOYMENT.md](../DEPLOYMENT.md) for the recommended hosting setup and rollout path.
