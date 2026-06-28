# Atlas Queue Interview Notes

## Postgres as source of truth

**Why:** Durable task state, audit history, idempotency constraints, and operational queries belong in a relational store.

**Alternatives:** Redis-only queues (fast but weak durability), Kafka (great streaming but heavier ops).

**Tradeoffs:** Dual-write complexity vs simpler single-store designs.

**Failure scenarios:** Redis enqueue succeeds but Postgres fails (or vice versa) — reconcilers and enqueue-failed status recover drift.

## Redis for delivery

**Why:** Low-latency dequeue, priority lists, scheduled ZSET, inflight TTL, and worker heartbeats.

**Alternatives:** Postgres `SKIP LOCKED` polling, SQS, RabbitMQ.

**Scalability:** Horizontal workers with `BRPOP`; scheduler leader election avoids duplicate releases.

## At-least-once execution

**Why:** Crash after dequeue requires retry/reconcile; idempotency keys protect submit side.

**Interview answer:** "We optimize for at-least-once with explicit idempotency and DLQ replay rather than pretending exactly-once without distributed transactions."

## Retry and DLQ model

**Why:** Central `TaskFailureHandler` keeps worker and timeout reconciler behavior consistent.

**Tradeoffs:** Manual replay resets attempts for operator-driven recovery.

## Auth model

**Why:** JWT + RBAC for humans/dashboards; API key retained for automation and backward compatibility.

**Roles:** `admin`, `user`, `worker` with route-level authorization.

## Observability

**Why:** Structured JSON logs with request IDs, Prometheus RED metrics, optional OpenTelemetry tracing, Grafana dashboards.

**Failure scenarios:** DLQ growth, scheduler leader loss, Redis/Postgres readiness failures surfaced via `/v1/ready`.

## Compared to Celery/Sidekiq

| Dimension | Atlas Queue | Celery/Sidekiq |
|-----------|-------------|----------------|
| State store | Postgres SoT + Redis delivery | Broker-centric |
| Audit trail | First-class `task_events` | Usually external |
| Ops complexity | Self-hosted components | Mature ecosystem |
| Learning value | Shows distributed design choices | Production default |
