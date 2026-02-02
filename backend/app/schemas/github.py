from __future__ import annotations

from pydantic import BaseModel

from app.schemas.analysis import RepoHealth


class Repo(BaseModel):
    id: int
    name: str
    full_name: str
    private: bool
    html_url: str
    description: str | None = None
    health: RepoHealth | None = None
    draft_proposal: dict | None = None


class AuthExchangeRequest(BaseModel):
    code: str
