#!/usr/bin/env python3
"""Автономное удаление фона: python remove_bg.py photo.png"""

from __future__ import annotations

import argparse
import importlib.util
import os
import subprocess
import sys
from io import BytesIO
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
MODEL_DIR = ROOT_DIR / "models"
OUTPUT_DIR = ROOT_DIR / "output"
REQUIREMENTS_FILE = ROOT_DIR / "requirements.txt"
VENV_PYTHON = ROOT_DIR / ".venv" / "Scripts" / "python.exe"
SUPPORTED_EXTENSIONS = {".bmp", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}


def is_project_python() -> bool:
    """Проверяет, запущен ли скрипт Python из локального .venv."""
    try:
        return Path(sys.executable).resolve() == VENV_PYTHON.resolve()
    except OSError:
        return False


def dependencies_are_installed() -> bool:
    return all(
        importlib.util.find_spec(module) is not None
        for module in ("PIL", "rembg")
    )


def install_dependencies() -> None:
    """Устанавливает зависимости в текущий Python, если их ещё нет."""
    if not REQUIREMENTS_FILE.exists():
        raise FileNotFoundError(f"Не найден файл зависимостей: {REQUIREMENTS_FILE}")

    print("Устанавливаю необходимые библиотеки (это делается только один раз)...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS_FILE)],
        cwd=ROOT_DIR,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Не удалось установить библиотеки. Проверьте интернет и повторите запуск."
        )


def create_virtual_environment() -> None:
    print("Создаю локальное виртуальное окружение .venv...")
    result = subprocess.run(
        [sys.executable, "-m", "venv", str(ROOT_DIR / ".venv")],
        cwd=ROOT_DIR,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Не удалось создать .venv. Установите Python с официального сайта "
            "и включите опцию Add python.exe to PATH."
        )


def restart_in_project_environment() -> int | None:
    """Запускает этот же файл через .venv, чтобы команда была действительно простой."""
    if not VENV_PYTHON.exists():
        create_virtual_environment()

    if not is_project_python():
        print("Перезапускаю скрипт в локальном окружении проекта...")
        completed = subprocess.run(
            [str(VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]],
            # Сохраняем текущую папку пользователя, чтобы относительный путь к фото
            # (например, photo.png) не изменился при перезапуске в .venv.
            cwd=Path.cwd(),
            env=os.environ.copy(),
        )
        return completed.returncode

    # Проверяем зависимости уже после перехода в .venv. Иначе первый запуск
    # мог попасть в чистое окружение без rembg и завершиться ошибкой импорта.
    if not dependencies_are_installed():
        install_dependencies()

    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Удаляет фон и сохраняет прозрачный PNG. Модель u2net выбирается автоматически."
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Путь к фото или папке с фото.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=OUTPUT_DIR,
        help="Папка результатов (по умолчанию: output рядом со скриптом).",
    )
    return parser.parse_args()


def collect_images(input_path: Path) -> list[Path]:
    if input_path.is_file():
        if input_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"Неподдерживаемый формат: {input_path.suffix}")
        return [input_path]

    if input_path.is_dir():
        return sorted(
            path
            for path in input_path.iterdir()
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
        )

    raise FileNotFoundError(f"Путь не найден: {input_path}")


def process_image(input_path: Path, destination: Path, session: object) -> None:
    # Импорты выполняются после bootstrap, поэтому обычная команда python remove_bg.py
    # работает даже в чистом Python без предварительной установки rembg вручную.
    from PIL import Image
    from rembg import remove
    from image_processing import crop_transparent, remove_halo

    result_bytes = remove(input_path.read_bytes(), session=session)
    with Image.open(BytesIO(result_bytes)) as result:
        clean_result = remove_halo(result, soft_threshold=40)
        crop_transparent(clean_result, padding=20).save(
            destination, format="PNG", optimize=True
        )


def main() -> int:
    try:
        runtime_result = restart_in_project_environment()
        if runtime_result is not None:
            return runtime_result
    except (OSError, RuntimeError, FileNotFoundError) as error:
        print(f"Ошибка подготовки окружения: {error}", file=sys.stderr)
        return 1

    # U2NET_HOME задаётся до импорта rembg. Модель u2net будет автоматически
    # скачана один раз в папку models рядом с этим файлом и затем переиспользована.
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    os.environ["U2NET_HOME"] = str(MODEL_DIR)

    try:
        args = parse_args()
        images = collect_images(args.input)
        if not images:
            print(f"В папке нет поддерживаемых изображений: {args.input}", file=sys.stderr)
            return 1
        args.output.mkdir(parents=True, exist_ok=True)
    except (FileNotFoundError, ValueError, OSError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1

    print("Модель: u2net (выбрана автоматически)")
    print("Если это первый запуск, модель скачивается в папку models...")

    try:
        from rembg import new_session

        session = new_session("u2net")
    except Exception as error:
        print(f"Не удалось загрузить модель u2net: {error}", file=sys.stderr)
        print("Проверьте интернет-соединение и запустите команду ещё раз.", file=sys.stderr)
        return 1

    failed = 0
    for image_path in images:
        destination = args.output / f"{image_path.stem}_nobg.png"
        try:
            process_image(image_path, destination, session)
            print(f"Готово: {image_path} -> {destination}")
        except Exception as error:
            failed += 1
            print(f"Ошибка в {image_path}: {error}", file=sys.stderr)

    print(f"\nОбработано: {len(images) - failed} из {len(images)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
