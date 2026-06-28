# Database Schema

## `tasks`

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | Task identifier |
| name | varchar(255) | Handler/webhook name |
| executor_type | varchar(32) | `python` or `webhook` |
| payload | jsonb | Task input |
| status | varchar(32) | Lifecycle state |
| priority | int | Lower = higher priority |
| scheduled_at | timestamptz | Optional delayed run |
| attempts | int | Failure count |
| max_retries | int | Retry budget |
| timeout_seconds | int | Execution timeout |
| backoff_policy | jsonb | Retry delay policy |
| worker_id | varchar(128) | Last worker |
| result | jsonb | Success output |
| error | text | Last error |
| idempotency_key | varchar(255) unique partial | Submit dedup |
| created_at/updated_at/started_at/finished_at | timestamptz | Timestamps |

Indexes: `status`, unique partial `idempotency_key`.

## `task_events`

Append-only audit log keyed by `task_id` with `event_type`, status transitions, message, metadata.

## `workers`

Registered workers with hostname, status, heartbeat timestamps, metadata.

## `users`

JWT auth users with `username`, `password_hash`, `role`.
