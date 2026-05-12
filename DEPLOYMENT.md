# Deployment Guide

## Recommended path

For this project's current shape, the best balance of cheap, scalable, and low-maintenance is:

- Frontend: `Netlify`
- Backend API: `Railway`
- Secrets and broker/data credentials: platform environment variables
- Database later: `Neon` (Postgres) or `Supabase Postgres`
- Background jobs later: `Railway`, `GitHub Actions`, or a future worker service

This split is usually better than forcing everything into one host:

- Netlify is excellent for static React apps and fast global delivery.
- FastAPI runs more naturally on Railway than on Netlify Functions.
- You can scale the API independently from the UI.
- Maintenance stays low because each service matches the host's strengths.

## Why not Netlify-only

Netlify is a strong frontend host, but it is not the best fit for this backend if you expect:

- long-running Python services,
- broker API integrations,
- cached screening jobs,
- future background workers,
- websocket or streaming upgrades later.

You can technically adapt FastAPI to serverless, but that usually adds complexity before the product earns it.

## Best options by goal

### Cheapest to launch

- Frontend on `Netlify`
- Backend on `Railway`

Pros:

- very low setup friction,
- simple environment variable management,
- easy custom domains,
- straightforward Docker support if needed.

Tradeoff:

- cold starts or lower baseline performance on cheaper plans.

### Lowest maintenance burden

- Frontend on `Netlify`
- Backend on `Railway`

Pros:

- simple deploys from Git,
- easy logs and environment management,
- clean support for Python web apps,
- room to add databases, variables, and additional services later.

Tradeoff:

- not always the absolute cheapest option if traffic becomes large.

### Most extendable for product growth

- Frontend on `Vercel` or `Netlify`
- Backend on `Fly.io` or `Railway`
- Database on `Neon`
- Auth on `Clerk`, `Auth0`, or Supabase Auth

Pros:

- cleaner path to multi-tenant accounts,
- background workers and persistent services are easier,
- good path toward premium subscriptions, alerts, and saved models.

Tradeoff:

- slightly more moving pieces.

## What I recommend for this repo

Start with:

1. `Netlify` for the frontend
2. `Railway` for the FastAPI backend
3. No database yet
4. Alpaca as the only live provider
5. Paper trading only until audit logs, user auth, and permission controls exist

That gives you:

- low monthly cost,
- simple CI/CD,
- easy rollback,
- enough scale for an early paid beta,
- a clean future migration path.

## Suggested architecture

### Phase 1: working beta

- React frontend calls FastAPI over HTTPS
- FastAPI handles:
  - screening
  - explain endpoint
  - paper trading endpoint
  - basic caching
- Alpaca provides market data and paper order execution

### Phase 2: paid product

Add:

- Postgres for users, saved screens, watchlists, portfolios, billing records
- auth provider
- Stripe for subscriptions
- audit logging for all orders and model actions
- provider abstraction for fundamentals and alternative data

### Phase 3: trainable user models

Add:

- feature store or model-input history tables
- async job queue for retraining
- model versioning
- human-readable explanation logs
- stronger compliance controls and user consent records

## Important product guardrails

Before enabling real-money trading or "trainable AI" workflows, add:

- explicit disclaimers and consent flows,
- audit logs,
- role-based access,
- model/version traceability,
- rate limits,
- broker action confirmations,
- clear separation between screening insights and trade execution.

## Deployment setup

### Frontend on Netlify

- Build command: use your frontend framework's production build command
- Publish directory: your frontend build output
- Environment variable:
  - `VITE_API_BASE_URL` or equivalent pointing to the backend URL

For this repo:

- Base directory: `apps/web`
- Build command: `npm run build`
- Publish directory: `dist`

### Backend on Railway

For this repo, your paid Railway account is a very sensible backend choice.

Use the backend service from `apps/api`.

Suggested settings:

- Root directory: `/apps/api`
- Watch path: `/apps/api/**`
- Start command:
  `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health check path: `/healthz`

Environment variables:

- `ALPACA_API_KEY`
- `ALPACA_API_SECRET`
- `ALPACA_BASE_URL=https://paper-api.alpaca.markets/v2`
- `ALPACA_PAPER=true`
- `PAPER_TRADING_ENABLED=false`
- `ALPACA_DATA_FEED=iex`
- `ALLOWED_ORIGINS=https://your-frontend-domain`
- `GUEST_SCREEN_LIMIT=3`
- `GUEST_QUOTA_TTL_SECONDS=86400`
- `GUEST_SESSION_COOKIE_SECURE=true`
- `GUEST_SESSION_COOKIE_SAMESITE=none`
- `WHITELISTED_IPS=`
- `BYPASS_COOKIE_NAME=stock_picker_access`
- `BYPASS_COOKIE_VALUE=`

Future Auth0 variables:

- `AUTH0_DOMAIN`
- `AUTH0_AUDIENCE=https://api.be5g.com`
- `AUTH0_ISSUER`
- `AUTH0_ALGORITHMS=RS256`

## Roadmap for completion

To turn this repo into a real subscribable product, the next build steps should be:

1. Convert `be5g_react` from prototype files into a real app package with routing, API client, and env-based backend URL.
2. Replace mock screen execution with live calls to `/api/screen` and `/api/explain`.
3. Add persistent storage for users, saved screens, watchlists, and event logs.
4. Add authentication before exposing order-placement features.
5. Add billing only after auth and persistence exist.

See [docs/auth0-subscriptions-plan.md](docs/auth0-subscriptions-plan.md) for the detailed Auth0 roles, subscription tiers, and rollout sequence.

## Hosting decision summary

## Monorepo deployment notes

This repository is an isolated monorepo:

- frontend in `apps/web`
- backend in `apps/api`

For Railway, create a dedicated backend service and set its root directory to `/apps/api`.

For Netlify, point the site at `apps/web`.

## Hosting decision summary

If you already have Railway paid:

- `Netlify + Railway` is the best fit here.

If you want the absolute simplest single-vendor developer experience:

- `Railway` can host both, but I would still keep the frontend on `Netlify` unless you want one vendor more than best-in-class static hosting.

If you want to optimize harder for future infrastructure flexibility:

- `Fly.io + Netlify` is strong, but a little more operationally involved.
