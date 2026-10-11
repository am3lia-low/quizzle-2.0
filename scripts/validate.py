"""Validate a quiz: schema, content limits, theme contrast, CSS safety.

Usage: python3 scripts/validate.py 2026-W42
Exit code 0 = valid, 1 = problems (printed one per line).
"""

import json
import sys

import quizlib


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    week = sys.argv[1]
    if not quizlib.WEEK_RE.match(week):
        print(f"bad week id: {week}")
        return 2
    path = quizlib.quiz_dir(week) / "quiz.json"
    try:
        quiz = quizlib.load_quiz(week)
    except FileNotFoundError:
        print(f"missing {path}")
        return 1
    except json.JSONDecodeError as e:
        print(f"{path}: invalid JSON: {e}")
        return 1
    errors = quizlib.validate(quiz, week) + quizlib.validate_css(quizlib.load_css(week))
    if not (quizlib.quiz_dir(week) / "style.css").exists():
        errors.append("missing style.css")
    for e in errors:
        print(e)
    if errors:
        print(f"\nFAIL: {len(errors)} problem(s)")
        return 1
    print(f"OK: {week} is valid ({len(quiz['questions'])} questions, {len(quiz['outcomes'])} outcomes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
