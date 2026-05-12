# Launch Today Runbook

Use this path for the fastest safe launch:

- Frontend: Netlify
- Backend: Railway
- Public app URL: `https://stocks.be5g.com` recommended for today
- API URL: Railway-generated URL first, then `https://api.be5g.com` later if DNS is ready

`stocks.be5g.com` is recommended over a subpath like `be5g.com/stocks` because Auth0 callback URLs, Netlify routing, CORS, and API origins are simpler.

## 1. Railway Backend

Create a Railway service from this repository.

Settings:

- Root directory: `apps/api`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health check path: `/healthz`

Environment variables:

```bash
ALPACA_API_KEY=your_alpaca_key
ALPACA_API_SECRET=your_alpaca_secret
ALPACA_BASE_URL=https://paper-api.alpaca.markets/v2
ALPACA_PAPER=true
PAPER_TRADING_ENABLED=false
ALPACA_DATA_FEED=iex
ALLOWED_ORIGINS=https://stocks.be5g.com
SNAPSHOT_CACHE_TTL_SECONDS=600
GUEST_SCREEN_LIMIT=3
GUEST_QUOTA_TTL_SECONDS=86400
GUEST_SESSION_COOKIE_SECURE=true
GUEST_SESSION_COOKIE_SAMESITE=none
WHITELISTED_IPS=
BYPASS_COOKIE_NAME=stock_picker_access
BYPASS_COOKIE_VALUE=
```

After deploy, open:

```text
https://your-railway-api-url/healthz
```

It should return `ok: true`.

## 2. Netlify Frontend

Create a Netlify site from this repository.

Settings are already in `netlify.toml`:

- Base directory: `apps/web`
- Build command: `npm run build`
- Publish directory: `dist`

Environment variables:

```bash
VITE_API_BASE_URL=https://your-railway-api-url
```

Deploy once with the temporary Netlify URL first. After the custom domain is connected, update `VITE_API_BASE_URL` if you move the API to a custom domain and redeploy.

## 3. Guest Usage Limits

For the public beta, Auth0 login is disabled and the API limits guest usage by client IP plus a server-issued session cookie.

Default behavior:

- Each guest gets `GUEST_SCREEN_LIMIT=3` successful screens per `GUEST_QUOTA_TTL_SECONDS=86400`.
- `WHITELISTED_IPS` can include exact IPs or CIDR ranges, comma-separated.
- `BYPASS_COOKIE_VALUE` can be set to a high-entropy token. Requests with cookie `BYPASS_COOKIE_NAME=that-token` are exempt.
- Keep `GUEST_SESSION_COOKIE_SECURE=true` and `GUEST_SESSION_COOKIE_SAMESITE=none` when Netlify and Railway are on different domains.

## 4. DNS

For `stocks.be5g.com`, add the DNS record Netlify gives you.

For `api.be5g.com`, add it later after the frontend is working, or use the Railway domain for launch day.

## 5. Smoke Test

Test in this order:

1. Open `/healthz` on the Railway API.
2. Open the Netlify frontend.
3. Confirm the API status panel shows healthy.
4. Confirm the guest access panel shows 3 free screens.
5. Run a screen.
6. Confirm the guest access panel decrements remaining usage.

## 6. Launch Guardrails

For launch day:

- Keep `PAPER_TRADING_ENABLED=false`.
- Do not enable live trading.
- Keep `ALPACA_DATA_FEED=iex` unless your Alpaca account has SIP entitlement.
- Put Alpaca credentials only in Railway, never in Netlify.
- Use the guest quota for the public launch. Add Auth0 and subscription billing after backend authorization and persistent usage storage are ready.
