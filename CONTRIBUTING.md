# Contributing

Thanks for your interest in contributing to Background Remover!

## Development setup

1. Install Python 3.10 or newer.
2. Clone the repository and enter its directory.
3. Create a virtual environment:

   ```bash
   python -m venv .venv
   ```

4. Activate it and install development dependencies:

   ```bash
   # Linux/macOS
   source .venv/bin/activate

   # Windows PowerShell
   .venv\Scripts\Activate.ps1

   python -m pip install -r requirements-build.txt
   ```

5. Download the model for local development:

   ```bash
   python scripts/download_model.py
   ```

6. Run the application:

   ```bash
   python background_remover_app.py
   ```

## Pull requests

- Keep changes focused and explain the motivation in the pull request.
- Use clear English for code, comments, documentation, and commit messages.
- Run the local checks before opening a pull request:

  ```bash
  python -m compileall -q background_remover_app.py scripts
  ```

- Do not commit generated files, virtual environments, model weights, or build output.
- If you change packaging, test the affected platform workflow or document what was not tested.

## Model and data policy

Do not submit model weights or datasets unless their licenses clearly allow redistribution. The release workflow downloads the model during CI rather than storing it in Git.

## Issues

Use GitHub Issues for reproducible bugs and feature requests. Please include your operating system, release version, and relevant logs. Never include private images or other sensitive data in an issue.
