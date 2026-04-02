#!/usr/bin/env python3
import os
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))
os.environ.setdefault("NODE_NO_WARNINGS", "1")

from browser_agent.controller import main


if __name__ == "__main__":
    raise SystemExit(main())
