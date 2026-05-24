import uuid
from datetime import datetime, timezone

from sqlmodel import Field, Relationship, SQLModel, Column, JSON


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    github_id: int = Field(unique=True, index=True)
    username: str

    repositories: list["Repository"] = Relationship(back_populates="owner")


class Repository(SQLModel, table=True):
    __tablename__ = "repositories"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    github_repo_id: int = Field(unique=True, index=True)
    owner_id: uuid.UUID = Field(foreign_key="users.id")
    name: str
    full_name: str
    html_url: str
    structure_map: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))

    owner: User = Relationship(back_populates="repositories")
    analysis_results: list["AnalysisResult"] = Relationship(back_populates="repository")


class AnalysisResult(SQLModel, table=True):
    __tablename__ = "analysis_results"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    repo_id: uuid.UUID = Field(foreign_key="repositories.id")
    health_score: int
    issues: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    pending_fix_url: str | None = None
    draft_proposal: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    status: str = Field(default="idle")  # idle | drafting_docs | review_ready
    last_analyzed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_gardener_run_at: datetime | None = Field(default=None)

    repository: Repository = Relationship(back_populates="analysis_results")


class IdempotencyKey(SQLModel, table=True):
    """E5 — dedup window for mutating endpoints.

    Composite PK on (token_fingerprint, key, endpoint) so two users sharing
    the same key value, OR one user using the same key across endpoints, all
    get distinct rows. The 24h dedup window is enforced at query time via
    ``created_at`` (see ``app/services/idempotency.py``).
    """

    __tablename__ = "idempotency_keys"

    token_fingerprint: str = Field(primary_key=True, max_length=64)
    key: str = Field(primary_key=True, max_length=128)
    endpoint: str = Field(primary_key=True, max_length=128)
    workflow_id: str = Field(max_length=256)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        index=True,
    )
