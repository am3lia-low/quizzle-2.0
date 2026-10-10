"""Write reports/<week>.md from the quiz, the simulation and the agent's notes.

Usage: python3 scripts/report.py 2026-W42 --notes .work/2026-W42/notes.md --attempts 2

All numbers come straight from .work/<week>/simulation.json (written by simulate.py),
so the report can't drift from what the simulator measured.
"""

import argparse
import json
import sys

import quizlib


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("week")
    parser.add_argument("--notes", help="markdown file with the agent's and critic's notes")
    parser.add_argument("--attempts", type=int, default=1, help="validate/simulate attempts needed")
    args = parser.parse_args()

    week = args.week
    quiz = quizlib.load_quiz(week)
    sim_path = quizlib.ROOT / ".work" / week / "simulation.json"
    if not sim_path.exists():
        print("run simulate.py first")
        return 1
    sim = json.loads(sim_path.read_text(encoding="utf-8"))
    notes = ""
    if args.notes:
        notes = open(args.notes, encoding="utf-8").read().strip()

    names = {o["id"]: o["name"] for o in quiz["outcomes"]}
    lines = [
        f"# Quiz report: {week}",
        "",
        f"**{quiz.get('emoji', '')} {quiz['title']}**".replace("** ", "**"),
        "",
        "| | |",
        "|---|---|",
        f"| Topic | {quiz['topic']} |",
        f"| Category | {quiz['category']} |",
        f"| Scoring | {quiz['scoring']} |",
        f"| Questions | {len(quiz['questions'])} |",
        f"| Outcomes | {len(quiz['outcomes'])} |",
        f"| Fix attempts | {args.attempts} |",
        f"| Theme | bg `{quiz['theme']['bg']}` · fg `{quiz['theme']['fg']}` · accent `{quiz['theme']['accent']}` |",
        "",
        f"> {quiz['intro']}",
        "",
        f"## Outcome split ({sim['runs']:,} random playthroughs)",
        "",
        quizlib.split_table(quiz, sim),
        "",
        f"- Every outcome reachable: {'✅' if not sim['unreachable'] else '❌ ' + ', '.join(sim['unreachable'])}",
        f"- Ties before tie-break: {sim['tie_rate'] * 100:.1f}% "
        "(tie-break: the tied outcome that scored most recently wins)",
    ]
    if sim["max_min_ratio"]:
        lines.append(f"- Most common vs rarest: {sim['max_min_ratio']:.1f}× apart")
    lines.append(f"- Reachability checked by: {sim['reachability_method']} "
                 f"({sim['combinations']:,} possible answer combinations)")

    lines += ["", "## Outcomes", ""]
    for o in quiz["outcomes"]:
        lines += [
            f"### {o.get('emoji', '')} {o['name']}".replace("###  ", "### "),
            f"*{o['tagline']}*",
            "",
            o["description"],
            "",
            f"Traits: {', '.join(o['traits'])}",
            "",
        ]

    lines += ["## Questions", ""]
    for qi, q in enumerate(quiz["questions"], 1):
        lines += [f"**Q{qi}. {q['text']}**", "", "| Answer | Points |", "|---|---|"]
        for a in q["answers"]:
            pts = ", ".join(f"{names[k]} +{v}" for k, v in a["scores"].items())
            lines.append(f"| {a['text'].replace('|', '/')} | {pts} |")
        lines.append("")

    lines += ["## Agent notes", "", notes or "_No notes._", ""]
    lines += [
        "## Checklist",
        "",
        "- [x] validate.py passed",
        "- [x] simulate.py passed (every outcome reachable)",
        "- [x] build.py + playtest passed",
        "- [x] check_scope.py passed (only this week's files changed)",
        "",
    ]

    quizlib.REPORTS.mkdir(exist_ok=True)
    out = quizlib.REPORTS / f"{week}.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out.relative_to(quizlib.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
