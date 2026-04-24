#!/bin/sh
set -eu

if [ "${WAIT_FOR_QDRANT:-true}" = "true" ]; then
  python - <<'PY'
import os
import sys
import time
import urllib.error
import urllib.request

base_url = os.getenv("QDRANT_URL", "").rstrip("/")
if not base_url:
    print("QDRANT_URL is not configured.", file=sys.stderr)
    sys.exit(1)

timeout_seconds = float(os.getenv("QDRANT_STARTUP_TIMEOUT_SECONDS", "60"))
deadline = time.time() + timeout_seconds
headers = {}
api_key = os.getenv("QDRANT_API_KEY")
if api_key:
    headers["api-key"] = api_key

health_url = f"{base_url}/collections"
last_error = None

while time.time() < deadline:
    request = urllib.request.Request(health_url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=5):
            print(f"Qdrant is reachable at {base_url}", flush=True)
            break
    except Exception as exc:  # noqa: BLE001
        last_error = exc
        time.sleep(2)
else:
    print(f"Timed out waiting for Qdrant at {base_url}: {last_error}", file=sys.stderr)
    sys.exit(1)
PY
fi

if [ "${APP_RELOAD:-false}" = "true" ]; then
  exec python -m uvicorn app.main:app \
    --host "${APP_HOST:-0.0.0.0}" \
    --port "${APP_PORT:-8000}" \
    --reload \
    --reload-dir /app/app
fi

exec python -m uvicorn app.main:app --host "${APP_HOST:-0.0.0.0}" --port "${APP_PORT:-8000}"
