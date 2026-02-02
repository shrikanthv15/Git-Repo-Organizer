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
    last_analyzed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    repository: Repository = Relationship(back_populates="analysis_results")
