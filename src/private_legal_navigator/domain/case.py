"""Domain model for a legal/administrative Case."""

import uuid
from datetime import UTC, datetime
from enum import StrEnum


class CaseStatus(StrEnum):
    """The status of a case.

    In M1, only 'open' is used. Future milestones will add more statuses.
    """

    OPEN = "open"


class Case:
    """A case representing a legal or administrative matter.

    Invariants:
        - case_id is a server-generated UUIDv4, immutable after creation
        - title is trimmed and must be 1-200 characters
        - status defaults to OPEN
        - created_at and updated_at are timezone-aware UTC
    """

    MAX_TITLE_LENGTH = 200

    def __init__(
        self,
        title: str,
        *,
        case_id: uuid.UUID | None = None,
        status: CaseStatus | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        self._validate_title(title)

        now = datetime.now(UTC)
        self.case_id = case_id or uuid.uuid4()
        self.title = title.strip()
        self.status = status or CaseStatus.OPEN
        self.created_at = created_at or now
        self.updated_at = updated_at or now

    @staticmethod
    def _validate_title(title: str) -> None:
        """Validate the title according to domain rules."""
        if not title or not title.strip():
            raise ValueError("Titel darf nicht leer sein")
        if len(title) > Case.MAX_TITLE_LENGTH:
            raise ValueError(
                f"Titel darf maximal {Case.MAX_TITLE_LENGTH} Zeichen haben"
            )
