# Weekly Personality Quiz

A Claude Code agent writes a new personality quiz every week. You review it as a pull request,
play the preview, and merge to publish it on GitHub Pages.

Site: https://am3lia-low.github.io/quizzle-2.0/

## How a week works

1. A weekly **Routine** (scheduled Claude Code cloud session) runs the `weekly-quiz` skill.
2. The agent takes the next topic from `topics.json`, writes `quizzes/<week>/quiz.json` (questions, outcomes,
   scoring) and `quizzes/<week>/style.css` (that quiz's theme).
3. It runs the checks (`scripts/check_quiz.sh <week>`), gets a second opinion from a critic subagent,
   writes `reports/<week>.md`, and opens a PR titled `Quiz <week>: <topic>`.
4. The PR triggers a preview at https://am3lia-low.github.io/quizzle-2.0/preview/
5. You get an email when the run finishes. Play the preview, read the report, then merge (publish) or
   close (reject; the topic goes back in the queue).

## Layout

| Path | What | Who edits it |
|---|---|---|
| `quizzes/<week>/quiz.json` | Quiz content and colours | Agent |
| `quizzes/<week>/style.css` | Quiz theme | Agent |
| `reports/<week>.md` | Review report: outcomes, every question, outcome split | Agent (via `report.py`) |
| `topics.json` | Upcoming topics, one used per week | Agent removes one; you refill it |
| `engine/` | Quiz engine (`engine.js`), page shell, main page template | You |
| `scripts/` | Checks, simulation, build, playtest, scope guard | You |
| `.github/workflows/` | Deploy on merge, preview on PR | You |
| `.claude/skills/weekly-quiz/` | The agent's playbook | You |
| `docs/example-quiz/` | Reference quiz (format example, used for testing) | You |

The agent may only change its week's quiz files, its report and `topics.json`. `check_scope.py` enforces this.

## The checks

| Script | Checks |
|---|---|
| `validate.py` | Schema, 5–12 questions, 2–10 outcomes, text lengths, colour contrast, safe CSS |
| `simulate.py` | 10,000 random playthroughs → outcome split; every outcome must be reachable |
| `build.py` | Builds one self-contained HTML file per quiz plus the main page into `_site/` |
| `playtest.mjs` | Headless browser plays the built page to every outcome and replays random paths |
| `report.py` | Writes the report from the simulation output (numbers are never typed by hand) |
| `check_scope.py` | Fails if anything outside this week's files changed |

Try it locally with the example quiz:

```sh
mkdir -p quizzes/2026-W41 && cp docs/example-quiz/* quizzes/2026-W41/
scripts/check_quiz.sh 2026-W41      # needs Python 3 and Node with Playwright
open .work/site/2026-W41.html       # single file, works straight from disk
rm -rf quizzes/2026-W41 .work       # clean up
```

## One-time setup

1. Merge this into `main`.
2. Repo **Settings → Pages → Build and deployment → Source: GitHub Actions**.
3. Create the weekly Routine in Claude Code (prompt: `Run the weekly-quiz skill.`), with email notifications on.

## Re-running a week

Open the Routine and press **Run now**, or ask Claude in any session, e.g. "run the weekly quiz Routine for
week 2026-W43" or "…and skip this topic". The run stops on its own if that week is already published or
already has an open PR.
