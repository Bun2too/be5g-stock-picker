# Stock Picker Workspace

This repository is organized as a small product workspace:

- `apps/web` - React + Vite frontend
- `apps/api` - FastAPI backend

## Single-command workflows

From the repo root:

```bash
make setup
make dev
make test
make package
```

## Hosting recommendation

`Netlify + Railway` is a strong fit for this repo.

- Use `Netlify` for the frontend.
- Use `Railway` for the FastAPI backend.
- Keep Alpaca secrets only in Railway.

That split keeps the UI fast and simple while letting Railway handle the long-running Python API cleanly.

See [DEPLOYMENT.md](DEPLOYMENT.md) for the deployment rollout and hosting guidance.
For a same-day release checklist, use [docs/launch-today.md](docs/launch-today.md).

## Product auth and subscriptions

The Auth0 role model, account hierarchy, and subscription tiers are planned in
[docs/auth0-subscriptions-plan.md](docs/auth0-subscriptions-plan.md).

Alpaca backend configuration lives in `apps/api/.env` locally and should be set
as Railway environment variables in production.
