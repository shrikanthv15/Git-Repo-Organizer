"""
GitHub Gardener — System Health Check
Run: python scripts/system_check.py
"""

import subprocess
import sys
import urllib.request
import urllib.error

CHECKS = {
    "Backend API": "http://localhost:8000/api/health",
    "Temporal UI": "http://localhost:8233",
}

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"


def check_http(name: str, url: str) -> bool:
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            status = resp.status
        if 200 <= status < 400:
            print(f"  {GREEN}[PASS]{RESET} {name} ({url}) — HTTP {status}")
            return True
        print(f"  {RED}[FAIL]{RESET} {name} ({url}) — HTTP {status}")
        return False
    except urllib.error.URLError as exc:
        print(f"  {RED}[FAIL]{RESET} {name} ({url}) — {exc.reason}")
        return False
    except Exception as exc:
        print(f"  {RED}[FAIL]{RESET} {name} ({url}) — {exc}")
        return False


def check_worker_container() -> bool:
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=worker", "--filter", "status=running", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        containers = [line.strip() for line in result.stdout.strip().splitlines() if line.strip()]
        if containers:
            print(f"  {GREEN}[PASS]{RESET} Worker container — running ({', '.join(containers)})")
            return True
        print(f"  {RED}[FAIL]{RESET} Worker container — not running")
        return False
    except FileNotFoundError:
        print(f"  {YELLOW}[SKIP]{RESET} Worker container — docker CLI not found")
        return False
    except Exception as exc:
        print(f"  {RED}[FAIL]{RESET} Worker container — {exc}")
        return False


def main() -> None:
    print(f"\n{BOLD}=== GitHub Gardener System Check ==={RESET}\n")

    results: list[bool] = []

    for name, url in CHECKS.items():
        results.append(check_http(name, url))

    results.append(check_worker_container())

    print()
    if all(results):
        print(f"  {GREEN}{BOLD}{'=' * 40}{RESET}")
        print(f"  {GREEN}{BOLD}       SYSTEM ONLINE{RESET}")
        print(f"  {GREEN}{BOLD}{'=' * 40}{RESET}")
    else:
        passed = sum(results)
        total = len(results)
        print(f"  {RED}{BOLD}SYSTEM DEGRADED — {passed}/{total} checks passed{RESET}")

    print()
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
