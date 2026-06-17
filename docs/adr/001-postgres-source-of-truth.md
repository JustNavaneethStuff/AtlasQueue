# ADR 001: PostgreSQL as Source of Truth

## Status

Accepted

## Context

Task queues typically store message state in the broker (Redis/RabbitMQ). Clients often cannot query reliable task history without extra infrastructure.

## Decision

PostgreSQL holds authoritative task state. Redis is a delivery mechanism only. All status reads go to Postgres.

## Consequences

- Strong auditability via `task_events` table
- Dual-write complexity between Postgres and Redis
- Reconciler required for `enqueue_failed` and inflight orphans
