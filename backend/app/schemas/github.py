from pydantic import BaseModel


class Repo(BaseModel):
    id: int
    name: str
    full_name: str
    private: bool
    html_url: str
    description: str | None = None


class AuthExchangeRequest(BaseModel):
    code: str
