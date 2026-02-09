from datetime import datetime, timezone

from sqlmodel import Session, select

from app.db.models import AnalysisResult, Repository, User

# Valid analysis result statuses
STATUS_IDLE = "idle"
STATUS_DRAFTING = "drafting_docs"
STATUS_REVIEW_READY = "review_ready"


def upsert_user(session: Session, *, github_id: int, username: str) -> User:
    user = session.exec(select(User).where(User.github_id == github_id)).first()
    if user:
        user.username = username
    else:
        user = User(github_id=github_id, username=username)
        session.add(user)
    session.flush()
    return user


def upsert_repository(
    session: Session,
    *,
    github_repo_id: int,
    owner_id,
    name: str,
    full_name: str,
    html_url: str,
) -> Repository:
    repo = session.exec(
        select(Repository).where(Repository.github_repo_id == github_repo_id)
    ).first()
    if repo:
        repo.owner_id = owner_id
        repo.name = name
        repo.full_name = full_name
        repo.html_url = html_url
    else:
        repo = Repository(
            github_repo_id=github_repo_id,
            owner_id=owner_id,
            name=name,
            full_name=full_name,
            html_url=html_url,
        )
        session.add(repo)
    session.flush()
    return repo


def upsert_analysis_result(
    session: Session,
    *,
    repo_id,
    health_score: int,
    issues: list[str],
    pending_fix_url: str | None,
    last_gardener_run_at: datetime | None = None,
) -> AnalysisResult:
    result = session.exec(
        select(AnalysisResult).where(AnalysisResult.repo_id == repo_id)
    ).first()
    if result:
        result.health_score = health_score
        result.issues = issues
        result.pending_fix_url = pending_fix_url
        result.last_analyzed_at = datetime.now(timezone.utc)
        if last_gardener_run_at is not None:
            result.last_gardener_run_at = last_gardener_run_at
    else:
        result = AnalysisResult(
            repo_id=repo_id,
            health_score=health_score,
            issues=issues,
            pending_fix_url=pending_fix_url,
            last_gardener_run_at=last_gardener_run_at,
        )
        session.add(result)
    session.flush()
    return result


def update_structure_map(
    session: Session, *, github_repo_id: int, structure_map: dict
) -> Repository | None:
    repo = session.exec(
        select(Repository).where(Repository.github_repo_id == github_repo_id)
    ).first()
    if repo:
        repo.structure_map = structure_map
        session.flush()
    return repo


def save_draft_proposal(
    session: Session,
    *,
    github_repo_id: int,
    draft_proposal: dict | None,
) -> bool:
    """Save or clear a draft_proposal on the latest AnalysisResult for a repo."""
    repo = session.exec(
        select(Repository).where(Repository.github_repo_id == github_repo_id)
    ).first()
    if not repo:
        return False

    result = session.exec(
        select(AnalysisResult)
        .where(AnalysisResult.repo_id == repo.id)
        .order_by(AnalysisResult.last_analyzed_at.desc())
    ).first()
    if not result:
        return False

    result.draft_proposal = draft_proposal
    session.flush()
    return True


def get_draft_proposal(
    session: Session,
    *,
    github_repo_id: int,
) -> dict | None:
    """Fetch the draft_proposal for a repo, if any."""
    repo = session.exec(
        select(Repository).where(Repository.github_repo_id == github_repo_id)
    ).first()
    if not repo:
        return None

    result = session.exec(
        select(AnalysisResult)
        .where(AnalysisResult.repo_id == repo.id)
        .order_by(AnalysisResult.last_analyzed_at.desc())
    ).first()
    if not result:
        return None

    return result.draft_proposal


def set_repo_status(
    session: Session, *, github_repo_id: int, status: str
) -> bool:
    """Update the status field on the latest AnalysisResult for a repo."""
    repo = session.exec(
        select(Repository).where(Repository.github_repo_id == github_repo_id)
    ).first()
    if not repo:
        return False
    result = session.exec(
        select(AnalysisResult)
        .where(AnalysisResult.repo_id == repo.id)
        .order_by(AnalysisResult.last_analyzed_at.desc())
    ).first()
    if not result:
        return False
    result.status = status
    session.flush()
    return True


def get_repos_with_pending_pr(session: Session) -> list[tuple[str, str]]:
    """Return (full_name, pending_fix_url) for all repos with an open PR tracked."""
    stmt = (
        select(Repository.full_name, AnalysisResult.pending_fix_url)
        .join(AnalysisResult, AnalysisResult.repo_id == Repository.id)
        .where(AnalysisResult.pending_fix_url.isnot(None))
        .where(AnalysisResult.pending_fix_url != "")
    )
    rows = session.exec(stmt).all()
    return [(full_name, url) for full_name, url in rows]


def clear_pending_fix_for_repo(session: Session, *, repo_full_name: str) -> bool:
    """Clear pending_fix_url on all analysis results for a repo by full_name."""
    repo = session.exec(
        select(Repository).where(Repository.full_name == repo_full_name)
    ).first()
    if not repo:
        return False

    results = session.exec(
        select(AnalysisResult)
        .where(AnalysisResult.repo_id == repo.id)
        .where(AnalysisResult.pending_fix_url.isnot(None))
    ).all()
    for result in results:
        result.pending_fix_url = None
    session.flush()
    return len(results) > 0


def get_latest_analysis_for_repos(
    session: Session, github_repo_ids: list[int]
) -> dict[int, AnalysisResult]:
    """Return a mapping of github_repo_id -> latest AnalysisResult for given repo IDs."""
    if not github_repo_ids:
        return {}

    stmt = (
        select(Repository.github_repo_id, AnalysisResult)
        .join(AnalysisResult, AnalysisResult.repo_id == Repository.id)
        .where(Repository.github_repo_id.in_(github_repo_ids))
    )
    rows = session.exec(stmt).all()

    best: dict[int, AnalysisResult] = {}
    for github_repo_id, analysis in rows:
        existing = best.get(github_repo_id)
        if existing is None or analysis.last_analyzed_at > existing.last_analyzed_at:
            best[github_repo_id] = analysis

    return best
