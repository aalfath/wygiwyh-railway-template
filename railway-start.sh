#!/bin/bash
# Start WYGIWYH on Railway: settings from Railway's variables, a quiet
# migrate + admin bootstrap before the port opens, then gunicorn and the
# procrastinate worker. If either process stops, the container exits
# non-zero so Railway's ON_FAILURE policy restarts it.
set -euo pipefail
cd /usr/src/app

die() { echo "[railway-start] $*" >&2; exit 1; }

# ---- resources: size workers from the container's limits, not the host ----
cpus=1
if [ -r /sys/fs/cgroup/cpu.max ]; then
  read -r quota period < /sys/fs/cgroup/cpu.max || true
  if [ "${quota:-max}" != "max" ] && [ "${period:-0}" -gt 0 ]; then
    cpus=$(( (quota + period - 1) / period ))
  fi
fi
[ "$cpus" -ge 1 ] || cpus=1
[ "$cpus" -le 8 ] || cpus=8
mem_mb=0
if [ -r /sys/fs/cgroup/memory.max ]; then
  m=$(cat /sys/fs/cgroup/memory.max)
  [ "$m" != "max" ] && mem_mb=$(( m / 1048576 ))
fi
# Railway shows every host CPU inside the container; keep numeric libraries
# (pandas/numpy via yfinance) and malloc from spawning one thread per host CPU.
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}" OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}" \
       MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}" NUMEXPR_MAX_THREADS="${NUMEXPR_MAX_THREADS:-1}" \
       MALLOC_ARENA_MAX="${MALLOC_ARENA_MAX:-2}"
# One gunicorn worker is ~140 MB; add a second only with room to spare.
if [ -z "${WEB_CONCURRENCY:-}" ]; then
  if [ "$mem_mb" -ge 1500 ] && [ "$cpus" -ge 2 ]; then WEB_CONCURRENCY=2; else WEB_CONCURRENCY=1; fi
fi
export WEB_CONCURRENCY WEB_THREADS="${WEB_THREADS:-4}" PROCRASTINATE_WORKER_CONCURRENCY="${PROCRASTINATE_WORKER_CONCURRENCY:-1}"
echo "[railway-start] cpus=$cpus mem_limit_mb=${mem_mb:-unknown} web_workers=$WEB_CONCURRENCY threads=$WEB_THREADS"

# ---- settings ----
[ -n "${SECRET_KEY:-}" ] || die "SECRET_KEY is empty; set it (the template generates one)"
[ -n "${SQL_HOST:-}" ] && [ -n "${SQL_DATABASE:-}" ] || die "SQL_HOST/SQL_DATABASE are empty; link the Postgres service"
export DEBUG="${DEBUG:-false}" HTTPS_ENABLED="${HTTPS_ENABLED:-true}" TZ="${TZ:-UTC}" PORT="${PORT:-8000}"
export FORWARDED_ALLOW_IPS="${FORWARDED_ALLOW_IPS:-*}"

# Host names and CSRF origins: Railway's domain, its health-check host and
# anything you add in DJANGO_ALLOWED_HOSTS / URL (space-separated).
domain="${RAILWAY_PUBLIC_DOMAIN:-}"
case "$domain" in *.*) ;; *) domain="" ;; esac
hosts="healthcheck.railway.app localhost 127.0.0.1 ${DJANGO_ALLOWED_HOSTS:-}"
urls=""
[ -n "$domain" ] && hosts="$domain $hosts" && urls="https://$domain"
for u in ${URL:-}; do
  case "$u" in http://?*.*|https://?*.*|http://localhost*|https://localhost*) urls="$urls $u" ;; *) echo "[railway-start] ignoring invalid URL entry '$u'" ;; esac
done
[ -n "$urls" ] || urls="http://localhost"
export DJANGO_ALLOWED_HOSTS="$(echo $hosts | tr ' ' '\n' | awk 'NF && !seen[$0]++' | tr '\n' ' ' | sed 's/ $//')"
export URL="$(echo $urls | sed 's/^ //')"
echo "[railway-start] allowed hosts: $DJANGO_ALLOWED_HOSTS"
echo "[railway-start] public URL(s): $URL"
if [ -n "${AWS_STORAGE_BUCKET_NAME:-}" ]; then
  echo "[railway-start] attachments: bucket ${AWS_STORAGE_BUCKET_NAME}"
else
  echo "[railway-start] attachments: local folder (no bucket configured; files are lost on redeploy unless a volume is mounted at /usr/src/app/attachments)"
fi

# ---- migrate + admin, before the port opens ----
python /railway_bootstrap.py || die "bootstrap failed"

# Check for a newer WYGIWYH release now instead of waiting a day; never block on it.
python manage.py procrastinate defer check_for_updates >/dev/null 2>&1 || true

# ---- run ----
pids=()
stop() { kill -TERM "${pids[@]}" 2>/dev/null || true; wait || true; exit 0; }
trap stop TERM INT

python manage.py procrastinate worker &
pids+=($!)
gunicorn WYGIWYH.wsgi:application --bind "0.0.0.0:${PORT}" --timeout 600 \
  --workers "$WEB_CONCURRENCY" --threads "$WEB_THREADS" --no-control-socket --access-logfile - &
pids+=($!)

# Exit non-zero as soon as either process stops, so Railway restarts us.
set +e
wait -n "${pids[@]}"
code=$?
echo "[railway-start] a process exited (code $code); stopping the container" >&2
kill -TERM "${pids[@]}" 2>/dev/null
sleep 2
exit 1
