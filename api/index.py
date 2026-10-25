"""Vercel entry point: serves the FastAPI app from backend/ as one Python function.

vercel.json rewrites /api/* and /health here; the app still sees the original path.
"""

import sys
from pathlib import Path

# Vercel runs this file from the repository root, where backend/ is not importable.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.main import app  # noqa: E402

__all__ = ["app"]
