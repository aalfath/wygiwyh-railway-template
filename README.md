[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/new/template/wygiwyh-1?utm_medium=integration&utm_source=button&utm_campaign=wygiwyh)

# WYGIWYH on Railway

One-click [Railway](https://railway.com) template for [WYGIWYH](https://github.com/eitchtee/WYGIWYH), the open-source, multi-currency personal finance tracker ("What You Get Is What You Have").

- **App:** WYGIWYH **0.28.0**, official image `eitchtee/wygiwyh:0.28.0@sha256:d8f08eaa3e19955400746059636da91211335206a77fcce562587c80c435c826`
- **Licence:** WYGIWYH is AGPL-3.0. The wrapper in this repo is MIT.
- **Fits Railway's Free plan:** about 290 MB of 512 MB RAM on 1 vCPU, and a single volume (Postgres).

## What the template deploys

| Service | What it does |
|---|---|
| `WYGIWYH` | Built from this repo. The Django web app (gunicorn, port 8080, health check `/login/`) and the procrastinate background worker (recurring transactions, exchange rates, clean-up) in one container. Public HTTPS domain. |
| `Postgres` | Railway's PostgreSQL, on its own volume. |
| `Bucket` | A private Railway Bucket (S3-compatible) for transaction and split attachments. Downloads go through WYGIWYH's login-protected views. |

The wrapper (`Dockerfile`, `railway-start.sh`, `railway_bootstrap.py`, `storage.py`):

- waits for Postgres, then applies migrations under a Postgres advisory lock (overlapping deploys never migrate twice), before the public port opens;
- creates the admin from `ADMIN_EMAIL` / `ADMIN_PASSWORD` the first time, when no admin exists yet, and refuses to start if it can't. Local sign-up is off in WYGIWYH, so nobody else can register;
- sets `DJANGO_ALLOWED_HOSTS`, `URL` (CSRF origins), Secure cookies and the proxy HTTPS header from Railway's domain;
- stores attachments in the Railway Bucket through `django-storages` (same `PrivateMediaStorage` class name as upstream, so migrations are unchanged; without bucket variables it falls back to the local folder);
- sizes gunicorn from the container's own CPU and memory limits (not the host's), keeps numeric libraries to one thread, and runs gunicorn and the worker without supervisord, so if either stops the container exits non-zero and Railway's `ON_FAILURE` policy restarts it.

## Variables

| Variable | Default | Notes |
|---|---|---|
| `ADMIN_EMAIL` | `admin@example.com` | Email of the first admin; WYGIWYH signs in by email. Used only when no admin exists. |
| `ADMIN_PASSWORD` | generated | Copy it from the service's Variables to sign in. Change it later in WYGIWYH. |
| `SECRET_KEY` | generated | Django secret key. |
| `PORT` | `8080` | Port gunicorn listens on. |
| `SQL_*` | references to `Postgres` | Database connection. |
| `AWS_*` | references to `Bucket` | Attachment storage. |

Optional: `TZ`, `ENABLE_SOFT_DELETE`, `KEEP_DELETED_ENTRIES_FOR`, `OIDC_*` (single sign-on; set `OIDC_ALLOW_SIGNUP=false` to stop strangers at your provider getting accounts), `MCP_ENABLED=true` (built-in MCP server at `/mcp/`), `WEB_CONCURRENCY`, `WEB_THREADS`. For a custom domain, add `https://YOUR-DOMAIN` to `URL` and `YOUR-DOMAIN` to `DJANGO_ALLOWED_HOSTS` (space-separated).

## After deploying

1. Wait for the `WYGIWYH` service to turn green (first build about 1–2 minutes).
2. Open its Variables, copy `ADMIN_EMAIL` and `ADMIN_PASSWORD`, and sign in at its domain.
3. Change your email and password under your profile. Add other people under Users.

## Updates

The `WYGIWYH` service builds from this repo's `main` branch. When a new WYGIWYH release is pinned here, Railway shows deployers an "update available" notice. Read [CHANGELOG.md](CHANGELOG.md) first (breaking changes are listed first), then apply it; migrations run on the next start. Back up the Postgres volume before major upgrades.

## Local test kit

`test/compose.yml` runs the same image with Postgres 17 and RustFS as a stand-in S3 bucket, limited to 512 MB / 1 CPU. `test/smoke.py` signs in, creates a currency, an account, a transaction and an attachment, and checks them again after a restart.
