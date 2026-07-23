"""Legal source application service (M7-A).

Orchestrates legal source operations: sync, search, resolve citations.
Delegates to repository, client, adapter, and resolver.
"""

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from private_legal_navigator.application.citation_resolver import (
    CitationResolver,
    ResolvedCitation,
)
from private_legal_navigator.application.legal_source_status_dto import LegalSourceStatusDTO
from private_legal_navigator.domain.legal_source import (
    ImportStatus,
    LegalSource,
)
from private_legal_navigator.infrastructure.gii_adapter import (
    GiiAdapter,
    GiiCatalogItem,
    GiiParsedInstrument,
    make_gii_source,
)
from private_legal_navigator.infrastructure.safe_logging import safe_log_event
from private_legal_navigator.infrastructure.safe_source_client import SourceClient
from private_legal_navigator.infrastructure.sqlite_legal_source_repository import (
    SqliteLegalSourceRepository,
)

logger = logging.getLogger("private_legal_navigator.legal_source_service")


class LegalSourceService:
    """Application service for legal source operations."""

    def __init__(
        self,
        repo: SqliteLegalSourceRepository,
        client: SourceClient,
        snapshot_dir: Path,
    ) -> None:
        self._repo = repo
        self._client = client
        self._snapshot_dir = snapshot_dir
        self._gii = GiiAdapter(client, snapshot_dir)
        self._resolver = CitationResolver(repo)

    # ── Source Registry ──────────────────────────

    def register_default_sources(self) -> None:
        """Register built-in sources (GII) if not already present."""
        gii_source = make_gii_source()
        existing = self._repo.get_source_by_key(gii_source.source_key)
        if existing is None:
            self._repo.save_source(gii_source)
            safe_log_event(
                logger, "legal_source.registered_default", display_name=gii_source.display_name
            )

    def list_sources(self) -> list[LegalSource]:
        """List all registered legal sources."""
        return self._repo.list_sources()

    def get_source_status(self) -> list[dict[str, Any]]:
        """Get real status overview of all sources with actual statistics."""
        sources = self._repo.list_sources(enabled_only=False)
        status_list = []
        for source in sources:
            # Get snapshots for this source
            snapshots = self._repo.list_snapshots_for_source(source.source_key)
            indexed = sum(1 for s in snapshots if s.import_status.value == "INDEXED")
            failed = sum(1 for s in snapshots if s.import_status.value == "FAILED")

            # Get instrument and provision counts
            instrument_count = self._repo.count_instruments(source.source_key)
            provision_count = self._repo.count_provisions(source.source_key)

            # Determine last retrieval times
            last_retrieved = ""
            last_imported = ""
            if snapshots:
                last_retrieved = max(s.retrieved_at for s in snapshots).isoformat()
                indexed_snaps = [s for s in snapshots if s.import_status.value == "INDEXED"]
                if indexed_snaps:
                    last_imported = max(s.retrieved_at for s in indexed_snaps).isoformat()

            # Integrity status: NOT_VERIFIED until explicitly verified
            integrity_status = "NOT_VERIFIED"

            dto = LegalSourceStatusDTO(
                source_key=source.source_key,
                display_name=source.display_name,
                authority_tier=source.authority_tier.value,
                jurisdiction=source.jurisdiction,
                enabled=source.enabled,
                base_url=source.base_url,
                description=source.description,
                snapshot_count=len(snapshots),
                indexed_snapshot_count=indexed,
                failed_snapshot_count=failed,
                instrument_count=instrument_count,
                provision_count=provision_count,
                last_retrieved_at=last_retrieved,
                last_successful_import_at=last_imported,
                integrity_status=integrity_status,
                integrity_checked_at="",
                integrity_failure_count=0,
                status_warnings=[],
            )

            if source.enabled and len(snapshots) == 0:
                dto.status_warnings.append("Quelle ist aktiviert, aber keine Snapshots vorhanden.")

            status_list.append(dto.to_dict())
        return status_list

    # ── GII Sync ─────────────────────────────────

    def fetch_gii_catalog(self) -> list[GiiCatalogItem]:
        """Fetch the GII catalog of available laws."""
        return self._gii.fetch_catalog()

    def sync_gii_instrument(self, key: str) -> GiiParsedInstrument | None:
        """Sync a single GII instrument by its key/abbreviation.

        Steps:
        1. Register GII source if needed
        2. Find instrument in catalog
        3. Download and snapshot
        4. Check for duplicate hash (skip if unchanged)
        5. Parse and persist atomically (SEC-015)
        """
        self.register_default_sources()

        # Find in catalog
        item = self._gii.find_in_catalog(key)
        if item is None:
            safe_log_event(logger, "legal_source.instrument_not_found", instrument_key=key)
            return None

        # Sync
        parsed = self._gii.sync_instrument(item)

        # Check for existing snapshot with same hash
        existing = self._repo.get_snapshot_by_hash(parsed.snapshot.sha256)
        if existing is not None:
            safe_log_event(
                logger,
                "legal_source.snapshot_duplicate",
                abbreviation=item.abbreviation,
                sha256_prefix=parsed.snapshot.sha256[:16],
            )
            parsed.snapshot.import_status = ImportStatus.DUPLICATE
            return parsed

        # Check for existing instrument and update/insert
        existing_inst = self._repo.get_instrument_by_abbreviation(parsed.instrument.abbreviation)
        if existing_inst is not None:
            assert existing_inst.instrument_id is not None
            parsed.instrument.instrument_id = existing_inst.instrument_id
            parsed.expression.instrument_id = existing_inst.instrument_id

        # SEC-015: Atomic batch import — all or nothing
        try:
            self._repo.save_instrument_batch(
                snapshot=parsed.snapshot,
                instrument=parsed.instrument,
                expression=parsed.expression,
                provisions=parsed.provisions,
            )

            # Mark import as successful
            self._repo.update_snapshot_status(
                parsed.snapshot.snapshot_id,  # type: ignore[arg-type]
                ImportStatus.INDEXED,
            )
            parsed.snapshot.import_status = ImportStatus.INDEXED

        except Exception as exc:
            # SEC-015-B: Snapshot remains with FAILED status
            self._repo.update_snapshot_status(
                parsed.snapshot.snapshot_id,  # type: ignore[arg-type]
                ImportStatus.FAILED,
                error=str(exc)[:500],
            )
            parsed.snapshot.import_status = ImportStatus.FAILED
            parsed.snapshot.error_summary = str(exc)[:500]
            raise

        safe_log_event(
            logger,
            "legal_source.instrument_synced",
            abbreviation=parsed.instrument.abbreviation,
            provision_count=len(parsed.provisions),
        )

        return parsed

    # ── Search ───────────────────────────────────

    def search(self, query: str, limit: int = 50) -> list[dict[str, Any]]:
        """Search the legal corpus using FTS5 full-text search."""
        return self._repo.search_provisions_fts(query, limit=limit)

    def resolve_citation(self, citation_text: str) -> ResolvedCitation:
        """Resolve a legal citation to a specific provision."""
        return self._resolver.resolve(citation_text)

    # ── Integrity ────────────────────────────────

    def verify_snapshot(self, snapshot_id: UUID) -> bool:
        """Verify a snapshot's integrity by comparing stored hash with computed hash."""
        snapshot = self._repo.get_snapshot(snapshot_id)
        if snapshot is None:
            return False
        try:
            content = Path(snapshot.storage_path).read_bytes()
            from private_legal_navigator.infrastructure.safe_source_client import compute_sha256

            actual_hash = compute_sha256(content)
            return actual_hash == snapshot.sha256
        except (OSError, ValueError):
            return False

    def verify_all_snapshots(self) -> list[dict[str, Any]]:
        """Verify all snapshots and return detailed results."""
        results = []
        sources = self._repo.list_sources(enabled_only=False)
        for source in sources:
            snapshots = self._repo.list_snapshots_for_source(source.source_key)
            for snap in snapshots:
                if snap.snapshot_id is not None:
                    result = self._verify_snapshot_detailed(snap.snapshot_id)
                    results.append(result)
        return results

    def _verify_snapshot_detailed(self, snapshot_id: uuid.UUID) -> dict[str, Any]:
        """Verify a snapshot and return detailed result dict."""
        snapshot = self._repo.get_snapshot(snapshot_id)
        if snapshot is None:
            return {
                "snapshot_id": str(snapshot_id),
                "status": "MISSING",
                "error_code": "SNAPSHOT_NOT_FOUND",
                "checked_at": datetime.now().isoformat(),
            }

        result = {
            "snapshot_id": str(snapshot.snapshot_id),
            "source_key": "",
            "expected_sha256": snapshot.sha256,
            "actual_sha256": "",
            "database_path": snapshot.storage_path,
            "file_exists": False,
            "size_matches": False,
            "hash_matches": False,
            "status": "NOT_VERIFIED",
            "error_code": "",
            "checked_at": datetime.now().isoformat(),
        }

        # Get source key for context
        source = self._repo.get_source(snapshot.source_id)
        if source:
            result["source_key"] = source.source_key

        try:
            path = Path(snapshot.storage_path)
            if not path.exists():
                result["status"] = "MISSING"
                result["error_code"] = "FILE_NOT_FOUND"
                return result

            result["file_exists"] = True
            content = path.read_bytes()

            # Size check
            result["size_matches"] = len(content) == snapshot.byte_size

            # Hash check
            from private_legal_navigator.infrastructure.safe_source_client import compute_sha256

            actual = compute_sha256(content)
            result["actual_sha256"] = actual
            result["hash_matches"] = actual == snapshot.sha256

            if result["hash_matches"] and result["size_matches"]:
                result["status"] = "VERIFIED"
            elif not result["hash_matches"]:
                result["status"] = "FAILED"
                result["error_code"] = "HASH_MISMATCH"
            elif not result["size_matches"]:
                result["status"] = "FAILED"
                result["error_code"] = "SIZE_MISMATCH"
        except (OSError, ValueError) as e:
            result["status"] = "FAILED"
            result["error_code"] = f"READ_ERROR: {type(e).__name__}"

        return result

    def verify_snapshot_detailed(self, snapshot_id: uuid.UUID) -> dict[str, Any]:
        """Public method — verify a single snapshot with detailed output."""
        return self._verify_snapshot_detailed(snapshot_id)
