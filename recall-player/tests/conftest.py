from __future__ import annotations

import sys
from pathlib import Path

RECALL_PLAYER_ROOT = Path(__file__).resolve().parents[1]
if str(RECALL_PLAYER_ROOT) not in sys.path:
    sys.path.insert(0, str(RECALL_PLAYER_ROOT))
