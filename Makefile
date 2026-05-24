# Convenience targets for running the test suite from the repo root.
# These mirror what .github/workflows/test.yml runs in CI so a passing
# `make test` locally is a strong signal CI will also pass.

.PHONY: help test test-backend test-frontend test-cov build typecheck

help:
	@echo "Targets:"
	@echo "  make test           Run backend + frontend tests"
	@echo "  make test-backend   Backend pytest (with coverage report)"
	@echo "  make test-frontend  Frontend vitest"
	@echo "  make test-cov       Backend pytest + 60% coverage gate"
	@echo "  make build          Frontend production build (pnpm)"
	@echo "  make typecheck      Frontend tsc --noEmit"

test: test-backend test-frontend

test-backend:
	uv --project backend run pytest --cov-report=term

test-frontend:
	cd frontend && pnpm test

test-cov:
	uv --project backend run pytest --cov-fail-under=60 --cov-report=term-missing

build:
	cd frontend && pnpm build

typecheck:
	cd frontend && pnpm typecheck
