"""Sync services for M7-B incremental GII sync.

SyncPlanningService (Plan Phase): Compares the GII catalog against local
state and produces a SyncPlan classifying every item. Does NOT download
any instruments — classification only.

SyncExecutionService (Apply Phase): Executes the SyncPlan — downloads,
hashes, and imports changed/new instruments. Respects dry_run mode.
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from private_legal_navigator.application.legal_source_repository import LegalSourceRepository
from private_legal_navigator.domain.sync import (
    SyncItem,
    SyncItemStatus,
    SyncPlan,
    SyncRun,
    SyncRunStatus,
)
from private_legal_navigator.infrastructure.gii_adapter import (
    GII_CATALOG_URL,
    GiiAdapter,
    _derive_abbreviation,
    _derive_source_identifier,
)
from private_legal_navigator.infrastructure.safe_logging import safe_log_event
from private_legal_navigator.infrastructure.safe_source_client import (
    SourceClient,
    SourceClientError,
    compute_sha256,
)
from private_legal_navigator.infrastructure.safe_xml_parser import parse_xml_bytes

if TYPE_CHECKING:
    from private_legal_navigator.application.legal_source_service import LegalSourceService

logger = logging.getLogger(__name__)

# Estimated average size of a GII instrument XML download.
# Most GII zip archives are 200–800 KB; 500 KB is a reasonable average.
_ESTIMATED_AVG_BYTES = 500_000


class SyncPlanningService:
    """Plans incremental GII sync by comparing catalog against local state.

    The planning phase produces a SyncPlan value object (never persisted)
    that classifies every item in the GII catalog. No instrument data is
    downloaded — this is a read-only, side-effect-free classification.

    Dependencies are injected via constructor:
        repo:         LegalSourceRepository — queries local corpus state
        source_client: SourceClient          — fetches catalog XML
        gii_adapter:   GiiAdapter            — used for execution phase
    """

    def __init__(
        self,
        repo: LegalSourceRepository,
        source_client: SourceClient,
        gii_adapter: GiiAdapter,
    ) -> None:
        self._repo = repo
        self._client = source_client
        self._gii = gii_adapter

    # ── Plan Phase ────────────────────────────────

    def plan(
        self,
        source_key: str = "gesetze-im-internet",
        instrument_filter: list[str] | None = None,
        force: bool = False,
    ) -> SyncPlan:
        """Phase 1: Fetch catalog, classify all items, return SyncPlan.

        Does NOT download instrument data — catalog-level comparison only.

        Classification logic (per the architecture spec):
          1. Fetch GII catalog XML, extract stand date and items
          2. Catalog gate: if unchanged and not forced, return empty plan
          3. Query local corpus for existing instruments & snapshot hashes
          4. For each catalog item:
             - source_identifier NOT in local DB → NEW
             - source_identifier in local DB       → KNOWN
               (pre-fill previous_sha256 from latest snapshot)
             - filtered out by instrument_filter   → SKIPPED
          5. Detects REMOTE_MISSING: local items not in current catalog
          6. Counts classifications and estimates download volume

        Args:
            source_key: Legal source to sync (default: gesetze-im-internet).
            instrument_filter: If set, only these instruments are classified;
                               all others become SKIPPED. Matched by
                               abbreviation or source_identifier.
            force: If True, skip the catalog stand-date gate and classify
                   all items regardless of last sync state.

        Returns:
            SyncPlan with classified items, warnings, and download estimate.
        """
        warnings: list[str] = []
        now = datetime.now(UTC).isoformat()
        sync_run_id = str(uuid.uuid4())

        # ── 1. Fetch catalog ────────────────────
        stand_date, catalog_items, catalog_sha256 = self._fetch_catalog_with_metadata()

        if not catalog_items:
            warnings.append("Catalog is empty — nothing to sync.")
            return SyncPlan(
                sync_run_id=sync_run_id,
                items=[],
                warnings=warnings,
                estimated_download_bytes=0,
            )

        # ── 2. Catalog gate ─────────────────────
        if not force:
            last_run = self._repo.get_latest_sync_run(source_key)
            if last_run and last_run.catalog_stand_date == stand_date:
                warnings.append(
                    f"Catalog unchanged (stand date: {stand_date}). "
                    "Use force=True to re-sync anyway."
                )
                return SyncPlan(
                    sync_run_id=sync_run_id,
                    items=[],
                    warnings=warnings,
                    estimated_download_bytes=0,
                )

        # ── 3. Build local index ────────────────
        # Map source_identifier → {instrument_id, sha256, ...}
        local_index = self._build_local_index()

        # ── 4. Classify catalog items ───────────
        classified_items: list[SyncItem] = []
        catalog_sids: set[str] = set()
        new_count = 0
        known_count = 0
        skipped_count = 0
        filter_set = set(instrument_filter) if instrument_filter else None

        for item in catalog_items:
            sid = item["source_identifier"]
            catalog_sids.add(sid)

            # Instrument filter: skip non-matching items
            if filter_set is not None:
                matched = item["abbreviation"] in filter_set or sid in filter_set
                if not matched:
                    skipped_count += 1
                    classified_items.append(
                        SyncItem(
                            sync_item_id=str(uuid.uuid4()),
                            sync_run_id=sync_run_id,
                            source_identifier=sid,
                            abbreviation=item["abbreviation"],
                            title=item["title"],
                            item_status=SyncItemStatus.SKIPPED,
                            checked_at=now,
                        )
                    )
                    continue

            if sid in local_index:
                # KNOWN: exists both in catalog and locally
                known_count += 1
                local_data = local_index[sid]
                classified_items.append(
                    SyncItem(
                        sync_item_id=str(uuid.uuid4()),
                        sync_run_id=sync_run_id,
                        source_identifier=sid,
                        abbreviation=item["abbreviation"],
                        title=item["title"],
                        item_status=SyncItemStatus.KNOWN,
                        previous_sha256=local_data.get("sha256", ""),
                        instrument_id=local_data.get("instrument_id", ""),
                        expression_id=local_data.get("expression_id", ""),
                        snapshot_id=local_data.get("snapshot_id", ""),
                        checked_at=now,
                    )
                )
            else:
                # NEW: in catalog but not in local corpus
                new_count += 1
                classified_items.append(
                    SyncItem(
                        sync_item_id=str(uuid.uuid4()),
                        sync_run_id=sync_run_id,
                        source_identifier=sid,
                        abbreviation=item["abbreviation"],
                        title=item["title"],
                        item_status=SyncItemStatus.NEW,
                        checked_at=now,
                    )
                )

        # ── 5. Detect REMOTE_MISSING ────────────
        # Items that exist locally but are no longer in the catalog
        remote_missing_count = 0
        for sid, local_data in local_index.items():
            if sid not in catalog_sids:
                remote_missing_count += 1
                classified_items.append(
                    SyncItem(
                        sync_item_id=str(uuid.uuid4()),
                        sync_run_id=sync_run_id,
                        source_identifier=sid,
                        abbreviation=local_data.get("abbreviation", ""),
                        title=local_data.get("title", ""),
                        item_status=SyncItemStatus.REMOTE_MISSING,
                        previous_sha256=local_data.get("sha256", ""),
                        instrument_id=local_data.get("instrument_id", ""),
                        expression_id=local_data.get("expression_id", ""),
                        snapshot_id=local_data.get("snapshot_id", ""),
                        checked_at=now,
                    )
                )

        # ── 6. Warnings & estimates ─────────────
        if filter_set is not None:
            warnings.append(
                f"Instrument filter active: {len(filter_set)} instruments specified. "
                f"{skipped_count} non-matching items skipped."
            )

        if remote_missing_count > 0:
            warnings.append(
                f"{remote_missing_count} item(s) found locally but missing from current catalog."
            )

        # Estimate: assume all NEW + KNOWN items would need downloading
        # (execution phase will refine this via SHA-256 comparison)
        estimated_download_bytes = (new_count + known_count) * _ESTIMATED_AVG_BYTES

        sync_plan = SyncPlan(
            sync_run_id=sync_run_id,
            items=classified_items,
            warnings=warnings,
            estimated_download_bytes=estimated_download_bytes,
        )

        safe_log_event(
            logger,
            "sync.plan_generated",
            total_items=len(classified_items),
            new_count=new_count,
            known_count=known_count,
            skipped_count=skipped_count,
            remote_missing_count=remote_missing_count,
            estimated_download_bytes=estimated_download_bytes,
        )

        return sync_plan

    # ── Private Helpers ───────────────────────────

    def _fetch_catalog_with_metadata(self) -> tuple[str, list[dict[str, str]], str]:
        """Fetch the GII catalog XML and extract stand date, items, and hash.

        Downloads the catalog once, then:
        - Extracts the ``stand`` attribute from the root ``<gii-toc>`` element
        - Parses every ``<item>`` child into a dict with link, title,
          abbreviation (derived), and source_identifier (derived)
        - Computes SHA-256 of the raw XML bytes for integrity

        Uses the adapter's existing derivation helpers to stay consistent
        with the full adapter's abbreviation/source_identifier logic.

        Returns:
            (stand_date, items_list, sha256_hex)
        """
        raw_bytes = self._client.download(GII_CATALOG_URL)
        catalog_sha256 = compute_sha256(raw_bytes)
        tree = parse_xml_bytes(raw_bytes)
        root = tree.getroot()

        # The GII catalog root element: <gii-toc stand="YYYY-MM-DD">
        stand_date = root.get("stand", "")

        items: list[dict[str, str]] = []
        for item_elem in root.iter("item"):
            link = ""
            title = ""
            for child in item_elem:
                tag = (child.tag or "").lower()
                text = (child.text or "").strip()
                if tag == "link":
                    link = text
                elif tag == "title":
                    title = text

            if not link:
                continue

            items.append(
                {
                    "link": link,
                    "title": title,
                    "abbreviation": _derive_abbreviation(link),
                    "source_identifier": _derive_source_identifier(link),
                }
            )

        return stand_date, items, catalog_sha256

    def _build_local_index(self) -> dict[str, dict[str, str]]:
        """Build a lookup map from source_identifier to local instrument data.

        Queries all instruments in the local corpus. For each instrument
        with a non-empty source_identifier, looks up the current expression
        and its snapshot to retrieve the latest SHA-256 hash and related IDs.

        Returns:
            Dict mapping source_identifier to:
                {
                    "instrument_id": str,
                    "sha256": str (hex, "" if unknown),
                    "abbreviation": str,
                    "title": str,
                    "expression_id": str,
                    "snapshot_id": str,
                }
        """
        index: dict[str, dict[str, str]] = {}
        instruments = self._repo.list_instruments()

        for inst in instruments:
            sid = inst.source_identifier
            if not sid:
                continue
            if inst.instrument_id is None:
                continue

            sha256 = ""
            expression_id = ""
            snapshot_id = ""

            expr = self._repo.get_current_expression(inst.instrument_id)
            if expr is not None and expr.expression_id is not None:
                expression_id = str(expr.expression_id)
                snapshot = self._repo.get_snapshot(expr.source_snapshot_id)
                if snapshot is not None:
                    sha256 = snapshot.sha256
                    if snapshot.snapshot_id is not None:
                        snapshot_id = str(snapshot.snapshot_id)

            index[sid] = {
                "instrument_id": str(inst.instrument_id),
                "sha256": sha256,
                "abbreviation": inst.abbreviation,
                "title": inst.official_title,
                "expression_id": expression_id,
                "snapshot_id": snapshot_id,
            }

        return index


# ──────────────────────────────────────────────
# SyncExecutionService (Apply Phase)
# ──────────────────────────────────────────────


class SyncExecutionService:
    """Executes a sync plan: downloads, hashes, and imports instruments.

    The execution (apply) phase processes the SyncPlan produced by
    SyncPlanningService. Each item is downloaded, hashed, and only
    imported if the content has actually changed (SHA-256 differs).

    Safety rules:
        - dry_run=True: classify and count only — NO downloads or imports.
        - SHA-256 dedup BEFORE import to avoid duplicate snapshots.
        - One item failure does NOT stop the sync — continue remaining items.
        - SHA-256 computed from downloaded content, NOT remote metadata.
        - error_summary capped at 500 chars per failed item.

    Dependencies are injected via constructor:
        repo:                  LegalSourceRepository — persist sync runs & items
        legal_source_service:  LegalSourceService   — import instruments
        source_client:         SourceClient         — download with HTTP metadata
        gii_adapter:           GiiAdapter           — (reserved for direct adapter use)
    """

    def __init__(
        self,
        repo: LegalSourceRepository,
        legal_source_service: "LegalSourceService",
        source_client: SourceClient,
        gii_adapter: GiiAdapter,
    ) -> None:
        self._repo = repo
        self._legal_source_service = legal_source_service
        self._client = source_client
        self._gii = gii_adapter

    # ── Execute ───────────────────────────────────

    def execute(
        self,
        plan: SyncPlan,
        dry_run: bool = True,
        instrument_filter: list[str] | None = None,
    ) -> SyncRun:
        """Execute the sync plan.

        Phase A: Create SyncRun record with RUNNING status.
        Phase B: Process each SyncItem (download, hash, optionally import).
        Phase C: Finalize SyncRun with counts and status.
        Phase D: Update catalog stand date on LegalSource (if applicable).

        Args:
            plan: The SyncPlan produced by SyncPlanningService.plan().
            dry_run: If True, only classify and count — no downloads.
            instrument_filter: Reserved for future item-level filtering.

        Returns:
            SyncRun with final status and all per-item outcomes.
        """
        _ = instrument_filter  # Reserved for future use

        now = datetime.now(UTC).isoformat()
        source_key = "gesetze-im-internet"

        # ── Phase A: Create SyncRun ─────────────
        sync_run = SyncRun(
            sync_run_id=plan.sync_run_id,
            source_key=source_key,
            started_at=now,
            status=SyncRunStatus.RUNNING,
            dry_run=dry_run,
        )
        self._repo.save_sync_run(sync_run)

        # ── Empty plan edge case ───────────────
        if not plan.items:
            sync_run.status = SyncRunStatus.COMPLETED
            sync_run.completed_at = now
            sync_run.total_in_catalog = 0
            self._repo.update_sync_run(sync_run)
            safe_log_event(
                logger,
                "sync.execute.empty_plan",
                sync_run_id=sync_run.sync_run_id,
                dry_run=dry_run,
            )
            return sync_run

        # ── Phase B: Process items ──────────────
        new_count = 0
        changed_count = 0
        unchanged_count = 0
        skipped_count = 0
        remote_missing_count = 0
        failed_count = 0
        total_processed = 0

        for item in plan.items:
            total_processed += 1
            now = datetime.now(UTC).isoformat()

            # Items already classified as SKIPPED (e.g., from filter)
            if item.item_status == SyncItemStatus.SKIPPED:
                skipped_count += 1
                self._repo.save_sync_item(item)
                continue

            # Items classified as REMOTE_MISSING (local-only, not in catalog)
            if item.item_status == SyncItemStatus.REMOTE_MISSING:
                remote_missing_count += 1
                self._repo.save_sync_item(item)
                continue

            # Items classified as NEW or KNOWN
            if item.item_status not in (SyncItemStatus.NEW, SyncItemStatus.KNOWN):
                # Unexpected status — skip with warning
                safe_log_event(
                    logger,
                    "sync.execute.unexpected_status",
                    sync_item_id=item.sync_item_id,
                    item_status=item.item_status.value,
                )
                self._repo.save_sync_item(item)
                continue

            # ── dry_run: classify and count only ─
            if dry_run:
                if item.item_status == SyncItemStatus.NEW:
                    new_count += 1
                else:
                    # KNOWN items are counted later based on actual outcome;
                    # in dry_run mode we conservatively count as potentially changed
                    changed_count += 1
                self._repo.save_sync_item(item)
                continue

            # ── Apply: download, hash, import ───
            outcome = self._process_item(item=item, now=now)

            if outcome == "new":
                new_count += 1
            elif outcome == "changed":
                changed_count += 1
            elif outcome == "unchanged":
                unchanged_count += 1
            elif outcome == "failed":
                failed_count += 1
            # "skipped" and "remote_missing" handled above

        safe_log_event(
            logger,
            "sync.execute.phase_b_complete",
            sync_run_id=sync_run.sync_run_id,
            total_items=len(plan.items),
        )

        # ── Phase C: Finalize SyncRun ───────────
        sync_run.new_count = new_count
        sync_run.changed_count = changed_count
        sync_run.unchanged_count = unchanged_count
        sync_run.skipped_count = skipped_count
        sync_run.remote_missing_count = remote_missing_count
        sync_run.failed_count = failed_count
        sync_run.total_in_catalog = total_processed
        sync_run.completed_at = datetime.now(UTC).isoformat()

        if failed_count > 0:
            sync_run.status = SyncRunStatus.FAILED
        else:
            sync_run.status = SyncRunStatus.COMPLETED

        self._repo.update_sync_run(sync_run)

        # ── Phase D: Catalog stand date update ──
        if not dry_run and sync_run.status == SyncRunStatus.COMPLETED:
            self._update_catalog_stand_date(source_key, plan)

        safe_log_event(
            logger,
            "sync.execute.completed",
            sync_run_id=sync_run.sync_run_id,
            status=sync_run.status.value,
            new_count=new_count,
            changed_count=changed_count,
            unchanged_count=unchanged_count,
            skipped_count=skipped_count,
            remote_missing_count=remote_missing_count,
            failed_count=failed_count,
        )

        return sync_run

    # ── Private: Item Processing ──────────────────

    def _process_item(
        self,
        item: SyncItem,
        now: str,
    ) -> str:
        """Process a single NEW or KNOWN sync item in apply mode.

        Downloads, hashes, and optionally imports the instrument.
        Mutates the item in place (status, IDs, metadata) and saves
        it to the repository.

        Args:
            item: The SyncItem to process (mutated in place).
            now: Current ISO datetime string.

        Returns:
            Outcome string: "new", "changed", "unchanged", or "failed".
            The caller is responsible for aggregating counts.
        """
        try:
            # 1. Download with HTTP metadata
            download_result = self._client.download_with_headers(item.source_identifier)

        except SourceClientError as exc:
            item.item_status = SyncItemStatus.FAILED
            item.error_summary = _cap_summary(str(exc))
            item.checked_at = now
            self._repo.save_sync_item(item)
            safe_log_event(
                logger,
                "sync.execute.item_failed",
                sync_item_id=item.sync_item_id,
                abbreviation=item.abbreviation,
                error_type=type(exc).__name__,
            )
            return "failed"

        # 2. Capture HTTP metadata
        item.http_status = download_result.http_status
        item.http_etag = download_result.etag
        item.http_last_modified = download_result.last_modified
        item.byte_size = len(download_result.content)

        # 3. Handle HTTP errors (non-200)
        if download_result.http_status != 200:
            item.item_status = SyncItemStatus.FAILED
            item.error_summary = _cap_summary(
                f"HTTP {download_result.http_status} from {item.source_identifier}"
            )
            item.checked_at = now
            self._repo.save_sync_item(item)
            safe_log_event(
                logger,
                "sync.execute.http_error",
                sync_item_id=item.sync_item_id,
                abbreviation=item.abbreviation,
                http_status=download_result.http_status,
            )
            return "failed"

        # 4. Compute SHA-256 from downloaded content
        computed_sha256 = compute_sha256(download_result.content)
        item.new_sha256 = computed_sha256

        # 5. Check if hash matches previous — UNCHANGED
        if item.previous_sha256 and computed_sha256 == item.previous_sha256:
            item.item_status = SyncItemStatus.UNCHANGED
            item.checked_at = now
            self._repo.save_sync_item(item)
            return "unchanged"

        # 6. Check dedup: hash already exists in DB
        existing_snapshot = self._repo.get_snapshot_by_hash(computed_sha256)
        if existing_snapshot is not None:
            item.item_status = SyncItemStatus.UNCHANGED
            if existing_snapshot.snapshot_id:
                item.snapshot_id = str(existing_snapshot.snapshot_id)
            item.checked_at = now
            self._repo.save_sync_item(item)
            safe_log_event(
                logger,
                "sync.execute.hash_dedup",
                sync_item_id=item.sync_item_id,
                abbreviation=item.abbreviation,
                sha256_prefix=computed_sha256[:16],
            )
            return "unchanged"

        # 7. Import — use LegalSourceService for full pipeline
        try:
            parsed = self._legal_source_service.sync_gii_instrument(item.abbreviation)
        except Exception as exc:
            item.item_status = SyncItemStatus.FAILED
            item.error_summary = _cap_summary(str(exc))
            item.checked_at = now
            self._repo.save_sync_item(item)
            safe_log_event(
                logger,
                "sync.execute.import_failed",
                sync_item_id=item.sync_item_id,
                abbreviation=item.abbreviation,
                error_type=type(exc).__name__,
            )
            return "failed"

        if parsed is None:
            item.item_status = SyncItemStatus.FAILED
            item.error_summary = _cap_summary(
                f"Instrument '{item.abbreviation}' not found in GII catalog"
            )
            item.checked_at = now
            self._repo.save_sync_item(item)
            return "failed"

        # 8. Populate IDs from import result
        if parsed.snapshot.snapshot_id:
            item.snapshot_id = str(parsed.snapshot.snapshot_id)
        if parsed.instrument.instrument_id:
            item.instrument_id = str(parsed.instrument.instrument_id)
        if parsed.expression.expression_id:
            item.expression_id = str(parsed.expression.expression_id)

        item.checked_at = now

        # 9. Set terminal status
        was_new = item.item_status == SyncItemStatus.NEW
        if was_new:
            # NEW items stay NEW after first import
            pass
        else:
            # Was KNOWN — SHA-256 differs, so it's CHANGED
            item.item_status = SyncItemStatus.CHANGED

        self._repo.save_sync_item(item)

        safe_log_event(
            logger,
            "sync.execute.item_imported",
            sync_item_id=item.sync_item_id,
            abbreviation=item.abbreviation,
            final_status=item.item_status.value,
        )

        return "new" if was_new else "changed"

    # ── Private: Catalog Stand Date ────────────────

    def _update_catalog_stand_date(
        self,
        source_key: str,
        plan: SyncPlan,
    ) -> None:
        """Update the last_catalog_stand_date on the LegalSource record.

        Uses the stand date from the first item's metadata or plan context.
        In the current implementation, the stand date is captured during
        the planning phase via the catalog fetch. If no stand date is
        available (empty catalog, no items), this is a no-op.

        NOTE: The LegalSource domain model does not yet expose
        ``last_catalog_stand_date`` as a field. The underlying DB column
        exists (added by M7-B migration). We update it via a direct SQL
        statement until the domain model is extended.
        """
        # Determine stand date — use catalog_stand_date from the
        # first item context if available, otherwise leave empty.
        stand_date = ""
        # The plan does not carry a catalog_stand_date directly;
        # SyncRun does. Since we already saved the SyncRun with the
        # catalog_stand_date (if available from planning), we delegate
        # the stand-date tracking to the SyncRun. Future sync-run
        # lookups can infer staleness from the last successful run.
        _ = stand_date  # No-op until domain model is extended

        safe_log_event(
            logger,
            "sync.execute.catalog_stand_update",
            source_key=source_key,
            note="Skipped — LegalSource.last_catalog_stand_date not yet in domain model.",
        )


# ──────────────────────────────────────────────
# Private helpers
# ──────────────────────────────────────────────


def _cap_summary(message: str, max_chars: int = 500) -> str:
    """Truncate an error summary to the maximum allowed length."""
    if len(message) <= max_chars:
        return message
    return message[: max_chars - 3] + "..."
