# Auth0, Roles, and Subscription Plan

This app should treat Auth0 as the identity provider, the FastAPI backend as the authorization enforcement point, and Stripe as the subscription/payment source of truth.

## Target URLs

- Public app: `https://be5g.com/stocks` or `https://stocks.be5g.com`
- API: `https://api.be5g.com`
- Local web: `http://localhost:5173`
- Local API: `http://localhost:8000`

For early launch, a subdomain is cleaner than a subpath because Auth0 callbacks, CORS, cookies, and API routing stay simpler. Use `stocks.be5g.com` for the app and keep `be5g.com` available for marketing.

## Auth0 Tenants and Applications

Create one Auth0 tenant for production and optionally one for development.

Recommended Auth0 apps/APIs:

- Single Page Application: `BE5G Stock Picker Web`
- API: `BE5G Stock Picker API`
- API audience: `https://api.be5g.com`
- Allowed callback URLs: `http://localhost:5173`, `https://stocks.be5g.com`
- Allowed logout URLs: `http://localhost:5173`, `https://stocks.be5g.com`
- Allowed web origins: `http://localhost:5173`, `https://stocks.be5g.com`

## Role Model

Roles should be enforced by the backend from JWT claims plus local tenant membership records.

| Role | Purpose | Initial Permissions |
| --- | --- | --- |
| `end_user` | Normal subscriber or free user | Run screens, manage own watchlists, view own history |
| `moderator` | Support and content safety | View support metadata, review flagged workflows, no trading authority |
| `group_admin` | Organization/team owner | Manage seats, invite users, view group usage, assign group roles |
| `global_admin` | BE5G operator | Manage plans, users, orgs, feature flags, audit logs |

Do not rely only on frontend hiding. Every protected backend endpoint should check the required role and the user's tenant/org membership.

## Subscription Tiers

| Tier | Price | Audience | Suggested Limits |
| --- | ---: | --- | --- |
| Free | `$0` | First-time users | 5 screens/day, mega-cap universe, no saved models, delayed/basic data feed |
| Level 1 | `$10/month` | Individual active users | 100 screens/day, saved screens/watchlists, larger universes, email summaries |
| Level 2 | `$29-$49/month` | Power users | Higher limits, advanced strategies, portfolio exports, priority jobs, richer analytics |
| Enterprise | Custom | Groups, advisors, integrations | SSO, team admin, custom data providers, API access, custom compliance/audit exports |

Auth0 handles identity. Stripe handles plans, checkout, invoices, coupons, upgrades, cancellations, and customer portal. The app stores a local entitlement snapshot so feature checks are fast and auditable.

## Backend Data Model to Add

Use Postgres before production auth/billing launch.

Core tables:

- `users`: Auth0 subject, email, display name, status, created time
- `organizations`: name, plan, Stripe customer id, status
- `memberships`: user id, organization id, role
- `subscriptions`: Stripe subscription id, plan, status, current period dates
- `entitlements`: normalized feature limits per org/user
- `usage_events`: screen runs, explain calls, paper order attempts, exports
- `audit_logs`: role changes, billing changes, order submissions, admin actions
- `saved_screens`, `watchlists`, `portfolios`: user-owned product data

## Endpoint Protection Plan

Initial route policy:

- Public: `/healthz`
- Authenticated free+: `/api/screen`, `/api/explain`, `/api/market/snapshot`
- Level 1+: saved screens, watchlists, usage history
- Level 2+: exports, larger universes, advanced analytics
- Group admin+: invite users, manage memberships, view group usage
- Global admin: admin console endpoints and feature flags
- Explicitly gated: `/api/trading/paper/order`

Paper trading should require authenticated users, explicit user consent, an audit log entry, and a plan/role check. Live trading should stay disabled until there are stronger compliance and risk controls.

## Implementation Sequence

1. Add Auth0 SPA SDK to `apps/web` and protect the React app.
2. Add JWT validation middleware/dependencies to `apps/api`.
3. Add Postgres and the user/org/membership/subscription tables.
4. Sync Auth0 signup/login users into the local `users` table.
5. Add role checks and subscription entitlement checks to backend endpoints.
6. Add Stripe Checkout and webhooks to update local subscription state.
7. Add an account/billing page and group admin page.
8. Add audit logs before exposing paper order placement to real users.

## Environment Variables

Backend:

```bash
AUTH0_DOMAIN=your-tenant.us.auth0.com
AUTH0_AUDIENCE=https://api.be5g.com
AUTH0_ISSUER=https://your-tenant.us.auth0.com/
AUTH0_ALGORITHMS=RS256
STRIPE_SECRET_KEY=...
STRIPE_WEBHOOK_SECRET=...
DATABASE_URL=...
```

Frontend:

```bash
VITE_AUTH0_DOMAIN=your-tenant.us.auth0.com
VITE_AUTH0_CLIENT_ID=...
VITE_AUTH0_AUDIENCE=https://api.be5g.com
VITE_AUTH0_REDIRECT_URI=https://stocks.be5g.com
```
