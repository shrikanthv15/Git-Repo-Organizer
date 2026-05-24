from contextlib import contextmanager
import structlog


@contextmanager
def temporal_activity_context(workflow_id: str, activity_name: str, repo_id: int = None, user_id: str = None):
    """Bind Temporal context to all logs emitted within this scope."""
    structlog.contextvars.bind_contextvars(
        workflow_id=workflow_id,
        activity_name=activity_name,
        repo_id=repo_id,
        user_id=user_id,
    )
    try:
        yield
    finally:
        structlog.contextvars.clear_contextvars()
