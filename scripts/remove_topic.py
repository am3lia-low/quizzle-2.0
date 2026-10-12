"""Remove one topic from topics.json, keeping the file's one-entry-per-line format.

Usage:
  python3 scripts/remove_topic.py --topic "Which bread are you"     # when picking a quiz's topic
  python3 scripts/remove_topic.py --quiz 2026-W42-2 --from origin/main
      # resolving a topics.json merge conflict: main's list minus this quiz's topic

--from REF starts from that git revision's topics.json instead of the working copy.
"""

import argparse
import json
import subprocess
import sys

import quizlib


def dump(topics: list) -> str:
    return "[\n" + ",\n".join("  " + json.dumps(t, ensure_ascii=False) for t in topics) + "\n]\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    which = parser.add_mutually_exclusive_group(required=True)
    which.add_argument("--topic", help="the topic string, exactly as in topics.json")
    which.add_argument("--quiz", metavar="QUIZ_ID", help="use the topic of quizzes/QUIZ_ID/quiz.json")
    parser.add_argument("--from", dest="ref", help="git revision to read topics.json from (e.g. origin/main)")
    args = parser.parse_args()

    topic = args.topic if args.topic is not None else quizlib.load_quiz(args.quiz)["topic"]
    if args.ref:
        text = subprocess.run(["git", "show", f"{args.ref}:topics.json"], cwd=quizlib.ROOT,
                              check=True, capture_output=True, text=True).stdout
    else:
        text = quizlib.TOPICS.read_text(encoding="utf-8")
    topics = json.loads(text)

    kept = [t for t in topics if t["topic"] != topic]
    if len(kept) == len(topics):
        print(f"topic not found in topics.json{f' at {args.ref}' if args.ref else ''}: {topic!r}")
        return 1
    quizlib.TOPICS.write_text(dump(kept), encoding="utf-8")
    print(f"removed {topic!r} ({len(kept)} topic(s) left)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
