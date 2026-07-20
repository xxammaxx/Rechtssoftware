"""Application service for reference event lifecycle management.

Orchestrates the reference event use cases:
  1. List reference event candidates for an M5 deadline candidate
  2. Confirm/reject/revoke a reference event
  3. Get confirmation history
  4. Idempotency-protected confirmation actions (M6-UI)
"""

import hashlib
import hmac
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime

from private_legal_navigator.application.reference_event_repository import (
    IdempotencyKeyConflictError,
    ReferenceEventRepository,
)
from private_legal_navigator.domain.reference_event import (
    ConfirmationMethod,
    ConfirmedReferenceEvent,
    EventType,
    ReferenceEventCandidate,
    SourceType,
)


@dataclass
class ConfirmationActionResult:
    """Result of a confirmation action with idempotency metadata."""

    event: ConfirmedReferenceEvent
    was_replay: bool
    redirect_path: str
    result_status: str  # 'confirmed', 'rejected'


class ReferenceEventService:
    """Application service for reference event lifecycle management."""

    def __init__(self, repo: ReferenceEventRepository, secret_key: str = "") -> None:
        self._repo = repo
        self._secret = secret_key.encode("utf-8") if secret_key else b""

    # ── Payload and key helpers ───────────────────────────────────

    @staticmethod
    def compute_payload_digest(payload: dict[str, object]) -> str:
        """Compute a deterministic SHA-256 digest of a canonical payload.

        Uses sort_keys and compact separators for reproducibility.
        """
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _hash_key(self, raw_key: str) -> str:
        """HMAC-SHA256 the raw idempotency key.

        The raw key from the browser is never stored directly.
        Only the HMAC digest is persisted in SQLite.
        """
        if not self._secret:
            # Development fallback: SHA-256 without HMAC
            return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
        return hmac.new(self._secret, raw_key.encode("utf-8"), hashlib.sha256).hexdigest()

    def get_reference_event_candidates(
        self,
        document_id: uuid.UUID,
        deadline_candidate_index: int,
    ) -> list[ReferenceEventCandidate]:
        """Get reference event candidates for a deadline candidate."""
        return self._detect_candidates(document_id, deadline_candidate_index)

    def confirm(
        self,
        document_id: uuid.UUID,
        deadline_candidate_index: int,
        event_type: EventType,
        confirmed_date: date,
        source_type: SourceType,
        confirmation_method: ConfirmationMethod,
        candidate_id: uuid.UUID | None = None,
        evidence_note: str = "",
        confirmed_by: str = "",
    ) -> ConfirmedReferenceEvent:
        """Confirm a reference event.

        Creates a new ConfirmedReferenceEvent. Supersedes any active
        confirmation for the same candidate.
        """
        now = datetime.now(UTC)
        confirmation_id = uuid.uuid4()

        active = self._repo.get_active_confirmation(document_id, deadline_candidate_index)

        event = ConfirmedReferenceEvent(
            confirmation_id=confirmation_id,
            document_id=document_id,
            deadline_candidate_index=deadline_candidate_index,
            event_type=event_type,
            confirmed_date=confirmed_date,
            source_type=source_type,
            confirmation_method=confirmation_method,
            confirmed_at=now,
            candidate_id=candidate_id,
            evidence_note=evidence_note,
            confirmed_by=confirmed_by,
            supersedes_confirmation_id=active.confirmation_id if active else None,
        )
        self._repo.save_confirmation(event)
        return event

    def reject(
        self,
        document_id: uuid.UUID,
        deadline_candidate_index: int,
        event_type: EventType,
        candidate_id: uuid.UUID | None = None,
        source_type: SourceType = SourceType.AUTO_DETECTED,
        confirmation_method: ConfirmationMethod = ConfirmationMethod.AUTO_SUGGESTED,
    ) -> ConfirmedReferenceEvent:
        """Reject a reference event candidate.

        Creates a REJECTED record and supersedes any existing active
        confirmation. confirmed_date=None marks this as REJECTED.
        """
        now = datetime.now(UTC)

        # Supersede existing active confirmation if any
        active = self._repo.get_active_confirmation(document_id, deadline_candidate_index)

        rejection = ConfirmedReferenceEvent(
            confirmation_id=uuid.uuid4(),
            document_id=document_id,
            deadline_candidate_index=deadline_candidate_index,
            event_type=event_type,
            confirmed_at=now,
            confirmed_date=None,
            source_type=source_type,
            confirmation_method=confirmation_method,
            candidate_id=candidate_id,
            supersedes_confirmation_id=active.confirmation_id if active else None,
        )
        self._repo.save_confirmation(rejection)
        return rejection

    # ── Idempotency-protected actions (M6-UI) ──────────────────────

    def confirm_with_idempotency(
        self,
        idempotency_key: str,
        document_id: uuid.UUID,
        deadline_candidate_index: int,
        event_type: EventType,
        confirmed_date: date,
        source_type: SourceType,
        confirmation_method: ConfirmationMethod,
        candidate_id: uuid.UUID | None = None,
        evidence_note: str = "",
        confirmed_by: str = "",
        redirect_path: str = "",
    ) -> ConfirmationActionResult:
        """Execute confirm with idempotency protection.

        Single atomic transaction: claim + domain mutation + complete.
        Payload digest binds operation details (including manual date) to
        the idempotency key. Replay with different payload returns 409.
        """
        key_digest = self._hash_key(idempotency_key)

        payload = {
            "op": "confirm",
            "did": str(document_id),
            "dci": deadline_candidate_index,
            "et": event_type.value,
            "cd": confirmed_date.isoformat(),
            "st": source_type.value,
            "cm": confirmation_method.value,
            "cid": str(candidate_id) if candidate_id else None,
            "en": evidence_note,
            "cb": confirmed_by,
        }
        payload_digest = self.compute_payload_digest(payload)

        repo = self._repo

        def _mutation(conn: object, active: object | None) -> ConfirmedReferenceEvent:
            now = datetime.now(UTC)
            confirmation_id = uuid.uuid4()
            event = ConfirmedReferenceEvent(
                confirmation_id=confirmation_id,
                document_id=document_id,
                deadline_candidate_index=deadline_candidate_index,
                event_type=event_type,
                confirmed_date=confirmed_date,
                source_type=source_type,
                confirmation_method=confirmation_method,
                confirmed_at=now,
                candidate_id=candidate_id,
                evidence_note=evidence_note,
                confirmed_by=confirmed_by,
                supersedes_confirmation_id=(
                    active.confirmation_id
                    if active and hasattr(active, "confirmation_id")
                    else None
                ),
            )
            repo.save_confirmation_in_conn(conn, event)
            return event

        try:
            event, was_replay = self._repo.execute_atomic_with_idempotency(
                idempotency_key=key_digest,
                operation_type="confirm",
                payload_digest=payload_digest,
                document_id=document_id,
                deadline_candidate_index=deadline_candidate_index,
                perform_mutation=_mutation,
            )
        except IdempotencyKeyConflictError:
            raise

        return ConfirmationActionResult(
            event=event,
            was_replay=was_replay,
            redirect_path=redirect_path,
            result_status="confirmed",
        )

    def reject_with_idempotency(
        self,
        idempotency_key: str,
        document_id: uuid.UUID,
        deadline_candidate_index: int,
        event_type: EventType,
        candidate_id: uuid.UUID | None = None,
        redirect_path: str = "",
    ) -> ConfirmationActionResult:
        """Execute reject with idempotency protection.

        Single atomic transaction: claim + domain mutation + complete.
        """
        key_digest = self._hash_key(idempotency_key)

        payload = {
            "op": "reject",
            "did": str(document_id),
            "dci": deadline_candidate_index,
            "et": event_type.value,
            "cid": str(candidate_id) if candidate_id else None,
        }
        payload_digest = self.compute_payload_digest(payload)

        repo = self._repo

        def _mutation(conn: object, active: object | None) -> ConfirmedReferenceEvent:
            now = datetime.now(UTC)
            rejection = ConfirmedReferenceEvent(
                confirmation_id=uuid.uuid4(),
                document_id=document_id,
                deadline_candidate_index=deadline_candidate_index,
                event_type=event_type,
                confirmed_at=now,
                confirmed_date=None,
                source_type=SourceType.AUTO_DETECTED,
                confirmation_method=ConfirmationMethod.AUTO_SUGGESTED,
                candidate_id=candidate_id,
                supersedes_confirmation_id=(
                    active.confirmation_id
                    if active and hasattr(active, "confirmation_id")
                    else None
                ),
            )
            repo.save_confirmation_in_conn(conn, rejection)
            return rejection

        try:
            event, was_replay = self._repo.execute_atomic_with_idempotency(
                idempotency_key=key_digest,
                operation_type="reject",
                payload_digest=payload_digest,
                document_id=document_id,
                deadline_candidate_index=deadline_candidate_index,
                perform_mutation=_mutation,
            )
        except IdempotencyKeyConflictError:
            raise

        return ConfirmationActionResult(
            event=event,
            was_replay=was_replay,
            redirect_path=redirect_path,
            result_status="rejected",
        )

    def revoke(
        self,
        confirmation_id: uuid.UUID,
    ) -> ConfirmedReferenceEvent | None:
        """Revoke a previous confirmation. Creates a REVOKED record.

        The revocation record has confirmed_date=None to distinguish it
        structurally from CONFIRMED records. The is_revoke flag in the
        repository marks this as a revocation in the database.
        """
        existing = self._repo.get_confirmation(confirmation_id)
        if existing is None:
            return None

        now = datetime.now(UTC)
        revoked = ConfirmedReferenceEvent(
            confirmation_id=uuid.uuid4(),
            document_id=existing.document_id,
            deadline_candidate_index=existing.deadline_candidate_index,
            event_type=existing.event_type,
            confirmed_date=None,  # REVOKED: no confirmed date
            source_type=existing.source_type,
            confirmation_method=existing.confirmation_method,
            confirmed_at=now,
            candidate_id=existing.candidate_id,
            supersedes_confirmation_id=confirmation_id,
        )
        self._repo.save_confirmation(revoked, is_revoke=True)
        return revoked

    def get_history(
        self,
        document_id: uuid.UUID,
        deadline_candidate_index: int,
    ) -> list[ConfirmedReferenceEvent]:
        """Get confirmation history for a deadline candidate."""
        return self._repo.get_history_for_candidate(document_id, deadline_candidate_index)

    # ── Correct with idempotency (M6-UI Slice 3) ──────────────────

    def correct_with_idempotency(
        self,
        idempotency_key: str,
        document_id: uuid.UUID,
        deadline_candidate_index: int,
        event_type: EventType,
        confirmed_date: date,
        expected_active_confirmation_id: str,
        evidence_note: str = "",
        redirect_path: str = "",
    ) -> ConfirmationActionResult:
        """Execute correction (supersession) with idempotency protection.

        Correct creates a new CONFIRMED record that supersedes the current
        active confirmation. The previous record becomes SUPERSEDED.

        Expected-state binding: the ``expected_active_confirmation_id``
        must match the current active confirmation. Stale forms → 409.
        """
        key_digest = self._hash_key(idempotency_key)

        payload = {
            "op": "correct",
            "did": str(document_id),
            "dci": deadline_candidate_index,
            "et": event_type.value,
            "cd": confirmed_date.isoformat(),
            "eac": expected_active_confirmation_id,
            "en": evidence_note,
        }
        payload_digest = self.compute_payload_digest(payload)

        repo = self._repo
        eac_uuid = uuid.UUID(expected_active_confirmation_id)

        def _mutation(conn: object, active: object | None) -> ConfirmedReferenceEvent:
            # Verify expected state — stale forms must fail
            if active is None:
                raise ValueError("Keine aktive Bestätigung zum Korrigieren vorhanden.")
            if not hasattr(active, "confirmation_id") or active.confirmation_id != eac_uuid:
                raise ValueError("Der Stand wurde inzwischen geändert.")

            now = datetime.now(UTC)
            confirmation_id = uuid.uuid4()
            event = ConfirmedReferenceEvent(
                confirmation_id=confirmation_id,
                document_id=document_id,
                deadline_candidate_index=deadline_candidate_index,
                event_type=event_type,
                confirmed_date=confirmed_date,
                source_type=SourceType.USER_CORRECTED,
                confirmation_method=ConfirmationMethod.CORRECTED,
                confirmed_at=now,
                candidate_id=active.candidate_id if hasattr(active, "candidate_id") else None,
                evidence_note=evidence_note,
                supersedes_confirmation_id=active.confirmation_id,
            )
            repo.save_confirmation_in_conn(conn, event)
            return event

        try:
            event, was_replay = self._repo.execute_atomic_with_idempotency(
                idempotency_key=key_digest,
                operation_type="correct",
                payload_digest=payload_digest,
                document_id=document_id,
                deadline_candidate_index=deadline_candidate_index,
                perform_mutation=_mutation,
            )
        except IdempotencyKeyConflictError:
            raise

        return ConfirmationActionResult(
            event=event,
            was_replay=was_replay,
            redirect_path=redirect_path,
            result_status="confirmed",
        )

    # ── Revoke with idempotency (M6-UI Slice 3) ───────────────────

    def revoke_with_idempotency(
        self,
        idempotency_key: str,
        document_id: uuid.UUID,
        deadline_candidate_index: int,
        event_type: EventType,
        expected_active_confirmation_id: str,
        redirect_path: str = "",
    ) -> ConfirmationActionResult:
        """Execute revocation with idempotency protection.

        Revoke creates a REVOKED record that supersedes the current
        active confirmation. The previous record becomes SUPERSEDED.
        The REVOKED record has confirmed_date=NULL and is_revoke=1.

        Expected-state binding: the ``expected_active_confirmation_id``
        must match the current active confirmation. Stale forms → 409.
        """
        key_digest = self._hash_key(idempotency_key)

        payload = {
            "op": "revoke",
            "did": str(document_id),
            "dci": deadline_candidate_index,
            "et": event_type.value,
            "eac": expected_active_confirmation_id,
        }
        payload_digest = self.compute_payload_digest(payload)

        repo = self._repo
        eac_uuid = uuid.UUID(expected_active_confirmation_id)

        def _mutation(conn: object, active: object | None) -> ConfirmedReferenceEvent:
            # Verify expected state
            if active is None:
                raise ValueError("Keine aktive Bestätigung zum Widerrufen vorhanden.")
            if not hasattr(active, "confirmation_id") or active.confirmation_id != eac_uuid:
                raise ValueError("Der Stand wurde inzwischen geändert.")

            now = datetime.now(UTC)
            revoked = ConfirmedReferenceEvent(
                confirmation_id=uuid.uuid4(),
                document_id=document_id,
                deadline_candidate_index=deadline_candidate_index,
                event_type=event_type,
                confirmed_date=None,  # REVOKED: no date
                source_type=active.source_type
                if hasattr(active, "source_type")
                else SourceType.AUTO_DETECTED,
                confirmation_method=active.confirmation_method
                if hasattr(active, "confirmation_method")
                else ConfirmationMethod.AUTO_SUGGESTED,
                confirmed_at=now,
                candidate_id=active.candidate_id if hasattr(active, "candidate_id") else None,
                supersedes_confirmation_id=active.confirmation_id,
            )
            repo.save_confirmation_in_conn(conn, revoked, is_revoke=True)
            return revoked

        try:
            event, was_replay = self._repo.execute_atomic_with_idempotency(
                idempotency_key=key_digest,
                operation_type="revoke",
                payload_digest=payload_digest,
                document_id=document_id,
                deadline_candidate_index=deadline_candidate_index,
                perform_mutation=_mutation,
            )
        except IdempotencyKeyConflictError:
            raise

        return ConfirmationActionResult(
            event=event,
            was_replay=was_replay,
            redirect_path=redirect_path,
            result_status="revoked",
        )

    def cleanup_idempotency(self) -> int:
        """Delete expired idempotency records."""
        return self._repo.cleanup_expired_idempotency_records()

    def _detect_candidates(
        self,
        document_id: uuid.UUID,
        deadline_candidate_index: int,
    ) -> list[ReferenceEventCandidate]:
        """Detect reference event candidates from document text.

        Placeholder for M6-B implementation.
        """
        return []
