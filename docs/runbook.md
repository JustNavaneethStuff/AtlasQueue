# Runbook

## Dead letter queue drain

1. Open dashboard → Dead Letter tab, or `GET /v1/tasks?status=dead_letter`
2. Inspect `error` field per task
3. Fix root cause, then `POST /v1/tasks/{id}/retry`

## Scheduler leader failover

If scheduler container dies, standby acquires `lock:scheduler` within `SCHEDULER_LOCK_TTL` seconds (default 30).

Verify: scheduled tasks resume moving to ready queues.

## Enqueue failures

Tasks in `enqueue_failed` status are retried by the scheduler reconciler. Check Redis connectivity.

## Stale workers

Workers not heartbeating are marked `offline` in Postgres after 60s. Redis heartbeat keys expire after `3 × WORKER_HEARTBEAT_INTERVAL`.
