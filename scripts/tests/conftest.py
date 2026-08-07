"""Put the scripts directory on the import path.

Layer-2 scripts import each other as siblings (`analyze.py` imports `cannibal_detect.py`), which
works when a script is run directly because Python puts its own directory on `sys.path`. Tests live
one level down, so they have to reproduce that.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
