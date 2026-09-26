#!/bin/bash
# Run Playwright E2E tests. Usage: ./run-tests.sh [tests/auth] [--ui]
# Sets up user-space Chromium libraries (no sudo needed on agents-01).
export LD_LIBRARY_PATH="/home/hermes/playwright-deps/usr/lib/aarch64-linux-gnu:${LD_LIBRARY_PATH}"
export PATH="/home/hermes/.hermes/node/bin:${PATH}"
cd "$(dirname "$0")"
exec npx playwright test "$@"
