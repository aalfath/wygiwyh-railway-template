# Deploy and Host WYGIWYH on Railway

WYGIWYH ("What You Get Is What You Have") is an open-source, self-hosted finance tracker built on one rule: spend what you earn this month and treat savings as untouchable. It tracks income and expenses across many accounts and currencies, with monthly and yearly views, net worth, rules, recurring entries, bill splitting, a DCA tracker and a REST API.

## About Hosting WYGIWYH

WYGIWYH is a Django app backed by PostgreSQL, with a procrastinate background worker for recurring transactions, exchange rates and clean-up. This template runs the official `eitchtee/wygiwyh:0.28.0` image (pinned by digest) as one public `WYGIWYH` service, built from a public GitHub repo, next to Railway's PostgreSQL and a private Railway Bucket for attachments. On every start it waits for the database, applies migrations under a lock, and creates your admin account once from generated credentials. Local sign-up is off in WYGIWYH, so nobody else can register. The service fits Railway's Free plan (about 290 MB of 512 MB RAM, one volume).

## Common Use Cases

* Track income, expenses and balances across bank accounts, cards, wallets and investments in one place
* Manage money in several currencies, including custom ones for crypto or reward points, with automatic exchange rates
* Follow monthly and yearly totals and net worth, and split shared bills with other people
* Automate entries from other tools through the REST API, rules or the built-in MCP server

## Dependencies for WYGIWYH Hosting

* PostgreSQL (Railway's PostgreSQL service, on its own volume)
* A Railway Bucket for transaction and split attachments (private, S3-compatible)

### Deployment Dependencies

* WYGIWYH (AGPL-3.0): https://github.com/eitchtee/WYGIWYH
* Template source, Dockerfile and changelog: https://github.com/aalfath/wygiwyh-railway-template

### Implementation Details

**Services:** `WYGIWYH` (web app on port 8080 plus the background worker, health check `/login/`), `Postgres` (database, volume) and `Bucket` (attachments). Everything talks over Railway's private network through reference variables.

**First sign-in:** when the deploy is green, open the `WYGIWYH` service's Variables, copy `ADMIN_EMAIL` (default `admin@example.com`) and `ADMIN_PASSWORD` (generated), and sign in at the service's domain. Then set your own email and password under your profile. The variables are only used to create the admin the first time; to add people, go to Users in the admin menu.

**Optional settings** on `WYGIWYH`: `TZ` (time zone for background jobs, default UTC); `ENABLE_SOFT_DELETE` and `KEEP_DELETED_ENTRIES_FOR`; `OIDC_CLIENT_NAME`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET` and `OIDC_SERVER_URL` for single sign-on (set `OIDC_ALLOW_SIGNUP=false` unless everyone at your provider should get an account); `MCP_ENABLED=true` for the built-in MCP server at `/mcp/`. With a custom domain, add `https://YOUR-DOMAIN` to `URL` and `YOUR-DOMAIN` to `DJANGO_ALLOWED_HOSTS`.

**Resources:** one gunicorn worker with 4 threads and one task worker. On plans with 1.5 GB or more and 2 vCPUs a second web worker starts on its own; set `WEB_CONCURRENCY` to override. If the web process or the worker stops, the container exits with an error so Railway restarts it.

**Updates:** the service builds from the template's GitHub repo. When a new WYGIWYH release is pinned there, Railway shows an update notice in your project; read the repo's `CHANGELOG.md`, then apply it. Migrations run on the next start.

## Why Deploy WYGIWYH on Railway?

<!-- Recommended: Keep this section as shown below -->
Railway is a singular platform to deploy your infrastructure stack. Railway will host your infrastructure so you don't have to deal with configuration, while allowing you to vertically and horizontally scale it.

By deploying WYGIWYH on Railway, you are one step closer to supporting a complete full-stack application with minimal burden. Host your servers, databases, AI agents, and more on Railway.
<!-- End recommended section -->
