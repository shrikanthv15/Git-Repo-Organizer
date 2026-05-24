import json
import structlog
from io import StringIO
import pytest
from app.temporal.middleware import temporal_activity_context


def test_workflow_logs_structured():
    """Capture and parse JSON logs from a test activity."""
    output = StringIO()
    
    # Temporarily configure structlog to write to our StringIO
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=lambda: structlog.PrintLogger(file=output),
        cache_logger_on_first_use=False,
    )
    
    # Run activity with bound context
    with temporal_activity_context("wf-123", "test_activity", repo_id=456, user_id="gh-test"):
        structlog.get_logger().info("test_event", data="value")
    
    log_line = output.getvalue().strip()
    assert log_line, "No log output captured"
    
    log_obj = json.loads(log_line)
    
    assert log_obj["workflow_id"] == "wf-123"
    assert log_obj["activity_name"] == "test_activity"
    assert log_obj["repo_id"] == 456
    assert log_obj["user_id"] == "gh-test"
    assert log_obj["event"] == "test_event"
    assert log_obj["data"] == "value"


def test_temporal_context_clears():
    """Ensure context is properly cleared after the context manager exits."""
    output = StringIO()
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=lambda: structlog.PrintLogger(file=output),
        cache_logger_on_first_use=False,
    )
    
    # Log inside context
    with temporal_activity_context("wf-456", "test_activity2", repo_id=789):
        structlog.get_logger().info("inside_context", status="running")
    
    # Log after context (should not have workflow_id)
    output.truncate(0)
    output.seek(0)
    structlog.get_logger().info("outside_context", status="done")
    
    log_line = output.getvalue().strip()
    assert log_line
    log_obj = json.loads(log_line)
    
    # Should not have workflow context
    assert "workflow_id" not in log_obj
    assert log_obj["event"] == "outside_context"
