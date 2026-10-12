#!/usr/bin/env bash
# Add a preview page for every open quiz PR to an already-built site.
# Usage: scripts/build_pr_previews.sh OUT_DIR [LAST_PR_NUMBER]
#
# Each quiz gets OUT_DIR/preview/<quiz-id>/; OUT_DIR/preview/ shows LAST_PR_NUMBER's quiz
# (the PR that triggered the run), or the newest PR's when none is given.
# From each PR it takes nothing but quizzes/<id>/quiz.json and style.css, which build.py
# validates before using. PRs from forks are skipped. Needs GH_TOKEN and the gh CLI.
# A quiz that fails to build is reported and skipped, so one bad PR can't hide the others;
# the script still fails if LAST_PR_NUMBER's own quiz didn't build.
set -euo pipefail
out="${1:?usage: scripts/build_pr_previews.sh OUT_DIR [LAST_PR_NUMBER]}"
last="${2:-}"
cd "$(dirname "$0")/.."

id_re='^quizzes/([0-9]{4}-W[0-9]{2}(-[2-9])?)/quiz\.json$'
prs=$(gh pr list --state open --limit 100 --json number,headRefOid,isCrossRepository,files \
  --jq '.[] | select(.isCrossRepository | not) | "\(.number) \(.headRefOid) \([.files[].path] | join(","))"' \
  | sort -n)
# Build the triggering PR last so it ends up at preview/.
if [ -n "$last" ]; then
  prs=$(printf '%s\n' "$prs" | awk -v n="$last" '$1 != n'; printf '%s\n' "$prs" | awk -v n="$last" '$1 == n')
fi

built=0
last_failed=0
while read -r number sha files; do
  [ -n "${number:-}" ] || continue
  ids=$(tr ',' '\n' <<<"$files" | sed -nE "s#$id_re#\1#p" | sort -u)
  [ -n "$ids" ] || continue
  if ! git fetch --quiet --no-tags --depth=1 origin "$sha"; then
    echo "::warning::PR #$number: could not fetch $sha"
    [ "$number" != "$last" ] || last_failed=1
    continue
  fi
  for id in $ids; do
    mkdir -p "quizzes/$id"
    if git show "$sha:quizzes/$id/quiz.json" > "quizzes/$id/quiz.json" \
      && git show "$sha:quizzes/$id/style.css" > "quizzes/$id/style.css" \
      && python3 scripts/build.py --out "$out" --preview "$id"; then
      echo "- PR #$number: \`preview/$id/\`" >> "${GITHUB_STEP_SUMMARY:-/dev/null}"
      built=$((built + 1))
    else
      echo "::warning::PR #$number: could not build a preview of $id"
      [ "$number" != "$last" ] || last_failed=1
    fi
  done
done <<<"$prs"
echo "built $built preview page(s)"
if [ "$last_failed" = 1 ]; then echo "FAIL: PR #$last's preview did not build"; exit 1; fi
