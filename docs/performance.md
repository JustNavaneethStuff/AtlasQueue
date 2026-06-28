# Performance Notes

## Benchmark harness

Run the lightweight API benchmark:

```bash
pip install -e ".[dev]"
python benchmarks/api_submit_benchmark.py
```

## Improvements implemented

1. **Redis `KEYS` replaced with `SCAN`** for inflight and worker enumeration to avoid blocking Redis at scale.
2. **Atomic scheduled claim** via Lua script (`claim_due_scheduled`) to prevent duplicate scheduler releases.
3. **Shared failure handler** removes duplicated retry/DLQ logic between worker and reconciler paths.
4. **HTTP Prometheus middleware** tracks RED metrics for API endpoints.
5. **Repository pagination count** uses `COUNT(*)` instead of page length.

## Expected bottlenecks

- Dual-write enqueue path (Postgres + Redis) under very high submit rates.
- Priority `BRPOP` fairness without aging for low-priority tasks.
- Worker claim is not atomic; inflight reconciler compensates after crashes.

## Tuning knobs

- `WORKER_CONCURRENCY`
- `SCHEDULER_BATCH_SIZE`
- SQLAlchemy pool size in `infrastructure/persistence/database.py`
- Redis connection timeouts in `create_redis_client`
