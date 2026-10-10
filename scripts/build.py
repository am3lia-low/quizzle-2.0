"""Build the static site: one self-contained HTML file per quiz, plus the main page.

Usage:
  python3 scripts/build.py                     # every quiz -> _site/
  python3 scripts/build.py --out DIR           # choose the output folder
  python3 scripts/build.py --preview 2026-W42  # one quiz -> DIR/preview/index.html, with a PREVIEW banner

Each quiz page inlines engine/engine.js, the quiz's style.css and quiz.json, so it
works on its own, even opened straight from disk.
"""

import argparse
import html
import json
import shutil
import sys

import quizlib

ENGINE = quizlib.ROOT / "engine"


def _json_for_script(data) -> str:
    # Safe inside <script type="application/json">: never lets the data close the tag.
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


def render_quiz(week: str, nav: dict, preview: bool = False) -> str:
    quiz = quizlib.load_quiz(week)
    shell = (ENGINE / "shell.html").read_text(encoding="utf-8")
    banner = '<div class="preview-banner">PREVIEW · not published yet</div>' if preview else ""
    replacements = {
        "__TITLE__": html.escape(quiz["title"]),
        "__DESCRIPTION__": html.escape(quiz["intro"]),
        "__WEEK__": html.escape(week),
        "__HOME_HREF__": html.escape(nav["home"]),
        "__PREVIEW_BANNER__": banner,
        "__QUIZ_CSS__": theme_vars(quiz) + "\n" + quizlib.load_css(week),
        "__QUIZ_JSON__": _json_for_script(quiz),
        "__NAV_JSON__": _json_for_script(nav),
        "__ENGINE_JS__": (ENGINE / "engine.js").read_text(encoding="utf-8"),
    }
    # Single pass so inserted content is never re-scanned for placeholders.
    for key, value in replacements.items():
        shell = shell.replace(key, value.replace("__", "\x00"))
    return shell.replace("\x00", "__")


def theme_vars(quiz: dict) -> str:
    t = quiz["theme"]
    return (f":root {{ --bg: {t['bg']}; --fg: {t['fg']}; --accent: {t['accent']}; "
            f"--accent-fg: {t['accent_fg']}; --card: {t['card']}; }}")


def card_style(quiz: dict) -> str:
    t = quiz["theme"]
    return f"--qbg:{t['card']};--qfg:{t['fg']};--qaccent:{t['accent']};--qaccent-fg:{t['accent_fg']}"


def render_archive(weeks: list[str]) -> str:
    template = (ENGINE / "archive.html").read_text(encoding="utf-8")
    quizzes = [quizlib.load_quiz(w) for w in weeks]
    newest_first = list(reversed(quizzes))
    e = html.escape

    featured = ""
    if newest_first:
        q = newest_first[0]
        featured = (
            f'<a class="featured" href="{e(q["week"])}.html" style="{card_style(q)}">'
            f'<div class="label">This week · {e(q["week"])}</div>'
            f'<div class="emoji">{e(q.get("emoji", ""))}</div>'
            f'<h2>{e(q["title"])}</h2><p>{e(q["intro"])}</p>'
            f'<span class="cta">Take the quiz</span></a>'
        )

    categories = sorted({q["category"] for q in quizzes})
    chips = ['<button class="chip" type="button" data-category="all" aria-pressed="true">All</button>']
    chips += [f'<button class="chip" type="button" data-category="{e(c)}" aria-pressed="false">'
              f'{e(c.replace("-", " ").title())}</button>' for c in categories]

    cards = []
    for q in newest_first:
        search = " ".join([q["title"], q["category"], q["intro"]] + [o["name"] for o in q["outcomes"]]).lower()
        cards.append(
            f'<a class="card" href="{e(q["week"])}.html" data-category="{e(q["category"])}" '
            f'data-search="{e(search)}" style="{card_style(q)}">'
            f'<span class="emoji">{e(q.get("emoji", ""))}</span>'
            f'<h3>{e(q["title"])}</h3>'
            f'<span class="meta">{e(q["week"])} · {e(q["category"].replace("-", " "))} · '
            f'{len(q["outcomes"])} results</span></a>'
        )

    count = f"{len(quizzes)} quiz" + ("" if len(quizzes) == 1 else "zes")
    out = template
    for key, value in {"__COUNT__": count, "__FEATURED__": featured,
                       "__CHIPS__": "".join(chips), "__CARDS__": "".join(cards)}.items():
        out = out.replace(key, value)
    if not quizzes:
        out = out.replace('<p class="empty" hidden>No quizzes match.', '<p class="empty">The first quiz is on its way.')
    return out


def build_site(out_dir, weeks: list[str]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    titles = {w: quizlib.load_quiz(w)["title"] for w in weeks}
    for i, week in enumerate(weeks):
        nav = {"home": "./"}
        if i > 0:
            nav["prev"] = {"href": f"{weeks[i - 1]}.html", "title": titles[weeks[i - 1]]}
        if i + 1 < len(weeks):
            nav["next"] = {"href": f"{weeks[i + 1]}.html", "title": titles[weeks[i + 1]]}
        (out_dir / f"{week}.html").write_text(render_quiz(week, nav), encoding="utf-8")
    (out_dir / "index.html").write_text(render_archive(weeks), encoding="utf-8")
    (out_dir / ".nojekyll").write_text("", encoding="utf-8")


def build_preview(out_dir, week: str) -> None:
    preview_dir = out_dir / "preview"
    preview_dir.mkdir(parents=True, exist_ok=True)
    html_text = render_quiz(week, {"home": "../"}, preview=True)
    (preview_dir / "index.html").write_text(html_text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default=str(quizlib.ROOT / "_site"))
    parser.add_argument("--preview", metavar="WEEK", help="build only this quiz as the preview page")
    parser.add_argument("--clean", action="store_true", help="delete the output folder first")
    args = parser.parse_args()

    from pathlib import Path
    out_dir = Path(args.out)
    if args.clean and out_dir.exists():
        shutil.rmtree(out_dir)

    weeks = [args.preview] if args.preview else quizlib.all_weeks()
    problems = []
    for week in weeks:
        problems += [f"{week}: {p}" for p in quizlib.validate(quizlib.load_quiz(week), week)]
        problems += [f"{week}: {p}" for p in quizlib.validate_css(quizlib.load_css(week))]
    if problems:
        print("\n".join(problems))
        print("FAIL: not building invalid quizzes")
        return 1

    if args.preview:
        build_preview(out_dir, args.preview)
        print(f"built preview of {args.preview} -> {out_dir / 'preview' / 'index.html'}")
    else:
        build_site(out_dir, weeks)
        print(f"built {len(weeks)} quiz page(s) + index.html -> {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
