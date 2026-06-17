from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from atlasqueue.domain.value_objects.enums import WorkerStatus


@dataclass
class Worker:
    id: UUID
    hostname: str
    status: WorkerStatus = WorkerStatus.ACTIVE
    registered_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_seen_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, str] = field(default_factory=dict)

    @classmethod
    def create(cls, hostname: str, metadata: dict[str, str] | None = None) -> Worker:
        now = datetime.now(UTC)
        return cls(
            id=uuid4(),
            hostname=hostname,
            status=WorkerStatus.ACTIVE,
            registered_at=now,
            last_seen_at=now,
            metadata=metadata or {},
        )

    def heartbeat(self) -> None:
        self.last_seen_at = datetime.now(UTC)
        self.status = WorkerStatus.ACTIVE
