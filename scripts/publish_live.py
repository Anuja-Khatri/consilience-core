"""Publish the agreed set to Knowledge Pixels. See src/consilience/export/live.py.

    python scripts/publish_live.py keygen
    python scripts/publish_live.py plan
    python scripts/publish_live.py publish --confirm-permanent
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from consilience.export.live import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
