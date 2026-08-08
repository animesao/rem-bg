# Background Remover

[![CI](https://github.com/animesao/rem-bg/actions/workflows/ci.yml/badge.svg)](https://github.com/animesao/rem-bg/actions/workflows/ci.yml)
[![Latest release](https://img.shields.io/github/v/release/animesao/rem-bg)](https://github.com/animesao/rem-bg/releases)

A local, offline desktop application for removing image backgrounds. Select one image or an entire folder, process it on your own computer, and export transparent PNG files.

## Features

- Native desktop GUI built with Python and Tkinter.
- Fully local inference after installation; no image uploads and no API key.
- Single-image and folder processing.
- Transparent RGBA PNG output.
- Bundled `u2net` model in release builds.
- Automated GitHub builds for Windows and Ubuntu.
- Release assets: Windows `.exe` and Ubuntu/Debian `.deb`.
- English UI by default with a Russian language switch.
- Built-in version display and GitHub release update checker.
- Polished light desktop interface with progress feedback.

## Download

Download the latest release from the [GitHub Releases page](https://github.com/animesao/rem-bg/releases):

- `background-remover-windows-x64.exe` for 64-bit Windows.
- `background-remover-ubuntu-amd64.deb` for 64-bit Ubuntu/Debian.

The release binaries include the application, Python runtime, dependencies, and the `u2net` model. End users do not need Python or an internet connection after downloading the release.


## Windows

1. Download `background-remover-windows-x64.exe`.
2. Run it. Windows SmartScreen may show a warning because release binaries are not code-signed.
3. Add images or a folder, choose an output folder, and click **Remove background**.
4. Results are written as `<original-name>_nobg.png`.

## Ubuntu / Debian

Install the package:

```bash
sudo apt install ./background-remover-ubuntu-amd64.deb
```

Start it from the application menu or run:

```bash
background-remover
```

The package targets `amd64` Ubuntu/Debian systems. It requires a graphical desktop session.

## Build from source

### Requirements

- Python 3.10 or newer.
- A graphical desktop environment for running the GUI.
- Internet access during development setup to install packages and download `u2net`.

Create an environment and install build dependencies:

```bash
python -m venv .venv

# Linux/macOS
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -r requirements-build.txt
python scripts/download_model.py
```

Run from source:

```bash
python background_remover_app.py
```

### Build the executable

On Windows:

```powershell
python scripts/build_app.py
```

The executable is created at `dist/background-remover.exe`.

On Ubuntu/Debian:

```bash
python scripts/build_app.py
python scripts/package_deb.py 0.1.2
```

The package is created at `dist/background-remover_0.1.2_amd64.deb`.

> Build on the target operating system. Windows executables and Debian packages are produced by separate GitHub Actions runners.

## Automated releases

The repository includes two workflows:

- `CI` checks Python syntax on Ubuntu and Windows for pushes and pull requests.
- `Build and Release` builds both platform packages and publishes them to GitHub Releases.

To publish a release, push a semantic version tag:

```bash
git tag v0.1.2
git push origin v0.1.2
```

GitHub Actions will build:

```text
background-remover-windows-x64.exe
background-remover-ubuntu-amd64.deb
```

and attach both files to the new release. The workflow requires the repository's default `GITHUB_TOKEN` with `contents: write` permission; no custom secret is needed.

## Model and third-party notices

This project uses the open-source `rembg` runtime and the `u2net` model. Their licenses and notices are separate from this project's MIT license. Review the upstream notices before redistributing modified builds or using the project commercially.

The model is downloaded during CI and is intentionally not committed to Git because of its size and binary nature. The release workflow embeds it into each platform build.

## Privacy

Images are processed locally by the application. The application does not send images to a server. Internet access is only needed to download source dependencies/model during development or to download a prebuilt release from GitHub.

## License

The application source code is available under the [MIT License](LICENSE). See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for dependency and model notices.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and pull request guidelines.

## Security

See [SECURITY.md](SECURITY.md) for private vulnerability reporting guidance.
