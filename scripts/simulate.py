"""Play a quiz 10,000 times with random answers and check every outcome is reachable.

Usage: python3 scripts/simulate.py 2026-W42
Prints the outcome split and writes .work/<week>/simulation.json (used by report.py
and playtest.mjs). Exit code 1 if any outcome is unreachable.
"""

import json
import sys

import quizlib


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    week = sys.argv[1]
    quiz = quizlib.load_quiz(week)
    errors = quizlib.validate(quiz, week)
    if errors:
        print("quiz is invalid; run validate.py first")
        return 1
    sim = quizlib.simulate(quiz)
    out = quizlib.ROOT / ".work" / week
    out.mkdir(parents=True, exist_ok=True)
    (out / "simulation.json").write_text(json.dumps(sim, indent=2), encoding="utf-8")

    print(f"{sim['runs']:,} random playthroughs of {week}\n")
    print(quizlib.split_table(quiz, sim))
    print(f"\nTies before tie-break: {sim['tie_rate'] * 100:.1f}%")
    print(f"Reachability: {sim['reachability_method']} over {sim['combinations']:,} combinations")
    if sim["unreachable"]:
        print(f"\nFAIL: unreachable outcome(s): {', '.join(sim['unreachable'])}")
        return 1
    print("\nOK: every outcome is reachable")
    return 0


if __name__ == "__main__":
    sys.exit(main())
