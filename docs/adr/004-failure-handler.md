# ADR 004: Centralized Task Failure Handling

## Status

Accepted

## Context

Retry, timeout requeue, and DLQ transitions were duplicated in worker executor and inflight reconciler, risking behavioral drift.

## Decision

Introduce `TaskFailureHandler` in the application layer as the single place for failure-side effects.

## Alternatives

- Keep duplication — faster short term, bug prone
- Domain entity methods — mixes infrastructure side effects into entity

## Tradeoffs

- Slightly more indirection
- Easier to test and reason about in interviews

## Failure scenarios

- Handler throws mid-transition — task may remain RUNNING until reconciler runs again
- Manual DLQ replay resets attempts to give operators a clean retry budget
