"""Shared quiz logic: loading, validation, scoring, simulation.

Standard library only. Scoring and tie-break rules here must match engine/engine.js.
"""

from __future__ import annotations

import itertools
import json
import random
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUIZZES = ROOT / "quizzes"
REPORTS = ROOT / "reports"
TOPICS = ROOT / "topics.json"

WEEK_RE = re.compile(r"^\d{4}-W(0[1-9]|[1-4]\d|5[0-3])$")
ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")

MIN_QUESTIONS, MAX_QUESTIONS = 5, 12
MIN_OUTCOMES, MAX_OUTCOMES = 2, 10
MIN_ANSWERS, MAX_ANSWERS = 2, 6
MIN_POINTS, MAX_POINTS = 1, 3
SIM_RUNS = 10_000
RARE_SHARE = 0.05
DOMINANT_SHARE = 0.50
EXACT_LIMIT = 200_000  # enumerate every answer combination when there are at most this many
MAX_CSS_BYTES = 30_000


# ---------------------------------------------------------------- loading

def quiz_dir(week: str) -> Path:
    return QUIZZES / week


def load_quiz(week: str) -> dict:
    return json.loads((quiz_dir(week) / "quiz.json").read_text(encoding="utf-8"))


def load_css(week: str) -> str:
    path = quiz_dir(week) / "style.css"
    return path.read_text(encoding="utf-8") if path.exists() else ""


def all_weeks() -> list[str]:
    if not QUIZZES.exists():
        return []
    return sorted(p.name for p in QUIZZES.iterdir() if p.is_dir() and WEEK_RE.match(p.name))


# ---------------------------------------------------------------- validation

QUIZ_KEYS = {
    "week": True, "title": True, "topic": True, "category": True, "intro": True,
    "scoring": True, "theme": True, "outcomes": True, "questions": True,
    "emoji": False, "start_label": False, "result_label": False,
}
THEME_KEYS = {"bg", "fg", "card", "accent", "accent_fg"}
OUTCOME_KEYS = {
    "id": True, "name": True, "tagline": True, "description": True, "traits": True,
    "emoji": False, "color": False, "image": False,
}


def _check_keys(obj, spec: dict, where: str, errors: list[str]) -> None:
    for key, required in spec.items():
        if required and key not in obj:
            errors.append(f"{where}: missing '{key}'")
    for key in obj:
        if key not in spec:
            errors.append(f"{where}: unknown key '{key}'")


def _check_text(value, where: str, errors: list[str], max_len: int, min_len: int = 1) -> None:
    if not isinstance(value, str):
        errors.append(f"{where}: must be a string")
    elif not (min_len <= len(value.strip()) <= max_len):
        errors.append(f"{where}: length {len(value.strip())} not in {min_len}..{max_len}")


def _luminance(hex_color: str) -> float:
    def channel(c: int) -> float:
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast(a: str, b: str) -> float:
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def validate(quiz: dict, week: str | None = None) -> list[str]:
    """Return a list of human-readable problems. Empty list means valid."""
    errors: list[str] = []
    if not isinstance(quiz, dict):
        return ["quiz.json must be an object"]
    _check_keys(quiz, QUIZ_KEYS, "quiz", errors)

    if not isinstance(quiz.get("week"), str) or not WEEK_RE.match(quiz.get("week", "")):
        errors.append("quiz.week: must look like 2026-W42")
    elif week and quiz["week"] != week:
        errors.append(f"quiz.week: '{quiz['week']}' does not match folder '{week}'")
    _check_text(quiz.get("title"), "quiz.title", errors, 80)
    _check_text(quiz.get("topic"), "quiz.topic", errors, 120)
    if not isinstance(quiz.get("category"), str) or not ID_RE.match(quiz.get("category", "")):
        errors.append("quiz.category: must be a lowercase slug like 'food'")
    _check_text(quiz.get("intro"), "quiz.intro", errors, 300)
    for key in ("emoji", "start_label", "result_label"):
        if key in quiz:
            _check_text(quiz[key], f"quiz.{key}", errors, 30)
    if quiz.get("scoring") not in ("winner", "blend"):
        errors.append("quiz.scoring: must be 'winner' or 'blend'")

    theme = quiz.get("theme")
    if not isinstance(theme, dict):
        errors.append("quiz.theme: must be an object with bg, fg, card, accent, accent_fg")
    else:
        _check_keys(theme, {k: True for k in THEME_KEYS}, "quiz.theme", errors)
        if all(isinstance(theme.get(k), str) and HEX_RE.match(theme[k]) for k in THEME_KEYS):
            if contrast(theme["fg"], theme["bg"]) < 4.5:
                errors.append(f"quiz.theme: fg/bg contrast {contrast(theme['fg'], theme['bg']):.1f} < 4.5")
            if contrast(theme["fg"], theme["card"]) < 4.5:
                errors.append(f"quiz.theme: fg/card contrast {contrast(theme['fg'], theme['card']):.1f} < 4.5")
            if contrast(theme["accent_fg"], theme["accent"]) < 4.5:
                errors.append(
                    f"quiz.theme: accent_fg/accent contrast {contrast(theme['accent_fg'], theme['accent']):.1f} < 4.5")
        else:
            errors.append("quiz.theme: every colour must be a 6-digit hex like #1a2b3c")

    outcomes = quiz.get("outcomes")
    ids: list[str] = []
    if not isinstance(outcomes, list) or not (MIN_OUTCOMES <= len(outcomes) <= MAX_OUTCOMES):
        errors.append(f"quiz.outcomes: need {MIN_OUTCOMES}..{MAX_OUTCOMES} outcomes")
        outcomes = outcomes if isinstance(outcomes, list) else []
    for i, o in enumerate(outcomes):
        where = f"outcomes[{i}]"
        if not isinstance(o, dict):
            errors.append(f"{where}: must be an object")
            continue
        _check_keys(o, OUTCOME_KEYS, where, errors)
        oid = o.get("id")
        if not isinstance(oid, str) or not ID_RE.match(oid):
            errors.append(f"{where}.id: must be a lowercase slug like 'oat-latte'")
        elif oid in ids:
            errors.append(f"{where}.id: duplicate '{oid}'")
        else:
            ids.append(oid)
        _check_text(o.get("name"), f"{where}.name", errors, 40)
        _check_text(o.get("tagline"), f"{where}.tagline", errors, 90)
        _check_text(o.get("description"), f"{where}.description", errors, 600, 80)
        traits = o.get("traits")
        if not isinstance(traits, list) or len(traits) != 3:
            errors.append(f"{where}.traits: need exactly 3")
        else:
            for j, t in enumerate(traits):
                _check_text(t, f"{where}.traits[{j}]", errors, 30)
        if "emoji" in o:
            _check_text(o["emoji"], f"{where}.emoji", errors, 16)
        if "color" in o:
            if not (isinstance(o["color"], str) and HEX_RE.match(o["color"])):
                errors.append(f"{where}.color: must be a 6-digit hex")
            elif isinstance(theme, dict) and isinstance(theme.get("card"), str) and HEX_RE.match(theme["card"]):
                if contrast(o["color"], theme["card"]) < 3:
                    errors.append(f"{where}.color: contrast with theme.card "
                                  f"{contrast(o['color'], theme['card']):.1f} < 3 (the result name would be hard to read)")
        if "image" in o and o["image"] is not None:
            errors.append(f"{where}.image: images are not supported yet; leave it null")

    questions = quiz.get("questions")
    if not isinstance(questions, list) or not (MIN_QUESTIONS <= len(questions) <= MAX_QUESTIONS):
        errors.append(f"quiz.questions: need {MIN_QUESTIONS}..{MAX_QUESTIONS} questions")
        questions = questions if isinstance(questions, list) else []
    seen_text = set()
    for qi, q in enumerate(questions):
        where = f"questions[{qi}]"
        if not isinstance(q, dict):
            errors.append(f"{where}: must be an object")
            continue
        _check_keys(q, {"text": True, "answers": True}, where, errors)
        _check_text(q.get("text"), f"{where}.text", errors, 200)
        if isinstance(q.get("text"), str):
            key = q["text"].strip().lower()
            if key in seen_text:
                errors.append(f"{where}.text: duplicate question")
            seen_text.add(key)
        answers = q.get("answers")
        if not isinstance(answers, list) or not (MIN_ANSWERS <= len(answers) <= MAX_ANSWERS):
            errors.append(f"{where}.answers: need {MIN_ANSWERS}..{MAX_ANSWERS} answers")
            continue
        for ai, a in enumerate(answers):
            aw = f"{where}.answers[{ai}]"
            if not isinstance(a, dict):
                errors.append(f"{aw}: must be an object")
                continue
            _check_keys(a, {"text": True, "scores": True}, aw, errors)
            _check_text(a.get("text"), f"{aw}.text", errors, 140)
            scores = a.get("scores")
            if not isinstance(scores, dict) or not scores:
                errors.append(f"{aw}.scores: must give points to at least one outcome")
                continue
            for oid, pts in scores.items():
                if oid not in ids:
                    errors.append(f"{aw}.scores: unknown outcome '{oid}'")
                if not isinstance(pts, int) or isinstance(pts, bool) or not (MIN_POINTS <= pts <= MAX_POINTS):
                    errors.append(f"{aw}.scores['{oid}']: points must be an integer {MIN_POINTS}..{MAX_POINTS}")
    return errors


FORBIDDEN_CSS = [
    (re.compile(r"<"), "'<' is not allowed (could close the style tag)"),
    (re.compile(r"javascript:", re.I), "'javascript:' is not allowed"),
    (re.compile(r"expression\s*\(", re.I), "'expression(' is not allowed"),
    (re.compile(r"-moz-binding|behavior\s*:", re.I), "bindings/behaviors are not allowed"),
]
IMPORT_RE = re.compile(r"@import\s+(?:url\(\s*)?(['\"]?)([^'\"\s)]+)\1\s*\)?[^;\n]*;?", re.I)
URL_RE = re.compile(r"url\(\s*['\"]?([^'\")\s]+)", re.I)


def validate_css(css: str) -> list[str]:
    errors: list[str] = []
    if len(css.encode("utf-8")) > MAX_CSS_BYTES:
        errors.append(f"style.css: larger than {MAX_CSS_BYTES} bytes")
    for pattern, message in FORBIDDEN_CSS:
        if pattern.search(css):
            errors.append(f"style.css: {message}")
    for _, target in IMPORT_RE.findall(css):
        if not target.startswith("https://fonts.googleapis.com/"):
            errors.append(f"style.css: @import only allowed from https://fonts.googleapis.com/ (got {target[:60]})")
    for target in URL_RE.findall(IMPORT_RE.sub("", css)):
        if not target.startswith("data:"):
            errors.append(f"style.css: url() must be a data: URI (got {target[:60]})")
    return errors


# ---------------------------------------------------------------- scoring

def score(quiz: dict, picks: list[int]) -> tuple[str, dict[str, int], bool]:
    """Return (winner_id, totals, was_tied).

    Tie-break (same as engine.js): among outcomes tied on points, the one that most
    recently received points wins; if still tied, the one listed first in outcomes.
    """
    order = [o["id"] for o in quiz["outcomes"]]
    totals = {oid: 0 for oid in order}
    last = {oid: -1 for oid in order}
    for q, answer_index in enumerate(picks):
        for oid, pts in quiz["questions"][q]["answers"][answer_index]["scores"].items():
            if pts > 0:
                totals[oid] += pts
                last[oid] = q
    best = order[0]
    for oid in order[1:]:
        if totals[oid] > totals[best] or (totals[oid] == totals[best] and last[oid] > last[best]):
            best = oid
    top = max(totals.values())
    tied = sum(1 for v in totals.values() if v == top) > 1
    return best, totals, tied


def answer_counts(quiz: dict) -> list[int]:
    return [len(q["answers"]) for q in quiz["questions"]]


def _search_witness(quiz: dict, target: str, rng: random.Random) -> list[int] | None:
    """Hill-climb for an answer path that makes `target` the result."""
    counts = answer_counts(quiz)

    def margin(picks):
        winner, totals, _ = score(quiz, picks)
        other = max((v for k, v in totals.items() if k != target), default=0)
        return (winner == target, totals[target] - other)

    for restart in range(60):
        if restart == 0:  # greedy start: best answer for target on each question
            picks = []
            for q in quiz["questions"]:
                best = max(range(len(q["answers"])), key=lambda i: (
                    q["answers"][i]["scores"].get(target, 0)
                    - max((p for k, p in q["answers"][i]["scores"].items() if k != target), default=0)))
                picks.append(best)
        else:
            picks = [rng.randrange(n) for n in counts]
        current = margin(picks)
        improved = True
        while improved and not current[0]:
            improved = False
            for q, n in enumerate(counts):
                for a in range(n):
                    if a == picks[q]:
                        continue
                    trial = picks[:q] + [a] + picks[q + 1:]
                    m = margin(trial)
                    if m > current:
                        picks, current, improved = trial, m, True
        if current[0]:
            return picks
    return None


def simulate(quiz: dict, runs: int = SIM_RUNS, seed: str | None = None) -> dict:
    """Random playthroughs plus a reachability check with an example path per outcome."""
    rng = random.Random(seed or quiz.get("week", "seed"))
    counts = answer_counts(quiz)
    order = [o["id"] for o in quiz["outcomes"]]
    wins = {oid: 0 for oid in order}
    ties = 0
    samples = []  # a few random paths with the expected result, replayed by playtest.mjs
    for i in range(runs):
        picks = [rng.randrange(n) for n in counts]
        winner, _, tied = score(quiz, picks)
        wins[winner] += 1
        ties += tied
        if i < 15:
            samples.append({"picks": picks, "winner": winner})

    combos = 1
    for n in counts:
        combos *= n
    witnesses: dict[str, list[int] | None] = {oid: None for oid in order}
    if combos <= EXACT_LIMIT:
        method = "exact"
        for picks in itertools.product(*(range(n) for n in counts)):
            winner, _, _ = score(quiz, list(picks))
            if witnesses[winner] is None:
                witnesses[winner] = list(picks)
                if all(w is not None for w in witnesses.values()):
                    break
    else:
        method = "search"
        for oid in order:
            witnesses[oid] = _search_witness(quiz, oid, rng)

    shares = {oid: wins[oid] / runs for oid in order}
    reached = [oid for oid in order if wins[oid] > 0]
    ratio = (max(wins[o] for o in reached) / min(wins[o] for o in reached)) if reached else None
    return {
        "runs": runs,
        "wins": wins,
        "shares": shares,
        "tie_rate": ties / runs,
        "combinations": combos,
        "reachability_method": method,
        "witnesses": witnesses,
        "samples": samples,
        "unreachable": [oid for oid in order if witnesses[oid] is None],
        "max_min_ratio": ratio,
    }


def split_table(quiz: dict, sim: dict) -> str:
    """Markdown table of the outcome split, most common first."""
    names = {o["id"]: (o.get("emoji", "") + " " + o["name"]).strip() for o in quiz["outcomes"]}
    rows = sorted(sim["wins"], key=lambda oid: sim["wins"][oid], reverse=True)
    lines = ["| Outcome | Share | Count | Bar | Note |", "|---|---:|---:|---|---|"]
    for oid in rows:
        share = sim["shares"][oid]
        note = ""
        if sim["witnesses"][oid] is None:
            note = "❌ unreachable"
        elif share == 0:
            note = "🦄 reachable, but never hit in random play"
        elif share < RARE_SHARE:
            note = "🦄 rare"
        elif share > DOMINANT_SHARE:
            note = "👑 dominant"
        bar = "█" * max(1 if share > 0 else 0, round(share * 20))
        lines.append(f"| {names[oid]} | {share * 100:.1f}% | {sim['wins'][oid]:,} | {bar} | {note} |")
    return "\n".join(lines)
