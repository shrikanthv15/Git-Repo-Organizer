from datetime import datetime

from pydantic import BaseModel


class RepoHealth(BaseModel):
    repo_name: str
    health_score: int
    issues: list[str]
    last_commit_date: datetime
    pending_fix_url: str | None = None


class BatchInput(BaseModel):
    access_token: str
    limit: int = 5


class BatchStatus(BaseModel):
    total: int
    completed: int
    results: list[RepoHealth]
