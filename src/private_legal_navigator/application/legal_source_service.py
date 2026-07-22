"""Legal source application service (M7-A).

Orchestrates legal source operations: sync, search, resolve citations.
Delegates to repository, client, adapter, and resolver.
"""

import logging
from pathlib import Path
from uuid import UUID

from private_legal_navigator.application.citation_resolver import (
    CitationResolver,
    ResolvedCitation,
)
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
            logger.info("Registered default source: %s", gii_source.display_name)

    def list_sources(self) -> list[LegalSource]:
        """List all registered legal sources."""
        return self._repo.list_sources()

    def get_source_status(self) -> list[dict]:
        """Get status overview of all sources with sync info."""
        sources = self._repo.list_sources()
        status_list = []
        for source in sources:
            status_list.append(
                {
                    "source_key": source.source_key,
                    "display_name": source.display_name,
                    "authority_tier": source.authority_tier.value,
                    "enabled": source.enabled,
                    "base_url": source.base_url,
                }
            )
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
        5. Parse and persist
        """
        self.register_default_sources()

        # Find in catalog
        item = self._gii.find_in_catalog(key)
        if item is None:
            logger.warning("Instrument '%s' not found in GII catalog", key)
            return None

        # Sync
        parsed = self._gii.sync_instrument(item)

        # Check for existing snapshot with same hash
        existing = self._repo.get_snapshot_by_hash(parsed.snapshot.sha256)
        if existing is not None:
            logger.info(
                "Snapshot already exists for %s (hash: %s...) — skipping duplicate",
                item.abbreviation,
                parsed.snapshot.sha256[:16],
            )
            parsed.snapshot.import_status = parsed.snapshot.import_status or ImportStatus.DUPLICATE  # type: ignore[name-defined]
            return parsed

        # Persist snapshot
        self._repo.save_snapshot(parsed.snapshot)

        # Check for existing instrument and update/insert
        existing_inst = self._repo.get_instrument_by_abbreviation(parsed.instrument.abbreviation)
        if existing_inst is not None:
            parsed.instrument.instrument_id = existing_inst.instrument_id
            parsed.expression.instrument_id = existing_inst.instrument_id

        self._repo.save_instrument(parsed.instrument)
        self._repo.save_expression(parsed.expression)

        # Persist provisions
        for provision in parsed.provisions:
            self._repo.save_provision(provision)

        # Rebuild FTS index after adding provisions
        try:
            self._repo.rebuild_fts_index()
        except Exception as exc:
            logger.warning("FTS index rebuild failed (non-fatal): %s", exc)

        logger.info(
            "Synced instrument %s: %d provisions",
            parsed.instrument.abbreviation,
            len(parsed.provisions),
        )

        return parsed

    # ── Search ───────────────────────────────────

    def search(self, query: str, limit: int = 50) -> list[dict]:
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
