# API Documentation

Base URL: `/v1`

## Authentication

Use either:

- `X-API-Key: <API_KEY>` (automation, admin-equivalent)
- `Authorization: Bearer <JWT>` from `POST /v1/auth/login`

## Core endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | none | Liveness |
| GET | `/ready` | none | Readiness (Postgres + Redis) |
| GET | `/metrics` | optional | Prometheus metrics |
| POST | `/auth/login` | none | Obtain JWT |
| POST | `/tasks` | admin,user | Submit task |
| GET | `/tasks` | any | List with pagination/filter/sort |
| GET | `/tasks/{id}` | any | Get task |
| POST | `/tasks/{id}/cancel` | admin,user | Cancel task |
| POST | `/tasks/{id}/retry` | admin | Replay DLQ task |
| GET | `/tasks/{id}/events` | any | Audit events |
| GET | `/workers` | any | List workers |
| POST | `/workers/register` | admin,worker | Register worker |
| GET | `/admin/stats` | admin | Queue stats |

## Error envelope

```json
{
  "detail": "Task not found",
  "code": "task_not_found",
  "request_id": "..."
}
```

OpenAPI schema: `/openapi.json` or `/docs`.
