"""Write vocab/cv.ttl from the TERMS table in src/consilience/export/vocab.py.

    python scripts/write_vocab.py           # write
    python scripts/write_vocab.py --check   # exit 1 if vocab/cv.ttl is out of date
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from consilience.export.vocab import CV_ONTOLOGY, TERMS, vocab_graph  # noqa: E402

OUT = ROOT / "vocab" / "cv.ttl"
HEADER = ("# Consilience verdict vocabulary (cv). CC BY 4.0.\n"
          "# Generated from src/consilience/export/vocab.py by scripts/write_vocab.py; do not edit.\n")


def render() -> str:
    return HEADER + vocab_graph().serialize(format="turtle")


def main() -> int:
    text = render()
    if "--check" in sys.argv:
        ok = OUT.exists() and OUT.read_text(encoding="utf-8") == text
        print("vocab/cv.ttl is up to date" if ok else "vocab/cv.ttl is out of date")
        return 0 if ok else 1
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(TERMS)} terms under {CV_ONTOLOGY}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
