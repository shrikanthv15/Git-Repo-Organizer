"""E5 guardrails — Idempotency-Key support for mutating endpoints.

Surface:
    * :func:`fingerprint_token` — stable per-token identifier (sha256[:32]).
    * :func:`lookup_idempotency_key` — given (key, token, endpoint), return the
      previously-issued workflow_id if one was recorded within the 24h
      dedup window; otherwise None.
    * :func:`record_idempotency_key` — persist the (key, token, endpoint) →
      workflow_id mapping. Idempotent (won't error on duplicate insert).
    * :func:`get_idempotency_key` — FastAPI dependency reading the
      ``Idempotency-Key`` request header.

The raw GitHub access token is never persisted — only a sha256 truncated
to 32 chars is stored, so a DB leak doesn't expose tokens.
"""

import hashlib
from datetime import datetime, timedelta, timezone

import structlog
from fastapi import Header
from sqlmodel import Session, select

from app.db.models import IdempotencyKey

logger = structlog.get_logger(__name__)

# Dedup window — same (key, token, endpoint) within this duration returns
# the prior workflow_id instead of starting a new workflow.
DEDUP_WINDOW = timedelta(hours=24)


def fingerprint_token(token: str) -> str:
    """Stable per-token identifier suitable as a DB-safe namespace.

    sha256 truncated to 32 hex chars (= 128 bits of entropy). Two callers
    with the same token always map to the same fingerprint; tokens are
    never persisted in raw form.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:32]


def lookup_idempotency_key(
    session: Session,
    *,
    key: str,
    token: str,
    endpoint: str,
    window: timedelta = DEDUP_WINDOW,
) -> str | None:
    """Return the cached workflow_id if (key, token, endpoint) was seen within ``window``.

    Returns None if no entry exists OR the entry is older than the window.
    """
    fp = fingerprint_token(token)
    cutoff = datetime.now(timezone.utc) - window
    stmt = select(IdempotencyKey).where(
        IdempotencyKey.token_fingerprint == fp,
        IdempotencyKey.key == key,
        IdempotencyKey.endpoint == endpoint,
        IdempotencyKey.created_at >= cutoff,
    )
    row = session.exec(stmt).first()
    if row:
        # SQLite drops tzinfo on round-trip; assume UTC for naive values
        # so the age subtraction below doesn't blow up under sqlite test DBs.
        created_at = row.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        logger.info(
            "idempotency_hit",
            endpoint=endpoint,
            key=key,
            workflow_id=row.workflow_id,
            age_seconds=int((datetime.now(timezone.utc) - created_at).total_seconds()),
        )
        return row.workflow_id
    return None


def record_idempotency_key(
    session: Session,
    *,
    key: str,
    token: str,
    endpoint: str,
    workflow_id: str,
) -> None:
    """Persist the (key, token, endpoint) → workflow_id mapping.

    No-ops cleanly if a row already exists (race-window safety). Caller
    should ``session.commit()``.
    """
    fp = fingerprint_token(token)
    # Use a query rather than session.get() with a tuple PK — SQLAlchemy's
    # composite-PK identity-key handling is awkward across versions; a
    # plain select is portable.
    existing = session.exec(select(IdempotencyKey).where(
        IdempotencyKey.token_fingerprint == fp,
        IdempotencyKey.key == key,
        IdempotencyKey.endpoint == endpoint,
    )).first()
    if existing is not None:
        # Race: another concurrent request already inserted. Leave existing.
        return
    row = IdempotencyKey(
        token_fingerprint=fp,
        key=key,
        endpoint=endpoint,
        workflow_id=workflow_id,
        created_at=datetime.now(timezone.utc),
    )
    session.add(row)
    logger.info("idempotency_recorded", endpoint=endpoint, key=key, workflow_id=workflow_id)


# FastAPI dependency — pulls Idempotency-Key from headers (case-insensitive).
async def get_idempotency_key(
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> str | None:
    """Return the request's ``Idempotency-Key`` header or None."""
    if idempotency_key is not None:
        idempotency_key = idempotency_key.strip()
        if not idempotency_key:
            return None
        if len(idempotency_key) > 128:
            # Header too long for our schema — treat as absent rather than
            # silently truncating. Caller can shorten + retry.
            logger.warning("idempotency_key_too_long", length=len(idempotency_key))
            return None
    return idempotency_key
