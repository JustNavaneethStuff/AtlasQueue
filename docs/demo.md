# Demo script

Use this script for portfolio videos, interviews, or README GIFs.

## Setup (30 seconds)

```bash
docker compose up --build
```

Wait until:
- http://localhost:8000/v1/health returns `{"status":"ok"}`
- http://localhost:5173 loads the dashboard

## Narration outline

1. **Problem** — "Most task queues hide state in the broker. Atlas Queue makes Postgres the source of truth."
2. **Submit** — POST an `echo` task and a `fail_always` task.
3. **Dashboard** — Show task list, event timeline, DLQ replay.
4. **Scale** — `docker compose up --scale worker=3` (optional).
5. **Metrics** — Show Prometheus or `/v1/metrics`.

## Commands

```bash
# Success path
curl -X POST http://localhost:8000/v1/tasks \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-api-key" \
  -d '{"name":"echo","payload":{"message":"portfolio-demo"},"priority":0}'

# Failure → DLQ path
curl -X POST http://localhost:8000/v1/tasks \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-api-key" \
  -d '{"name":"fail_always","payload":{},"max_retries":2}'

# Admin stats
curl -H "X-API-Key: dev-api-key" http://localhost:8000/v1/admin/stats
```

## Recording tips

- 1920×1080, 60–90 seconds
- Show: terminal submit → dashboard refresh → task detail events → DLQ replay
- Optional: split screen with architecture diagram from README
