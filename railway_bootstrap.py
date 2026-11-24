"""First-boot and every-boot setup for WYGIWYH on Railway.

Runs before the public port opens:
  1. waits for PostgreSQL (Railway's private DNS can lag for a minute),
  2. takes a Postgres advisory lock so two overlapping deploys never migrate
     at the same time (polls pg_try_advisory_lock instead of blocking),
  3. runs the migrations quietly,
  4. creates the admin from ADMIN_EMAIL / ADMIN_PASSWORD when no active
     admin exists yet (first boot), and exits non-zero if it can't.

Local sign-up is off in WYGIWYH (accounts are made by an admin), so the admin
created here is the only way in until you add users.
"""

import os
import sys
import time

import django
import psycopg

LOCK_ID = 7_312_125_001
APP_DIR = "/usr/src/app"
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)


def log(msg):
    print(f"[railway-bootstrap] {msg}", flush=True)


def connect(deadline):
    params = dict(
        host=os.environ.get("SQL_HOST", ""),
        port=os.environ.get("SQL_PORT", "5432"),
        user=os.environ.get("SQL_USER", ""),
        password=os.environ.get("SQL_PASSWORD", ""),
        dbname=os.environ.get("SQL_DATABASE", ""),
        connect_timeout=5,
        autocommit=True,
    )
    last = None
    while time.time() < deadline:
        try:
            return psycopg.connect(**params)
        except Exception as exc:  # DNS not ready, DB still starting...
            last = exc
            log(f"waiting for PostgreSQL at {params['host']}: {str(exc).strip()[:120]}")
            time.sleep(3)
    log(f"PostgreSQL did not answer in time: {last}")
    sys.exit(1)


def main():
    deadline = time.time() + int(os.environ.get("RAILWAY_DB_WAIT_SECONDS", "240"))
    lock_conn = connect(deadline)
    while True:
        got = lock_conn.execute("SELECT pg_try_advisory_lock(%s)", (LOCK_ID,)).fetchone()[0]
        if got:
            break
        if time.time() > deadline:
            log("another deploy still holds the migration lock; giving up")
            sys.exit(1)
        log("another deploy is migrating; waiting")
        time.sleep(2)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "WYGIWYH.settings")
    django.setup()
    from django.contrib.auth import get_user_model
    from django.core.management import call_command

    log("applying database migrations")
    call_command("migrate", interactive=False, verbosity=0)
    log("migrations done")

    User = get_user_model()
    email = os.environ.get("ADMIN_EMAIL", "").strip()
    password = os.environ.get("ADMIN_PASSWORD", "")
    admins = User.objects.filter(is_superuser=True, is_active=True)
    if admins.exists():
        # Created on an earlier start (or by hand). The variables are only
        # used once, so changing the admin's email or password in WYGIWYH
        # sticks across restarts.
        log(f"{admins.count()} active admin account(s) already exist; not touching them")
    elif email and password:
        from django.core.exceptions import ValidationError
        from django.core.validators import validate_email

        try:
            validate_email(email)
        except ValidationError:
            log(f"ADMIN_EMAIL '{email}' is not a valid email address (WYGIWYH signs in by email); fix it and redeploy")
            sys.exit(1)
        if User.objects.filter(email__iexact=email).exists():
            log(f"a user {email} exists but is not an active admin; refusing to change it")
            sys.exit(1)
        User.objects.create_superuser(email=email, password=password)
        log(f"created admin {email} (password from ADMIN_PASSWORD)")
    else:
        log("no active admin account exists and ADMIN_EMAIL/ADMIN_PASSWORD are not both set; refusing to start")
        sys.exit(1)

    try:
        call_command("setup_oauth", verbosity=0)
    except Exception as exc:
        log(f"setup_oauth failed: {exc}")
        sys.exit(1)

    lock_conn.execute("SELECT pg_advisory_unlock(%s)", (LOCK_ID,))
    lock_conn.close()
    log("ready")


if __name__ == "__main__":
    main()
