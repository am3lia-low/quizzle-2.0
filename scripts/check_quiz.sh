#!/usr/bin/env bash
# Run every automatic check on one quiz: validate -> simulate -> build -> playtest.
# Usage: scripts/check_quiz.sh 2026-W42
set -euo pipefail
week="${1:?usage: scripts/check_quiz.sh WEEK}"
cd "$(dirname "$0")/.."
echo "== validate";  python3 scripts/validate.py "$week"
echo "== simulate";  python3 scripts/simulate.py "$week"
echo "== build";     python3 scripts/build.py --out .work/site --clean
echo "== playtest";  NODE_PATH="${NODE_PATH:-$(npm root -g)}" node scripts/playtest.mjs "$week" ".work/site/$week.html"
echo "ALL CHECKS PASSED for $week"
