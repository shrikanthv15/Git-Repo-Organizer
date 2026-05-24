"""E5 — LLM cost cap + max-tokens enforcement.

Covers:
- Cheap prompt passes
- Oversized input prompt is rejected (LLMCostExceededError) with the
  expected fields populated
- Estimated cost over budget is rejected
- _safe_acompletion injects max_tokens
- The FastAPI handler converts LLMCostExceededError to 400
"""
from unittest.mock import AsyncMock, patch

import pytest

from app.core.config import settings
from app.services.llm_service import (
    LLMCostExceededError,
    _check_llm_budget,
    _count_message_tokens,
    _estimate_cost,
    _safe_acompletion,
)


SHORT_MESSAGES = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello."},
]


class TestTokenCounting:
    def test_short_prompt_is_small(self):
        assert _count_message_tokens(SHORT_MESSAGES, "gpt-4o-mini") < 50

    def test_unknown_model_falls_back_to_cl100k(self):
        # Should not raise even for a model name tiktoken doesn't recognize
        n = _count_message_tokens(SHORT_MESSAGES, "made-up-model")
        assert n > 0

    def test_multipart_content_counts_text_parts(self):
        messages = [{"role": "user", "content": [
            {"type": "text", "text": "describe this image"},
            {"type": "image_url", "image_url": {"url": "https://x"}},
        ]}]
        n = _count_message_tokens(messages, "gpt-4o-mini")
        assert n > 0  # only the text part counts


class TestEstimateCost:
    def test_known_model_uses_table_price(self):
        # gpt-4o-mini: (0.00015 input, 0.00060 output) per 1k
        cost = _estimate_cost(prompt_tokens=1000, max_output_tokens=1000, model="gpt-4o-mini")
        assert cost == pytest.approx(0.00015 + 0.00060, rel=1e-6)

    def test_unknown_model_uses_default(self):
        cost_known = _estimate_cost(1000, 1000, "gpt-4o-mini")
        cost_unknown = _estimate_cost(1000, 1000, "made-up")
        # default price is more conservative (higher) than gpt-4o-mini
        assert cost_unknown > cost_known


class TestBudgetCheck:
    def test_small_prompt_passes(self):
        # Should not raise
        tokens = _check_llm_budget(SHORT_MESSAGES, "gpt-4o-mini")
        assert tokens > 0

    def test_huge_prompt_rejected(self, monkeypatch):
        monkeypatch.setattr(settings, "LLM_MAX_TOKENS_PER_REQUEST", 100)
        huge = [{"role": "user", "content": "word " * 5000}]  # ~5000 tokens
        with pytest.raises(LLMCostExceededError) as exc_info:
            _check_llm_budget(huge, "gpt-4o-mini")
        err = exc_info.value
        assert err.prompt_tokens > 100
        assert "exceeds LLM_MAX_TOKENS_PER_REQUEST" in str(err)

    def test_expensive_model_over_budget_rejected(self, monkeypatch):
        # Use the most expensive entry in our price table with a tight budget
        monkeypatch.setattr(settings, "LLM_MAX_COST_PER_REQUEST_USD", 0.001)
        monkeypatch.setattr(settings, "LLM_MAX_TOKENS_PER_REQUEST", 4000)
        with pytest.raises(LLMCostExceededError) as exc_info:
            _check_llm_budget(SHORT_MESSAGES, "claude-opus-4.7")
        assert exc_info.value.estimated_cost > exc_info.value.max_cost


@pytest.mark.asyncio
class TestSafeAcompletion:
    async def test_injects_max_tokens(self):
        captured: dict = {}

        async def fake_acompletion(**kwargs):
            captured.update(kwargs)
            return type("R", (), {"choices": [type("C", (), {"message": type("M", (), {"content": "ok"})})], "usage": type("U", (), {"prompt_tokens": 5, "completion_tokens": 3})()})()

        with patch("app.services.llm_service.acompletion", fake_acompletion):
            await _safe_acompletion(
                model="gpt-4o-mini",
                messages=SHORT_MESSAGES,
            )
        assert captured["max_tokens"] == settings.LLM_MAX_TOKENS_PER_REQUEST

    async def test_does_not_override_explicit_max_tokens(self):
        captured: dict = {}

        async def fake_acompletion(**kwargs):
            captured.update(kwargs)
            return type("R", (), {"choices": [], "usage": None})()

        with patch("app.services.llm_service.acompletion", fake_acompletion):
            await _safe_acompletion(
                model="gpt-4o-mini",
                messages=SHORT_MESSAGES,
                max_tokens=500,
            )
        assert captured["max_tokens"] == 500


class TestExceptionHandler:
    def test_handler_returns_400_with_structured_body(self):
        """The FastAPI exception handler converts LLMCostExceededError → 400."""
        from fastapi.testclient import TestClient
        from fastapi import APIRouter

        # We add a test-only route that raises the error to exercise the handler.
        from app.main import app

        test_router = APIRouter()

        @test_router.get("/_test_llm_cost")
        async def _raise():
            raise LLMCostExceededError(
                "budget exceeded for test",
                estimated_cost=1.23,
                max_cost=0.50,
                prompt_tokens=9999,
            )

        app.include_router(test_router)
        client = TestClient(app)
        resp = client.get("/_test_llm_cost")
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"] == "llm_cost_exceeded"
        assert body["estimated_cost_usd"] == 1.23
        assert body["max_cost_usd"] == 0.50
        assert body["prompt_tokens"] == 9999
