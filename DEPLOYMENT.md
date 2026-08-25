# Deployment Guide

## Recommended path

For this project's current shape, the best balance of cheap, scalable, and low-maintenance is:

- Frontend: `Netlify`
- Backend API: `Railway`
- Secrets and broker/data credentials: platform environment variables
- Symbol/portfolio persistence and scheduled market jobs: optional AWS sub-project in [`infra/aws`](infra/aws)
- Database later for relational product data: `Neon` (Postgres) or `Supabase Postgres`
- Background jobs later for app-specific workflows: `Railway`, `GitHub Actions`, or a future worker service

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

## CI/CD Pipeline (GitHub Actions)

This repository includes a production-ready GitHub Actions workflow in [`.github/workflows/ci-cd.yml`](.github/workflows/ci-cd.yml).

### Pipeline Stages

1. **Test**:
   - `apps/api`: Runs `pytest` in Python 3.12 with simulated credentials.
   - `apps/web`: Runs `vitest` in Node 24.
2. **Build**:
   - `apps/web`: Executes `npm run build` with injected production variables and saves `dist/` as a pipeline artifact.
3. **Deploy** (Triggered automatically on push to `main`):
   - **Frontend → Netlify**: Uses Netlify CLI to deploy `dist/` directly to your production site.
   - **Backend → Railway**: Uses Railway CLI (`railway up apps/api --path-as-root`) to deploy the `apps/api` service from its Dockerfile.

### Required GitHub Repository Secrets

In your GitHub repository, navigate to **Settings → Secrets and variables → Actions → New repository secret** and add:

| Secret Name | Description | Example / Source |
|---|---|---|
| `NETLIFY_AUTH_TOKEN` | Netlify Personal Access Token with access to the target team/site | Netlify User Settings → Applications → Personal access tokens |
| `NETLIFY_SITE_ID` | Netlify Project ID, formerly Site ID | Netlify Project configuration → General → Project details → Project information |
| `RAILWAY_TOKEN` | Railway project token for the target project/environment | Railway project settings → Tokens |
| `RAILWAY_API_TOKEN` *(Alternative)* | Railway account/workspace token if you do not use a project token | Railway account/workspace settings → Tokens |
| `RAILWAY_PROJECT_ID` | Railway Project ID containing the backend service | Railway project settings |
| `RAILWAY_ENVIRONMENT_ID` *(Preferred)* | Railway environment ID for the deployment target | Railway environment settings |
| `RAILWAY_ENVIRONMENT_NAME` *(Alternative)* | Railway environment name if you do not set `RAILWAY_ENVIRONMENT_ID` | `production` |
| `RAILWAY_SERVICE_ID` | Railway Service ID for `apps/api` | Railway project → Service Settings → Service ID |
| `VITE_API_BASE_URL` | Live Backend API URL | `https://your-backend.railway.app` |
| `VITE_API_KEY` | Backend internal access key | Same value as `API_KEY` in Railway |
| `VITE_AUTH0_DOMAIN` *(Optional)* | Auth0 Domain | `dev-bun2too.us.auth0.com` |
| `VITE_AUTH0_CLIENT_ID` *(Optional)* | Auth0 Client ID | Your Auth0 SPA Client ID |
| `VITE_AUTH0_AUDIENCE` *(Optional)* | Auth0 Audience | `https://api.be5g.com` |

Railway token notes:

- Prefer `RAILWAY_TOKEN` as a project-scoped token for CI deployments.
- Use `RAILWAY_API_TOKEN` only if you are using an account/workspace token.
- Do not set both at the same time; the Railway CLI expects only one Railway auth token type.
- If CI says `Invalid RAILWAY_TOKEN`, regenerate a project token for the same Railway project/environment as `RAILWAY_PROJECT_ID` and replace the GitHub secret.
- If CI says `Service not found`, `RAILWAY_SERVICE_ID` is wrong or it does not belong to `RAILWAY_PROJECT_ID` + `RAILWAY_ENVIRONMENT_ID`/name.

Railway Dockerfile notes:

- The backend Dockerfile lives at `apps/api/Dockerfile`.
- The GitHub Actions deploy command passes `apps/api --path-as-root` so Railway treats `apps/api` as the uploaded source root and sees `Dockerfile` there.
- If you deploy from the Railway dashboard instead of this workflow, either set the service root directory to `apps/api` or configure the service's Dockerfile path as `apps/api/Dockerfile`.
- In Railway build logs, look for `Using detected Dockerfile!` to confirm Railway is using Docker instead of automatic Railpack detection.

Netlify token notes:

- `NETLIFY_SITE_ID` must be the Project ID, not the display name unless you intentionally deploy by name.
- `NETLIFY_AUTH_TOKEN` must belong to a user/team that can access that Project ID.
- If CI says `Failed retrieving site data ... Not Found`, either the Project ID is wrong or the token does not have access to that site/team.

---

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
- `SYMBOL_STORE_BACKEND=json`

Optional AWS DynamoDB persistence from [`infra/aws`](infra/aws):

- `SYMBOL_STORE_BACKEND=dynamodb`
- `AWS_REGION=us-east-1`
- `AWS_SYMBOLS_TABLE=<terraform output symbols_table_name>`
- `AWS_PORTFOLIOS_TABLE=<terraform output portfolios_table_name>`
- `AWS_ACCESS_KEY_ID=<Railway API IAM access key>`
- `AWS_SECRET_ACCESS_KEY=<Railway API IAM secret key>`

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

For Railway, create a dedicated backend service for the FastAPI app. In GitHub Actions, the workflow deploys it with:

```bash
npx @railway/cli@5.41.2 up apps/api --path-as-root \
  --project "$RAILWAY_PROJECT_ID" \
  --environment "$RAILWAY_ENVIRONMENT_ID" \
  --service "$RAILWAY_SERVICE_ID" \
  --detach
```

That makes `apps/api` the source root for the uploaded archive, so Railway detects `apps/api/Dockerfile` as the root `Dockerfile`. If you use Railway dashboard autodeploys instead, set the service root directory to `apps/api`.

For Netlify, point the site at `apps/web`.

## Hosting decision summary

If you already have Railway paid:

- `Netlify + Railway` is the best fit here.

If you want the absolute simplest single-vendor developer experience:

- `Railway` can host both, but I would still keep the frontend on `Netlify` unless you want one vendor more than best-in-class static hosting.

If you want to optimize harder for future infrastructure flexibility:

- `Fly.io + Netlify` is strong, but a little more operationally involved.
