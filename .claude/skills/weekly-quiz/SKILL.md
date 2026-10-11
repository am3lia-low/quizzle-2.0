---
name: weekly-quiz
description: Generate this week's personality quiz (content + theme), check it, write the report and open a PR for review. Use when asked to run the weekly quiz, make a quiz for a given week, or redo a failed week.
---

# Weekly quiz

You are making one personality quiz for the site at `https://am3lia-low.github.io/quizzle-2.0/`.
The output is a pull request that a human reviews, plays and merges. Merging publishes it.

You only ever **write data**: a `quiz.json`, a `style.css`, a report, and the shortened topic list.
You never edit the engine, the scripts, the workflows or anything else. A scope check enforces this.

Work through the steps in order. If a step says **stop**, end the run with a short message saying why;
the person gets an email for every run, so a clear failure message is the whole error report.

## 1. Work out the week

- Default: the current ISO week in Singapore time, `TZ=Asia/Singapore date +%G-W%V` (e.g. `2026-W42`).
  The Routine runs early Monday morning SGT, which is still Sunday in UTC, so don't use UTC here.
- If the request names a week (e.g. "do week 2026-W43"), use that instead.
- Call it `WEEK` below.

## 2. Make sure this isn't a duplicate run

- `git fetch origin main` and start from a fresh `origin/main`.
- If `quizzes/WEEK/` already exists on `main`: **stop** ("WEEK is already published").
- List open pull requests in this repo. If one is titled `Quiz WEEK: …`: **stop** ("WEEK already has an open PR: <link>").
- A leftover branch from a failed run with no PR is fine: delete it or reuse the name with a fresh start from `origin/main`.
- Branch name: `quiz/WEEK`. If this session was told to develop on a specific branch, use that branch instead.

## 3. Pick the topic

- Read `topics.json` (a list, already shuffled). If it's empty: **stop** ("topic list is empty; time for a refresh").
- Collect topics already in use: the `topic` field of every `quizzes/*/quiz.json`, plus the topic in the title of
  every open `Quiz …: <topic>` PR. Take the **first entry that is not already in use**.
- If the request says "skip this topic" or names a topic, follow that.
- Remove the chosen entry from `topics.json`, keeping the rest of the file exactly as it was
  (same order, one entry per line).
- The entry may preset `outcomes` (how many results) and `scoring` (`winner` or `blend`). `null` means you decide.

## 4. Design the quiz

Read `docs/example-quiz/quiz.json` and `style.css` for the exact format, then write
`quizzes/WEEK/quiz.json`. The validator is the source of truth for the rules; the main ones:

- **Questions:** 5–12. Pick the count that suits the topic. Each has 2–6 answers.
- **Outcomes:** 2–10, or the preset count. Each has `id` (slug), `name`, `tagline` (≤90 chars),
  `description` (80–600 chars), exactly 3 `traits`, an `emoji`, and a `color` that reads well on `theme.card`.
  Set `image` to `null` or leave it out (images come later).
- **Scores:** each answer gives 1–3 points to one or more outcomes, by `id`.
- **Scoring:** `winner` = most points wins. `blend` = the result also shows the mix (e.g. 55% / 27% / 18%).
  Use blend when results naturally overlap (styles, archetypes, aesthetics), winner when they're distinct types.
- **Tie-break** is automatic: the tied outcome that scored most recently wins. Don't design around it.
- **Theme:** `bg`, `fg`, `card`, `accent`, `accent_fg` as 6-digit hex. Text contrast must be ≥ 4.5.
- `week` = WEEK, `topic` = the topic string exactly as it was in `topics.json`, `category` = its category.

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
- Don't reuse questions or outcome sets from earlier quizzes; skim `quizzes/*/quiz.json` titles first.

## 5. Design the theme

Write `quizzes/WEEK/style.css` to give this quiz its own look. Be creative: it's the main way quizzes differ.

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
- Keep it readable on a phone (390 px wide) and respect `prefers-reduced-motion` for any animation.

## 6. Check and fix (max 3 attempts)

Run `scripts/check_quiz.sh WEEK`. It runs, in order:
`validate.py` (schema, limits, contrast, CSS rules) → `simulate.py` (10,000 random playthroughs; fails if an
outcome is unreachable) → `build.py` → `playtest.mjs` (a headless browser plays the real page to every outcome).

If anything fails, read the message, fix `quiz.json` / `style.css`, and run it again.
Count the attempts. After 3 failed attempts: **stop** with the last error output.

Look at the outcome split it prints. Imbalance is fine. But if one outcome is above ~60% or the split
obviously isn't what you intended, adjust the scores and re-run (this counts as an attempt).

## 7. Critic pass

Start a subagent (Agent tool) with this brief, passing it the path to `quiz.json` and the simulate output:

> You are reviewing a personality quiz before it's published. Read quizzes/WEEK/quiz.json, then
> .claude/skills/weekly-quiz/SKILL.md section 4 ("Question logic").
> Go through EVERY question one by one and check each answer against those rules: does it actually answer
> the question, is it the same kind of thing as the other answers, is it one idea, is it distinct?
> Report BLOCKING issues: any answer that breaks a question-logic rule; offensive or stereotyping content;
> factual errors about real or fictional things; confusing questions; an outcome that would feel insulting;
> answers that obviously point at one result. Report NON-BLOCKING notes (tone, weaker questions, ideas).
> Quote the exact text for every issue. Don't rewrite the quiz.

Fix every blocking issue, then run `scripts/check_quiz.sh WEEK` again (must pass). If you changed more than a
couple of answers, run the critic once more on the new version.

## 8. Report

Write `.work/WEEK/notes.md` with short sections:
- **Design choices:** why this number of questions/outcomes, why this scoring mode, the theme idea.
- **Critic notes:** what it flagged, what you changed, what you left and why.
- **Uncertainties:** anything the reviewer should look at closely.

Then run `python3 scripts/report.py WEEK --notes .work/WEEK/notes.md --attempts N`.
This writes `reports/WEEK.md` with the outcomes, every question and its scoring, and the outcome split.
Never type the numbers yourself.

## 9. Scope check, commit, PR

1. `python3 scripts/check_scope.py WEEK`. It must pass. If it lists other files, revert them (don't commit them).
2. Commit exactly: `quizzes/WEEK/quiz.json`, `quizzes/WEEK/style.css`, `reports/WEEK.md`, `topics.json`.
   Message: `Add quiz WEEK: <title>`.
3. Push the branch and open a PR against `main`:
   - Title: `Quiz WEEK: <topic>` (exactly this form; step 2 relies on it).
   - Body: the title and emoji, one line about the theme, the outcome split table (copy it from
     `reports/WEEK.md`), a link to the report file on the branch, and:
     "Preview: https://am3lia-low.github.io/quizzle-2.0/preview/ (ready a minute or two after the PR opens)".
4. Finish with a short summary: the title, the PR link, the preview link, and anything from "Uncertainties".

## Things that are not your job

- Don't merge the PR, don't push to `main`, don't touch `engine/`, `scripts/`, `.github/`, `docs/`.
- Don't "fix" a failing script by changing the script. Stop and report the failure instead.
