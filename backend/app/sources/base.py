from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.core.domain import SourceHealth


@dataclass
class SourceEvidence:
    field: str
    value: str
    method: str
    source_url: str | None = None
    confidence: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CollectionResult:
    health: SourceHealth
    evidence: list[SourceEvidence] = field(default_factory=list)
    snapshot_hash: str | None = None
    snapshot_metadata: dict[str, Any] = field(default_factory=dict)
    error_code: str | None = None


class EvidenceSourceAdapter(ABC):
    source_id: str
    display_name: str
    source_type: str
    official: bool = False
    automation_mode: str = "AUTOMATED"
    limitations: str = ""
    supported_fields: tuple[str, ...] = ()

    @abstractmethod
    async def health_check(self) -> SourceHealth:
        raise NotImplementedError

    @abstractmethod
    async def collect(self, claims: dict[str, str]) -> CollectionResult:
        raise NotImplementedError

    def metadata(self, health: SourceHealth) -> dict[str, Any]:
        return {
            "id": self.source_id,
            "name": self.display_name,
            "type": self.source_type,
            "official": self.official,
            "automation_mode": self.automation_mode,
            "health": health.value,
            "limitations": self.limitations,
            "supported_fields": list(self.supported_fields),
        }
