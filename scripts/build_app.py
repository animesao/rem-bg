#!/usr/bin/env python3
"""Build a standalone Background Remover executable with PyInstaller."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
MODEL_FILE = ROOT_DIR / "models" / "u2net.onnx"
DIST_DIR = ROOT_DIR / "dist"
BUILD_DIR = ROOT_DIR / "build"
APP_NAME = "background-remover"


def main() -> None:
    if not MODEL_FILE.is_file():
        raise FileNotFoundError(
            f"Missing {MODEL_FILE}. Run scripts/download_model.py first."
        )

    separator = ";" if sys.platform == "win32" else ":"
    pyinstaller = shutil.which("pyinstaller")
    command = [
        pyinstaller if pyinstaller else sys.executable,
        *([] if pyinstaller else ["-m", "PyInstaller"]),
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name",
        APP_NAME,
        "--distpath",
        str(DIST_DIR),
        "--workpath",
        str(BUILD_DIR),
        "--specpath",
        str(BUILD_DIR),
        "--add-data",
        f"{MODEL_FILE}{separator}models",
        "--collect-all",
        "rembg",
        "--collect-all",
        "onnxruntime",
        "--collect-all",
        "pymatting",
        "--hidden-import",
        "rembg.sessions.u2net",
        "--hidden-import",
        "onnxruntime.capi.onnxruntime_pybind11_state",
        str(ROOT_DIR / "background_remover_app.py"),
    ]

    DIST_DIR.mkdir(exist_ok=True)
    subprocess.run(command, cwd=ROOT_DIR, check=True)
    print(f"Built: {DIST_DIR / (APP_NAME + ('.exe' if sys.platform == 'win32' else ''))}")


if __name__ == "__main__":
    main()
