# Phase 2 Review

## Delivered

- Horizontal worker scaling via Compose replicas
- Task cancellation, timeout, exponential backoff
- Worker heartbeats + stale detection
- Leader election with lock renewal
- Inflight reconciler for orphaned running tasks
- Prometheus metrics + OpenTelemetry hooks
- API key authentication

## Tradeoffs revisited

- Python timeout via `asyncio.wait_for` does not kill CPU-bound threads
- Webhook cancel is best-effort

## Improvements

- Fencing token for scheduler leader
- Rate limiting middleware
- Grafana dashboard JSON in deploy/
