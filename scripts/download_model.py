#!/usr/bin/env python3
"""Download the u2net model into the local build directory."""

from __future__ import annotations

import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT_DIR / "models"
MODEL_FILE = MODEL_DIR / "u2net.onnx"


def main() -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    os.environ["U2NET_HOME"] = str(MODEL_DIR)

    from rembg import new_session

    if not MODEL_FILE.exists():
        print("Downloading u2net model...")
        new_session("u2net")

    if not MODEL_FILE.exists():
        available = ", ".join(path.name for path in MODEL_DIR.iterdir())
        raise RuntimeError(
            f"u2net download completed, but {MODEL_FILE} was not found. "
            f"Model directory contains: {available or '(empty)'}"
        )

    print(f"Using model: {MODEL_FILE}")


if __name__ == "__main__":
    main()
