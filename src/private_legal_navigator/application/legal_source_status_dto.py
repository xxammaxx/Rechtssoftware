"""Data Transfer Object for legal source status display (M7-A.1)."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LegalSourceStatusDTO:
    """Rich status model for a legal source — real data, no placeholders."""

    source_key: str
    display_name: str
    authority_tier: str
    jurisdiction: str
    enabled: bool
    base_url: str
    description: str
    snapshot_count: int
    indexed_snapshot_count: int
    failed_snapshot_count: int
    instrument_count: int
    provision_count: int
    last_retrieved_at: str
    last_successful_import_at: str
    integrity_status: str  # NOT_VERIFIED, VERIFIED, FAILED, MISSING
    integrity_checked_at: str
    integrity_failure_count: int
    status_warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_key": self.source_key,
            "display_name": self.display_name,
            "authority_tier": self.authority_tier,
            "jurisdiction": self.jurisdiction,
            "enabled": self.enabled,
            "base_url": self.base_url,
            "description": self.description,
            "snapshot_count": self.snapshot_count,
            "indexed_snapshot_count": self.indexed_snapshot_count,
            "failed_snapshot_count": self.failed_snapshot_count,
            "instrument_count": self.instrument_count,
            "provision_count": self.provision_count,
            "last_retrieved_at": self.last_retrieved_at,
            "last_successful_import_at": self.last_successful_import_at,
            "integrity_status": self.integrity_status,
            "integrity_checked_at": self.integrity_checked_at,
            "integrity_failure_count": self.integrity_failure_count,
            "status_warnings": self.status_warnings,
        }
