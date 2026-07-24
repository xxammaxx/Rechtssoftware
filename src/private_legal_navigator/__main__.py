"""Entry point for running PrivateLegalNavigator.

Supports two modes:
  python -m private_legal_navigator              → start server
  python -m private_legal_navigator serve        → start server (explicit)

M7-A CLI commands:
  python -m private_legal_navigator legal-source status
  python -m private_legal_navigator legal-source sync --source gii --instrument <KEY>
  python -m private_legal_navigator legal-source verify
  python -m private_legal_navigator legal-search "<QUERY>"
  python -m private_legal_navigator legal-citation resolve "<CITATION>"
  python -m private_legal_navigator legal-evidence export --case-id <ID> --output <PATH>
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from typing import TYPE_CHECKING, Any

from private_legal_navigator import __version__

if TYPE_CHECKING:
    from private_legal_navigator.application.legal_source_service import LegalSourceService
    from private_legal_navigator.config import Settings


def main() -> None:
    """Parse args and route to appropriate handler."""
    parser = _build_parser()
    args = parser.parse_args()

    if args.command is None:
        # Default: start server
        _start_server()
    elif args.command == "serve":
        _start_server()
    elif args.command == "legal-source":
        _handle_legal_source(args)
    elif args.command == "legal-search":
        _handle_legal_search(args)
    elif args.command == "legal-citation":
        _handle_legal_citation(args)
    elif args.command == "legal-evidence":
        _handle_legal_evidence(args)
    else:
        parser.print_help()
        sys.exit(1)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="private-legal-navigator",
        description="Local privacy-first legal assistance tool",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"PrivateLegalNavigator %(prog)s {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command")

    # serve
    subparsers.add_parser("serve", help="Start the local server (default)")

    # legal-source
    ls_parser = subparsers.add_parser("legal-source", help="Legal source management")
    ls_sub = ls_parser.add_subparsers(dest="ls_action", required=True)

    ls_sub.add_parser("status", help="Show source registry status")
    # ── M7-B: sync (incremental) ──
    sync_parser = ls_sub.add_parser("sync", help="Sync legal source instruments")
    sync_parser.add_argument("--source", default="gii", help="Source key (default: gii)")
    sync_parser.add_argument("--instrument", help="Single instrument key/abbreviation")
    sync_parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Preview changes without downloading (default)",
    )
    sync_parser.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Actually download and import changed instruments",
    )
    sync_parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Force full sync (ignore catalog stand-date gate)",
    )

    # ── M7-B: sync-status ──
    status_parser = ls_sub.add_parser("sync-status", help="Show sync run history")
    status_parser.add_argument("--source", default="gesetze-im-internet", help="Source key")
    status_parser.add_argument("--last", type=int, default=5, help="Number of recent runs to show")

    verify_parser = ls_sub.add_parser("verify", help="Verify snapshot integrity")
    verify_parser.add_argument("--json", action="store_true", help="Output as JSON")
    verify_parser.add_argument("--snapshot-id", help="Verify a specific snapshot by UUID")

    # legal-search
    search_parser = subparsers.add_parser("legal-search", help="Search the legal corpus")
    search_parser.add_argument("query", help="Search query text")

    # legal-citation
    cit_parser = subparsers.add_parser("legal-citation", help="Citation resolution")
    cit_sub = cit_parser.add_subparsers(dest="cit_action", required=True)
    resolve_parser = cit_sub.add_parser("resolve", help="Resolve a legal citation")
    resolve_parser.add_argument("citation", help="Citation text (e.g., '§ 48 SGB X')")

    # legal-evidence
    ev_parser = subparsers.add_parser("legal-evidence", help="Evidence pack operations")
    ev_sub = ev_parser.add_subparsers(dest="ev_action", required=True)
    export_parser = ev_sub.add_parser("export", help="Export evidence pack")
    export_parser.add_argument("--case-id", required=True, help="Case UUID")
    export_parser.add_argument("--output", required=True, help="Output file path")

    return parser


def _print_verify_results(results: list[dict[str, Any]]) -> None:
    """Print verification results in human-readable format."""
    ok = sum(1 for r in results if r["status"] == "VERIFIED")
    fail = sum(1 for r in results if r["status"] == "FAILED")
    missing = sum(1 for r in results if r["status"] == "MISSING")
    total = len(results)

    print("\nSnapshot Integrity Verification")
    print(f"{'=' * 50}")
    print(f"Total snapshots: {total}")
    print(f"  VERIFIED: {ok}")
    if fail:
        print(f"  FAILED:   {fail}")
    if missing:
        print(f"  MISSING:  {missing}")
    print()

    for r in results:
        if r["status"] != "VERIFIED":
            sid = r.get("snapshot_id", "?")[:8]
            print(f"  [{r['status']}] {sid}... — {r.get('error_code', '')}")
            if r.get("expected_sha256"):
                print(f"    Expected: {r['expected_sha256'][:16]}...")
            if r.get("actual_sha256"):
                print(f"    Actual:   {r['actual_sha256'][:16]}...")
            print()


# ──────────────────────────────────────────────
# Handlers
# ──────────────────────────────────────────────


def _start_server() -> None:
    import uvicorn

    from private_legal_navigator.config import Settings

    settings = Settings()
    uvicorn.run(
        "private_legal_navigator.app:create_app",
        host=settings.host,
        port=settings.port,
        factory=True,
        log_level="warning",
        access_log=False,
    )


def _get_legal_service() -> tuple[LegalSourceService, Settings]:
    """Get the legal source service with all dependencies."""
    from private_legal_navigator.application.legal_source_service import LegalSourceService
    from private_legal_navigator.config import Settings
    from private_legal_navigator.infrastructure.safe_source_client import SourceClient
    from private_legal_navigator.infrastructure.sqlite_legal_source_repository import (
        SqliteLegalSourceRepository,
    )

    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    snapshot_dir = settings.data_dir / "snapshots"
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    repo = SqliteLegalSourceRepository(settings.database_path)
    repo.initialize_schema()
    client = SourceClient()
    return LegalSourceService(repo, client, snapshot_dir), settings


def _handle_legal_source(args: argparse.Namespace) -> None:
    action = args.ls_action

    if action == "status":
        svc, _ = _get_legal_service()
        sources = svc.get_source_status()
        print(json.dumps(sources, indent=2, ensure_ascii=False))
        sys.exit(0)

    elif action == "sync":
        if args.instrument:
            # Single-instrument sync (legacy M7-A mode)
            svc, _ = _get_legal_service()
            print(f"Synchronizing {args.instrument} from {args.source}...")
            parsed = svc.sync_gii_instrument(args.instrument)
            if parsed is None:
                print(f"Error: Instrument '{args.instrument}' not found in GII catalog.")
                sys.exit(3)
            print(f"Done: {parsed.instrument.official_title}")
            print(f"  Abbreviation: {parsed.instrument.abbreviation}")
            print(f"  Provisions: {len(parsed.provisions)}")
            print(f"  Snapshot SHA-256: {parsed.snapshot.sha256}")
            print(f"  Authority: {parsed.instrument.authority_tier.value}")
            sys.exit(0)
        else:
            # M7-B: Incremental catalog-wide sync
            _handle_incremental_sync(args)

    elif action == "sync-status":
        _handle_sync_status(args)

    elif action == "verify":
        svc, _ = _get_legal_service()

        if hasattr(args, "snapshot_id") and args.snapshot_id:
            try:
                sid = uuid.UUID(args.snapshot_id)
            except ValueError:
                print(f"Error: Invalid snapshot ID: {args.snapshot_id}", file=sys.stderr)
                sys.exit(2)
            result = svc.verify_snapshot_detailed(sid)
            results = [result]
            if args.json:
                print(json.dumps(results, indent=2, ensure_ascii=False))
            else:
                _print_verify_results(results)
            has_failures = any(r["status"] in ("FAILED", "MISSING") for r in results)
            sys.exit(5 if has_failures else 0)
        else:
            results = svc.verify_all_snapshots()
            if not results:
                print("No snapshots found. Nothing to verify.")
                sys.exit(4)
            if args.json:
                print(json.dumps(results, indent=2, ensure_ascii=False))
            else:
                _print_verify_results(results)
            has_failures = any(r["status"] in ("FAILED", "MISSING") for r in results)
            sys.exit(5 if has_failures else 0)
    else:
        print(f"Unknown legal-source action: {action}")
        sys.exit(2)


def _handle_incremental_sync(args: argparse.Namespace) -> None:
    """M7-B: Incremental GII catalog-wide sync (dry-run or apply)."""
    from private_legal_navigator.application.sync_service import (
        SyncExecutionService,
        SyncPlanningService,
    )
    from private_legal_navigator.config import Settings
    from private_legal_navigator.infrastructure.gii_adapter import GiiAdapter
    from private_legal_navigator.infrastructure.safe_source_client import SourceClient
    from private_legal_navigator.infrastructure.sqlite_legal_source_repository import (
        SqliteLegalSourceRepository,
    )

    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    snapshot_dir = settings.data_dir / "snapshots"
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    repo = SqliteLegalSourceRepository(settings.database_path)
    repo.initialize_schema()
    client = SourceClient()

    from private_legal_navigator.application.legal_source_service import LegalSourceService

    legal_svc = LegalSourceService(repo, client, snapshot_dir)

    gii_adapter = GiiAdapter(client, snapshot_dir)

    planner = SyncPlanningService(repo, client, gii_adapter)
    executor = SyncExecutionService(repo, legal_svc, client, gii_adapter)

    dry_run = not args.apply

    print(f"\n{'DRY-RUN' if dry_run else 'APPLY'}: Incremental GII Sync")
    print(f"{'=' * 60}")

    # Phase 1: Plan
    print("Planning...")
    plan = planner.plan(source_key=args.source, force=args.force)

    if plan.warnings:
        for w in plan.warnings:
            print(f"  WARNING: {w}")

    # Count summary
    items = plan.items
    new = sum(1 for i in items if i.item_status.value == "NEW")
    known = sum(1 for i in items if i.item_status.value == "KNOWN")
    remote_missing = sum(1 for i in items if i.item_status.value == "REMOTE_MISSING")
    skipped = sum(1 for i in items if i.item_status.value == "SKIPPED")

    print(f"\nCatalog items: {len(items)}")
    print(f"  NEW:            {new}")
    print(f"  KNOWN:          {known}")
    print(f"  REMOTE_MISSING: {remote_missing}")
    if skipped:
        print(f"  SKIPPED:        {skipped}")

    if dry_run:
        print(f"\nEstimated downloads: {new + known}")
        print(f"Estimated download size: ~{plan.estimated_download_bytes / (1024 * 1024):.1f} MB")
        print(f"\nDry-run complete. No changes made.")
        print(f"Run with --apply to execute this plan.")
        sys.exit(1)
    else:
        # Phase 2: Execute
        print(f"\nDownloading and importing {new + known} instruments...")
        sync_run = executor.execute(plan, dry_run=False)

        print(f"\nSync complete: {sync_run.status.value}")
        print(f"  New:            {sync_run.new_count}")
        print(f"  Changed:        {sync_run.changed_count}")
        print(f"  Unchanged:      {sync_run.unchanged_count}")
        print(f"  Remote missing: {sync_run.remote_missing_count}")
        print(f"  Failed:         {sync_run.failed_count}")
        if sync_run.error_summary:
            print(f"  Errors:         {sync_run.error_summary[:200]}")

        if sync_run.failed_count > 0:
            sys.exit(2)
        sys.exit(0)


def _handle_sync_status(args: argparse.Namespace) -> None:
    """M7-B: Show sync run history."""
    from private_legal_navigator.config import Settings
    from private_legal_navigator.infrastructure.sqlite_legal_source_repository import (
        SqliteLegalSourceRepository,
    )

    settings = Settings()
    repo = SqliteLegalSourceRepository(settings.database_path)
    repo.initialize_schema()

    latest = repo.get_latest_sync_run(args.source, successful_only=False)

    if latest is None:
        print(f"No sync history found for source '{args.source}'.")
        sys.exit(0)

    print(f"\nSync History: {args.source}")
    print(f"{'=' * 60}")
    print(f"  Last sync:        {latest.started_at}")
    print(f"  Status:           {latest.status.value}")
    print(f"  Catalog date:     {latest.catalog_stand_date}")
    print(f"  Total in catalog: {latest.total_in_catalog}")
    print(f"  New:              {latest.new_count}")
    print(f"  Changed:          {latest.changed_count}")
    print(f"  Unchanged:        {latest.unchanged_count}")
    print(f"  Failed:           {latest.failed_count}")
    if latest.completed_at:
        print(f"  Completed:        {latest.completed_at}")
    sys.exit(0)


def _handle_legal_search(args: argparse.Namespace) -> None:
    svc, _ = _get_legal_service()
    results = svc.search(args.query)
    if not results:
        print(f"No results found for: {args.query}")
        sys.exit(7)
    print(json.dumps(results, indent=2, ensure_ascii=False, default=str))
    sys.exit(0)


def _handle_legal_citation(args: argparse.Namespace) -> None:
    if args.cit_action != "resolve":
        print(f"Unknown citation action: {args.cit_action}")
        sys.exit(2)

    svc, _ = _get_legal_service()
    from private_legal_navigator.application.citation_resolver import format_resolution_for_display

    resolved = svc.resolve_citation(args.citation)
    print(format_resolution_for_display(resolved))

    if resolved.status.value == "RESOLVED":
        sys.exit(0)
    elif resolved.status.value == "AMBIGUOUS":
        sys.exit(6)
    elif resolved.status.value == "NOT_FOUND":
        sys.exit(7)
    else:
        sys.exit(7)


def _handle_legal_evidence(args: argparse.Namespace) -> None:
    if args.ev_action != "export":
        print(f"Unknown evidence action: {args.ev_action}")
        sys.exit(2)

    from private_legal_navigator.application.case_timeline_service import (
        CaseTimelineService,
    )
    from private_legal_navigator.config import Settings
    from private_legal_navigator.infrastructure.sqlite_case_timeline_repository import (
        SqliteCaseTimelineRepository,
    )
    from private_legal_navigator.infrastructure.sqlite_legal_source_repository import (
        SqliteLegalSourceRepository,
    )

    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    timeline_repo = SqliteCaseTimelineRepository(settings.database_path)
    timeline_repo.initialize_schema()
    legal_repo = SqliteLegalSourceRepository(settings.database_path)
    legal_repo.initialize_schema()

    timeline_svc = CaseTimelineService(timeline_repo, legal_repo)

    try:
        case_id = uuid.UUID(args.case_id)
    except ValueError:
        print(f"Error: Invalid case ID: {args.case_id}")
        sys.exit(2)

    evidence = timeline_svc.export_evidence_pack(case_id)
    output_path = args.output
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(evidence, f, indent=2, ensure_ascii=False, default=str)
    print(f"Evidence pack exported to {output_path}")
    sys.exit(0)


if __name__ == "__main__":
    main()
