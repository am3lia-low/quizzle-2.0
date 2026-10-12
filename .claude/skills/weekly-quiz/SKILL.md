---
name: weekly-quiz
description: Generate this week's personality quiz (content + theme), check it, write the report and open a PR for review. Use when asked to run the weekly quiz, make a quiz (or several) for a given week, make an extra quiz this week, or redo a failed week.
---

# Weekly quiz

You are making personality quizzes for the site at `https://am3lia-low.github.io/quizzle-2.0/`.
Each quiz is its own pull request that a human reviews, plays and merges. Merging publishes it.

You only ever **write data**: a `quiz.json`, a `style.css` and a report per quiz, and the shortened topic list.
You never edit the engine, the scripts, the workflows or anything else. A scope check enforces this.

Work through the steps in order. If a step says **stop**, end the run with a short message saying why;
the person gets an email for every run, so a clear failure message is the whole error report.

## 1. Work out the week and how many quizzes

- Default: the current ISO week in Singapore time, `TZ=Asia/Singapore date +%G-W%V` (e.g. `2026-W42`).
  The Routine runs early Monday morning SGT, which is still Sunday in UTC, so don't use UTC here.
- If the request names a week (e.g. "do week 2026-W43"), use that instead.
- Call it `WEEK` below.
- `COUNT` = how many quizzes to make: 1 unless the request asks for more ("make 2 quizzes this week").
- `EXTRA` = yes if the request asks for quizzes *on top of* what the week already has ("make another quiz this
  week", "add a second quiz today"), or asks for more than one. Otherwise no.

## 2. Pick the quiz ID and make sure this isn't a duplicate run

A quiz ID is `WEEK` for the week's first quiz, then `WEEK-2`, `WEEK-3`, … up to `WEEK-9` for extra quizzes in the
same week (e.g. `2026-W42-2`). The ID names the folder, the report, the branch and the PR. Call it `ID` below.

- `git fetch origin main` and start from a fresh `origin/main`.
- An ID is **taken** if `quizzes/ID/` exists on `main` or an open pull request is titled `Quiz ID: …`.
  List the open pull requests once and check both.
- If EXTRA is no: `ID` = `WEEK`. If it's taken: **stop** ("WEEK is already published" or
  "WEEK already has an open PR: <link>"). This keeps an accidental second run of the Routine from making a duplicate.
- If EXTRA is yes: `ID` = the first free ID in the order `WEEK`, `WEEK-2`, `WEEK-3`, …
  If all nine are taken: **stop** ("WEEK already has 9 quizzes").
- A leftover branch from a failed run with no PR is fine: delete it or reuse the name with a fresh start from `origin/main`.
- Branch name: `quiz/ID`. If this session was told to develop on a specific branch, use that branch for the first
  quiz, and that name plus `-2`, `-3`, … for the others.

**More than one quiz (COUNT > 1):** make them one at a time. Do steps 2–9 for the first quiz, then go back to
step 2 for the next one. Each quiz gets its own branch, started fresh from `origin/main` (never on top of the previous
quiz's branch), and its own PR. Its new PR title makes its ID and topic count as taken for the next quiz.
If a later quiz has to **stop**, the earlier PRs stay open. Say which quizzes made it and which didn't.
Each PR removes its own topic from `topics.json`, so whichever is merged second will get a merge conflict there.
That's expected: say so in the final summary, and point to "Fixing a topics.json merge conflict".

## 3. Pick the topic

- Read `topics.json` (a list, already shuffled). If it's empty: **stop** ("topic list is empty; time for a refresh").
- Collect topics already in use: the `topic` field of every `quizzes/*/quiz.json`, plus the topic in the title of
  every open `Quiz …: <topic>` PR (including the ones you opened earlier in this run; their removal from
  `topics.json` isn't on `main` yet). Take the **first entry that is not already in use**.
  If every entry is in use: **stop** ("every topic left is already in an open PR; merge some or refresh the list").
- If the request says "skip this topic" or names a topic, follow that.
- Remove only the chosen entry: `python3 scripts/remove_topic.py --topic "<topic>"`. Don't edit `topics.json` by hand.
  (Each quiz PR removes its own topic. When two quiz PRs are open at once, merging one gives the other a merge
  conflict in `topics.json`; see "Fixing a topics.json merge conflict" below.)
- The entry may preset `outcomes` (how many results) and `scoring` (`winner` or `blend`). `null` means you decide.

## 4. Design the quiz

Read `docs/example-quiz/quiz.json` and `style.css` for the exact format, then write
`quizzes/ID/quiz.json`. The validator is the source of truth for the rules; the main ones:

- **Questions:** 5–12. Pick the count that suits the topic. Each has 2–6 answers.
- **Outcomes:** 2–10, or the preset count. Each has `id` (slug), `name`, `tagline` (≤90 chars),
  `description` (80–600 chars), exactly 3 `traits`, an `emoji`, and a `color` that reads well on `theme.card`.
  Set `image` to `null` or leave it out (images come later).
- **Scores:** each answer gives 1–3 points to one or more outcomes, by `id`.
- **Scoring:** `winner` = most points wins. `blend` = the result also shows the mix (e.g. 55% / 27% / 18%).
  Use blend when results naturally overlap (styles, archetypes, aesthetics), winner when they're distinct types.
- **Tie-break** is automatic: the tied outcome that scored most recently wins. Don't design around it.
- **Theme:** `bg`, `fg`, `card`, `accent`, `accent_fg` as 6-digit hex. Text contrast must be ≥ 4.5.
- `week` = WEEK (the plain ISO week, even for `WEEK-2`), `topic` = the topic string exactly as it was in `topics.json`, `category` = its category.

Writing guidelines:
- Fun, warm and a bit witty. Answers should be things people actually pick, not obviously "the right one".

Question logic (the most common failure, so check every question against these):
- **Answers must answer the question.** "Pick a weather" takes weathers ("Thunderstorm", "Drizzle",
  "Blazing heat"), not activities ("Overcast with a good book") or other categories ("Festival-weather sunshine").
- **Answers are parallel:** the same kind of thing, the same grammatical shape and roughly the same length.
  If one answer is a place, they're all places; if one is a sentence, they all are.
- **One idea per answer.** Don't bolt a second idea onto an answer to steer it to an outcome
  ("Rainy and cosy" smuggles in a mood). Pick a cleaner answer instead.
- **Distinct options:** no two answers in a question should feel interchangeable or overlap.
- **The link to the outcome should make sense on reflection** (a reader who sees the scoring nods),
  but shouldn't be spelled out in the answer. Don't name the outcomes or echo the topic in answers
  (no "a cup of tea" answers in a tea quiz).
- **Vary the questions:** mix scenarios ("Your friend cancels plans. You…"), preferences ("Pick a…"),
  and either/or style picks. No two questions should test the same thing.
- Before moving on, read each question with its answers aloud in your head. If any answer sounds odd after
  the question, rewrite it.
- Every outcome should feel like a result someone would be happy to get. No negative or mean outcomes.
- Lopsided results are allowed and can be fun (a rare 🦄 result is good), but every outcome must be reachable.
- No stereotypes about real groups of people, nothing about health, weight, religion or politics.
- Fictional characters: names and well-known traits only; no quoting copyrighted text.
- Don't reuse questions or outcome sets from earlier quizzes; skim `quizzes/*/quiz.json` titles first
  (and any quiz you wrote earlier in this run, which is on its own branch).

## 5. Design the theme

Write `quizzes/ID/style.css` to give this quiz its own look. Be creative: it's the main way quizzes differ.

- Your CSS is placed after the engine's base styles, so it overrides them.
- `theme` colours are already applied as `--bg --fg --card --accent --accent-fg`. You can also set:
  `--muted --border --radius --font-body --font-display`.
- Fonts: `@import` from `https://fonts.googleapis.com/` only. Images/patterns: `data:` URIs, gradients or
  emoji only; no other URLs. No `<` characters. Max 30 KB.
- Markup you can style (don't rely on anything else):
  - `body.quiz-page[data-quiz]` and, on the result screen, `body[data-result="<outcome-id>"]`
  - `.site-header .home-link .quiz-week`, `#app[data-screen="intro|question|result"]`, `.quiz-nav a`
  - Intro: `.screen.intro .quiz-emoji .quiz-title .quiz-intro .quiz-meta .btn.btn-primary`
  - Question: `.screen.question .progress .progress-bar .question-count .question-text .answers .answer .btn-back`
  - Result: `.screen.result .result-card[data-outcome] .result-label .result-emoji .result-name .result-tagline
    .result-description .result-traits li .blend .blend-row .blend-name .blend-bar .blend-fill .blend-pct
    .result-actions .btn .all-outcomes .outcome-mini(.is-yours) .outcome-mini-name .outcome-mini-tagline`
  - `--outcome-color` is set on result cards to that outcome's `color`.
  - Transitions are built in: each screen gets `.screen-enter` with `data-direction="forward|back|none"`, the
    tapped answer gets `.is-picked` and its list `.is-locked`. Tune them with `--enter-distance` (default 28px)
    and `--enter-duration` (default 320ms), or restyle `.answer.is-picked` to suit the theme. Don't remove them.
- Keep it readable on a phone (390 px wide) and respect `prefers-reduced-motion` for any animation.

## 6. Check and fix (max 3 attempts)

Run `scripts/check_quiz.sh ID`. It runs, in order:
`validate.py` (schema, limits, contrast, CSS rules) → `simulate.py` (10,000 random playthroughs; fails if an
outcome is unreachable) → `build.py` → `playtest.mjs` (a headless browser plays the real page to every outcome).

If anything fails, read the message, fix `quiz.json` / `style.css`, and run it again.
Count the attempts. After 3 failed attempts: **stop** with the last error output.

Look at the outcome split it prints. Imbalance is fine. But if one outcome is above ~60% or the split
obviously isn't what you intended, adjust the scores and re-run (this counts as an attempt).

## 7. Critic pass

Start a subagent (Agent tool) with this brief, passing it the path to `quiz.json` and the simulate output:

> You are reviewing a personality quiz before it's published. Read quizzes/ID/quiz.json, then
> .claude/skills/weekly-quiz/SKILL.md section 4 ("Question logic").
> Go through EVERY question one by one and check each answer against those rules: does it actually answer
> the question, is it the same kind of thing as the other answers, is it one idea, is it distinct?
> Report BLOCKING issues: any answer that breaks a question-logic rule; offensive or stereotyping content;
> factual errors about real or fictional things; confusing questions; an outcome that would feel insulting;
> answers that obviously point at one result. Report NON-BLOCKING notes (tone, weaker questions, ideas).
> Quote the exact text for every issue. Don't rewrite the quiz.

Fix every blocking issue, then run `scripts/check_quiz.sh ID` again (must pass). If you changed more than a
couple of answers, run the critic once more on the new version.

## 8. Report

Write `.work/ID/notes.md` with short sections:
- **Design choices:** why this number of questions/outcomes, why this scoring mode, the theme idea.
- **Critic notes:** what it flagged, what you changed, what you left and why.
- **Uncertainties:** anything the reviewer should look at closely.

Then run `python3 scripts/report.py ID --notes .work/ID/notes.md --attempts N`.
This writes `reports/ID.md` with the outcomes, every question and its scoring, and the outcome split.
Never type the numbers yourself.

## 9. Scope check, commit, PR

1. `python3 scripts/check_scope.py ID`. It must pass. If it lists other files, revert them (don't commit them).
2. Commit exactly: `quizzes/ID/quiz.json`, `quizzes/ID/style.css`, `reports/ID.md`, `topics.json`.
   Message: `Add quiz ID: <title>`.
3. Push the branch and open a PR against `main`:
   - Title: `Quiz ID: <topic>` (exactly this form; step 2 relies on it).
   - Body: the title and emoji, one line about the theme, the outcome split table (copy it from
     `reports/ID.md`), a link to the report file on the branch, and:
     "Preview: https://am3lia-low.github.io/quizzle-2.0/preview/ID/ (ready a minute or two after the PR opens)".
4. Finish with a short summary: the title, the PR link, the preview link, and anything from "Uncertainties".
   With several quizzes, one summary block per quiz.

## Fixing a topics.json merge conflict

Use this when asked to update or fix a quiz PR that GitHub says has conflicts (usually because another quiz PR
was merged first, and both removed a line from `topics.json`). It is also part of driving your own quiz PR to green.

1. Check out the PR's branch and `git fetch origin main`. Find its quiz `ID` from `quizzes/<ID>/` in the PR.
2. `git merge origin/main`. Never rebase or force-push a quiz branch.
3. If only `topics.json` conflicts, resolve it with
   `python3 scripts/remove_topic.py --quiz ID --from origin/main`
   (main's list, which already lacks the merged quizzes' topics, minus this quiz's topic), then `git add topics.json`
   and `git commit --no-edit`.
   If anything else conflicts, or the script says the topic isn't in main's list (another merged quiz already
   used it): `git merge --abort` and **stop**, explaining what conflicted.
4. Check: `python3 scripts/check_scope.py ID` and `scripts/check_quiz.sh ID` must pass, and
   `git diff origin/main -- topics.json` must show exactly one removed line: this quiz's topic.
5. Push the branch (a normal push; the merge commit keeps the history intact).

## Things that are not your job

- Don't merge the PR, don't push to `main`, don't touch `engine/`, `scripts/`, `.github/`, `docs/`.
- Don't "fix" a failing script by changing the script. Stop and report the failure instead.
