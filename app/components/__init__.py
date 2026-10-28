"""Streamlit UI components for HydroNet (thin; logic lives in hydronet.views)."""

import sys
from pathlib import Path

_SRC = str(Path(__file__).resolve().parents[2] / "src")
if _SRC not in sys.path:          # make `hydronet` importable however Streamlit (re)loads the pages
    sys.path.insert(0, _SRC)
