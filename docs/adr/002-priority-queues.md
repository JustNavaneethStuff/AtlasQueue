# ADR 002: Priority via Multiple Redis Lists

## Status

Accepted

## Context

Priority queues can be implemented with single ZSET (score = priority + timestamp) or multiple LISTs.

## Decision

Use bounded priority levels (default 4) with one LIST per level. Workers `BRPOP` from highest priority first.

## Consequences

- Simple, fast dequeue
- Possible starvation of low-priority tasks under sustained high-priority load
- Future: priority aging
