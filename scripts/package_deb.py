#!/usr/bin/env python3
"""Create an amd64 .deb package from the standalone Linux executable."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
DIST_DIR = ROOT_DIR / "dist"
PACKAGE_ROOT = ROOT_DIR / "build" / "deb-root"
PACKAGE_NAME = "background-remover"


def deb_version(value: str) -> str:
    cleaned = value.lstrip("v")
    cleaned = re.sub(r"[^0-9A-Za-z.+~-]", "-", cleaned)
    return cleaned or "0.0.0"


def main() -> None:
    if sys.platform != "linux":
        raise RuntimeError("Debian packages can only be built on Linux.")

    executable = DIST_DIR / PACKAGE_NAME
    if not executable.is_file():
        raise FileNotFoundError(f"Missing Linux executable: {executable}")

    version = deb_version(sys.argv[1] if len(sys.argv) > 1 else "0.0.0")
    if PACKAGE_ROOT.exists():
        shutil.rmtree(PACKAGE_ROOT)

    binary_dir = PACKAGE_ROOT / "usr" / "lib" / PACKAGE_NAME
    desktop_dir = PACKAGE_ROOT / "usr" / "share" / "applications"
    control_dir = PACKAGE_ROOT / "DEBIAN"
    binary_dir.mkdir(parents=True)
    desktop_dir.mkdir(parents=True)
    control_dir.mkdir(parents=True)

    packaged_binary = binary_dir / PACKAGE_NAME
    shutil.copy2(executable, packaged_binary)
    packaged_binary.chmod(0o755)

    launcher_dir = PACKAGE_ROOT / "usr" / "bin"
    launcher_dir.mkdir(parents=True)
    launcher = launcher_dir / PACKAGE_NAME
    launcher.symlink_to(Path("..") / "lib" / PACKAGE_NAME / PACKAGE_NAME)

    (desktop_dir / f"{PACKAGE_NAME}.desktop").write_text(
        "[Desktop Entry]\n"
        "Name=Background Remover\n"
        "Comment=Remove image backgrounds locally\n"
        "Exec=/usr/bin/background-remover\n"
        "Terminal=false\n"
        "Type=Application\n"
        "Categories=Graphics;Utility;\n",
        encoding="utf-8",
    )

    (control_dir / "control").write_text(
        f"Package: {PACKAGE_NAME}\n"
        f"Version: {version}\n"
        "Section: graphics\n"
        "Priority: optional\n"
        "Architecture: amd64\n"
        "Maintainer: Background Remover Contributors <noreply@example.com>\n"
        "Depends: libc6, libglib2.0-0, libx11-6, libxext6, libxrender1, libxrandr2, libfontconfig1\n"
        "Description: Local AI background remover\n"
        " A private, offline desktop application for removing image backgrounds.\n",
        encoding="utf-8",
    )

    output = DIST_DIR / f"{PACKAGE_NAME}_{version}_amd64.deb"
    subprocess.run(
        [
            "dpkg-deb",
            "--build",
            "--root-owner-group",
            str(PACKAGE_ROOT),
            str(output),
        ],
        check=True,
    )
    print(f"Built: {output}")


if __name__ == "__main__":
    main()
