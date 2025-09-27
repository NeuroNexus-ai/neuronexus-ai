# Path from repo root: streamlit\core\constants.py

# streamlit/core/constants.py
from __future__ import annotations
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
STREAMLIT_DIR = APP_DIR / ".streamlit"
SERVERS_STORE = STREAMLIT_DIR / "servers.json"
CSS_PATH = STREAMLIT_DIR / "neuroserve.css"