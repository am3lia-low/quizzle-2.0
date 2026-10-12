"""Guardrail: fail if the agent changed anything outside one quiz's files.

Usage: python3 scripts/check_scope.py 2026-W42 [--base origin/main]   (or 2026-W42-2, ...)
Looks at committed, staged, unstaged and untracked changes compared with the base.
"""

import argparse
import subprocess
import sys

import quizlib


def git(*args: str) -> list[str]:
    out = subprocess.run(["git", *args], cwd=quizlib.ROOT, check=True, capture_output=True, text=True).stdout
    return [line for line in out.splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("quiz_id")
    parser.add_argument("--base", default="origin/main")
    args = parser.parse_args()
    week = args.quiz_id
    if not quizlib.QUIZ_ID_RE.match(week):
        print(f"bad quiz id: {week}")
        return 2

    changed = set(git("diff", "--name-only", f"{args.base}...HEAD"))
    changed |= set(git("diff", "--name-only", "HEAD"))
    changed |= set(git("ls-files", "--others", "--exclude-standard"))

    # topics.json is left alone: used topics are found from quizzes/*/quiz.json and open PR titles,
    # so two quiz PRs open at once never conflict over it.
    allowed = {f"quizzes/{week}/quiz.json", f"quizzes/{week}/style.css", f"reports/{week}.md"}
    required = allowed

    outside = sorted(changed - allowed)
    missing = sorted(required - changed)
    for path in outside:
        print(f"not allowed to change: {path}")
    for path in missing:
        print(f"expected a change to: {path}")
    if outside or missing:
        print("FAIL: scope check")
        return 1
    print(f"OK: only {week}'s files changed ({len(changed)} file(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
