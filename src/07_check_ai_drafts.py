"""
LedgerGuard: Guardrail check for AI drafts
==========================================

Every number in an AI draft must appear in the brief it was written from.
This catches invented or mis-copied figures before a person reviews the tone.

    docs/ai/drafts/<name>.md  is checked against  docs/ai/brief_<name>.md

Run:  python src/07_check_ai_drafts.py      (exit code 1 if any draft fails)
"""

import re
import sys
from pathlib import Path

AI_DIR = Path(__file__).resolve().parents[1] / "docs" / "ai"
NUMBER = re.compile(r"\$?\d[\d,]*\.?\d*%?x?")


def normalise(token: str) -> str:
    return token.strip("$").rstrip("x%").replace(",", "").rstrip(".")


def draft_body(text: str) -> str:
    """The message itself: between the status header and the review checklist."""
    text = text.split("### Review checklist")[0]
    return text.split("---", 1)[1] if "---" in text else text


def main() -> int:
    failed = False
    for draft in sorted((AI_DIR / "drafts").glob("*.md")):
        brief = AI_DIR / f"brief_{draft.stem}.md"
        if not brief.exists():
            print(f"SKIP  {draft.name}: no matching brief")
            continue
        allowed = {normalise(n) for n in NUMBER.findall(brief.read_text())}
        extra = [n for n in NUMBER.findall(draft_body(draft.read_text())) if normalise(n) not in allowed]
        status = "FAIL" if extra else "PASS"
        failed |= bool(extra)
        print(f"{status}  {draft.name}" + (f": numbers not in brief: {extra}" if extra else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
