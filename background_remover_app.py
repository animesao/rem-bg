#!/usr/bin/env python3
"""Local GUI application for removing image backgrounds."""

from __future__ import annotations

import json
import os
import sys
import threading
import traceback
import urllib.error
import urllib.request
from collections.abc import Iterable
from io import BytesIO
from pathlib import Path
from tkinter import END, Listbox, StringVar, Tk, filedialog, messagebox
from tkinter import ttk

from app_info import APP_NAME, APP_VERSION, GITHUB_LATEST_RELEASE_API, GITHUB_RELEASES_URL
from image_processing import crop_transparent, remove_halo


def application_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def resource_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", application_dir()))
    return application_dir()


APP_DIR = application_dir()
RESOURCE_DIR = resource_dir()
MODEL_DIR = RESOURCE_DIR / "models"
DEFAULT_OUTPUT_DIR = Path.home() / "Background Remover" / "output"
SETTINGS_FILE = Path.home() / ".background-remover.json"
SUPPORTED_EXTENSIONS = {".bmp", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}

if not MODEL_DIR.exists() and not getattr(sys, "frozen", False):
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
os.environ["U2NET_HOME"] = str(MODEL_DIR)


TRANSLATIONS = {
    "en": {
        "subtitle": "Private, offline processing • transparent PNG output",
        "add_images": "Add images",
        "add_folder": "Add folder",
        "clear": "Clear",
        "images_to_process": "Images to process",
        "empty": "No images selected yet\nAdd one or more photos to get started",
        "output_folder": "Output folder",
        "change": "Change",
        "ready": "Ready when you are",
        "remove": "Remove background",
        "selected": "{count} image(s) selected",
        "choose_images": "Choose images",
        "choose_folder": "Choose an image folder",
        "choose_output": "Choose an output folder",
        "image_types": "Images",
        "all_files": "All files",
        "no_images": "No images",
        "add_first": "Add an image or folder first.",
        "loading": "Loading the u2net model...",
        "done_item": "Done: {name}",
        "failed_item": "Failed: {name}",
        "finished_errors": "Finished with errors: {done} of {total}",
        "some_failed": "Some files could not be processed:\n\n{items}",
        "processing_finished": "Processing finished",
        "done": "Done: {count} image(s)",
        "saved_to": "Files were saved to:\n{path}",
        "success": "Done",
        "model_failed": "Model loading failed",
        "could_not_start": "Could not start processing",
        "model_error": "The bundled u2net model could not be loaded.\n\n{details}",
        "version": "Version {version}",
        "language": "Language",
        "english": "English",
        "russian": "Русский",
        "check_updates": "Check for updates",
        "checking_updates": "Checking for updates...",
        "up_to_date": "You are up to date (v{version}).",
        "update_available": "Version {version} is available.",
        "update_error": "Could not check for updates. Check your internet connection.",
        "update_title": "Updates",
        "open_releases": "Open releases page",
        "local_processing": "Local processing",
        "local_detail": "Your images never leave this computer",
        "model_badge": "U²-Net model",
        "model_detail": "Runs offline after installation",
    },
    "ru": {
        "subtitle": "Локальная обработка без загрузки файлов • прозрачный PNG",
        "add_images": "Добавить фото",
        "add_folder": "Добавить папку",
        "clear": "Очистить",
        "images_to_process": "Файлы для обработки",
        "empty": "Пока нет выбранных изображений\nДобавьте одно или несколько фото",
        "output_folder": "Папка результата",
        "change": "Изменить",
        "ready": "Готово к работе",
        "remove": "Удалить фон",
        "selected": "Выбрано файлов: {count}",
        "choose_images": "Выберите изображения",
        "choose_folder": "Выберите папку с изображениями",
        "choose_output": "Выберите папку результата",
        "image_types": "Изображения",
        "all_files": "Все файлы",
        "no_images": "Нет изображений",
        "add_first": "Сначала добавьте фото или папку.",
        "loading": "Загрузка модели u2net...",
        "done_item": "Готово: {name}",
        "failed_item": "Ошибка: {name}",
        "finished_errors": "Завершено с ошибками: {done} из {total}",
        "some_failed": "Не удалось обработать некоторые файлы:\n\n{items}",
        "processing_finished": "Обработка завершена",
        "done": "Готово: {count} файл(ов)",
        "saved_to": "Файлы сохранены в:\n{path}",
        "success": "Готово",
        "model_failed": "Не удалось загрузить модель",
        "could_not_start": "Не удалось начать обработку",
        "model_error": "Не удалось загрузить встроенную модель u2net.\n\n{details}",
        "version": "Версия {version}",
        "language": "Язык",
        "english": "English",
        "russian": "Русский",
        "check_updates": "Проверить обновления",
        "checking_updates": "Проверка обновлений...",
        "up_to_date": "Установлена последняя версия (v{version}).",
        "update_available": "Доступна версия {version}.",
        "update_error": "Не удалось проверить обновления. Проверьте интернет.",
        "update_title": "Обновления",
        "open_releases": "Открыть страницу релизов",
        "local_processing": "Локальная обработка",
        "local_detail": "Файлы не покидают этот компьютер",
        "model_badge": "Модель U²-Net",
        "model_detail": "Работает без интернета после установки",
    },
}


def version_key(version: str) -> tuple[int, ...]:
    cleaned = version.strip().lstrip("vV").split("-")[0]
    numbers: list[int] = []
    for part in cleaned.split("."):
        digits = "".join(character for character in part if character.isdigit())
        numbers.append(int(digits or 0))
    return tuple((numbers + [0, 0, 0])[:3])


class BackgroundRemoverApp:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.root.title(f"{APP_NAME}  •  v{APP_VERSION}")
        self.root.geometry("860x760")
        self.root.minsize(760, 650)
        self.root.configure(bg="#f4f7fb")

        self.files: list[Path] = []
        self.processing_files: tuple[Path, ...] = ()
        self.processing_output_dir = DEFAULT_OUTPUT_DIR
        self.session: object | None = None
        self.busy = False
        self.output_dir = DEFAULT_OUTPUT_DIR
        self.language = self._load_language()
        self.status = StringVar()
        self.language_var = StringVar(value=self.language)
        self._text_widgets: dict[str, list[ttk.Widget]] = {}

        self._configure_style()
        self._build_ui()
        self._refresh_text()

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("App.TFrame", background="#f4f7fb")
        style.configure("Card.TFrame", background="#ffffff")
        style.configure("Title.TLabel", background="#f4f7fb", foreground="#12233f", font=("Segoe UI", 26, "bold"))
        style.configure("Subtitle.TLabel", background="#f4f7fb", foreground="#607089", font=("Segoe UI", 10))
        style.configure("CardTitle.TLabel", background="#ffffff", foreground="#12233f", font=("Segoe UI", 11, "bold"))
        style.configure("Body.TLabel", background="#ffffff", foreground="#607089", font=("Segoe UI", 9))
        style.configure("Muted.TLabel", background="#f4f7fb", foreground="#7889a1", font=("Segoe UI", 9))
        style.configure("Badge.TLabel", background="#e8f1ff", foreground="#2463b8", font=("Segoe UI", 9, "bold"), padding=(10, 5))
        style.configure("Accent.TButton", background="#2864d7", foreground="#ffffff", borderwidth=0, padding=(16, 10), font=("Segoe UI", 10, "bold"))
        style.map("Accent.TButton", background=[("active", "#1f50b1"), ("disabled", "#aabbd9")])
        style.configure("Secondary.TButton", background="#eef3fa", foreground="#28415f", borderwidth=0, padding=(12, 8), font=("Segoe UI", 9, "bold"))
        style.map("Secondary.TButton", background=[("active", "#dce8f8")])
        style.configure("Language.TButton", background="#ffffff", foreground="#2864d7", borderwidth=1, padding=(9, 5), font=("Segoe UI", 9, "bold"))
        style.configure("Horizontal.TProgressbar", troughcolor="#e4ebf5", background="#2864d7", borderwidth=0, thickness=8)

    def _label(self, parent: ttk.Widget, key: str, style: str = "Body.TLabel", **kwargs: object) -> ttk.Label:
        widget = ttk.Label(parent, style=style, **kwargs)
        self._text_widgets.setdefault(key, []).append(widget)
        return widget

    def _button(self, parent: ttk.Widget, key: str, command: object, style: str = "Secondary.TButton") -> ttk.Button:
        widget = ttk.Button(parent, style=style, command=command)
        self._text_widgets.setdefault(key, []).append(widget)
        return widget

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, style="App.TFrame", padding=(34, 28, 34, 24))
        container.pack(fill="both", expand=True)
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(2, weight=1)

        header = ttk.Frame(container, style="App.TFrame")
        header.grid(row=0, column=0, sticky="ew")
        title_block = ttk.Frame(header, style="App.TFrame")
        title_block.pack(side="left")
        ttk.Label(title_block, text=APP_NAME, style="Title.TLabel").pack(anchor="w")
        self._label(title_block, "subtitle", style="Subtitle.TLabel").pack(anchor="w", pady=(4, 0))
        self.version_label = ttk.Label(
            title_block, text=self._t("version", version=APP_VERSION), style="Muted.TLabel"
        )
        self.version_label.pack(anchor="w", pady=(8, 0))

        header_actions = ttk.Frame(header, style="App.TFrame")
        header_actions.pack(side="right", anchor="n")
        ttk.Label(header_actions, text="EN / RU", style="Muted.TLabel").pack(anchor="e")
        language_row = ttk.Frame(header_actions, style="App.TFrame")
        language_row.pack(anchor="e", pady=(4, 0))
        self._button(language_row, "english", self._set_english, "Language.TButton").pack(side="left")
        self._button(language_row, "russian", self._set_russian, "Language.TButton").pack(side="left", padx=(4, 0))
        self._button(header_actions, "check_updates", self.check_for_updates, "Language.TButton").pack(anchor="e", pady=(10, 0))

        badges = ttk.Frame(container, style="App.TFrame")
        badges.grid(row=1, column=0, sticky="ew", pady=(22, 18))
        self._add_badge(badges, "local_processing", "local_detail")
        self._add_badge(badges, "model_badge", "model_detail")

        card = ttk.Frame(container, style="Card.TFrame", padding=20)
        card.grid(row=2, column=0, sticky="nsew")
        self._label(card, "images_to_process", style="CardTitle.TLabel").pack(anchor="w")

        actions = ttk.Frame(card, style="Card.TFrame")
        actions.pack(fill="x", side="bottom")
        self._button(actions, "add_images", self.add_files).pack(side="left")
        self._button(actions, "add_folder", self.add_folder).pack(side="left", padx=(8, 0))
        self._button(actions, "clear", self.clear_files).pack(side="right")

        list_frame = ttk.Frame(card, style="Card.TFrame")
        list_frame.pack(fill="both", expand=True, pady=(14, 14))
        self.file_list = Listbox(list_frame, selectmode="extended", activestyle="none", borderwidth=0, highlightthickness=1, highlightcolor="#cbd9ec", bg="#f8fafd", fg="#29415e", selectbackground="#dce9ff", selectforeground="#173c74", font=("Segoe UI", 10), relief="flat")
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.file_list.yview)
        self.file_list.configure(yscrollcommand=scrollbar.set)
        self.file_list.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        # Create the placeholder after the list so it stays visibly above it.
        self.empty_label = self._label(list_frame, "empty", style="Body.TLabel")
        self.empty_label.place(relx=0.5, rely=0.5, anchor="center")

        output_row = ttk.Frame(container, style="App.TFrame")
        output_row.grid(row=3, column=0, sticky="ew", pady=(18, 0))
        self._label(output_row, "output_folder", style="Muted.TLabel").pack(side="left")
        self.output_label = ttk.Label(output_row, text=str(self.output_dir), style="Muted.TLabel")
        self.output_label.pack(side="left", padx=(8, 0))
        self._button(output_row, "change", self.choose_output).pack(side="right")

        self.progress = ttk.Progressbar(container, style="Horizontal.TProgressbar", mode="determinate")
        self.progress.grid(row=4, column=0, sticky="ew", pady=(18, 8))
        ttk.Label(container, textvariable=self.status, style="Muted.TLabel").grid(
            row=5, column=0, sticky="w"
        )
        self.process_button = self._button(container, "remove", self.start_processing, "Accent.TButton")
        self.process_button.grid(row=6, column=0, sticky="ew", pady=(14, 0), ipady=5)

    def _add_badge(self, parent: ttk.Widget, title_key: str, detail_key: str) -> None:
        badge = ttk.Frame(parent, style="Card.TFrame", padding=(12, 8))
        badge.pack(side="left", padx=(0, 10))
        self._label(badge, title_key, style="CardTitle.TLabel").pack(anchor="w")
        self._label(badge, detail_key, style="Body.TLabel").pack(anchor="w", pady=(2, 0))

    def _t(self, key: str, **kwargs: object) -> str:
        return TRANSLATIONS[self.language][key].format(**kwargs)

    def _refresh_text(self) -> None:
        for key, widgets in self._text_widgets.items():
            text = self._t(key)
            for widget in widgets:
                widget.configure(text=text)
        self.version_label.configure(text=self._t("version", version=APP_VERSION))
        self._update_language_button_styles()
        if not self.files and not self.busy:
            self.status.set(self._t("ready"))

    def _update_language_button_styles(self) -> None:
        # Keep the active language visibly selected without introducing a custom widget.
        for widget in self._text_widgets.get("english", []):
            widget.configure(style="Accent.TButton" if self.language == "en" else "Language.TButton")
        for widget in self._text_widgets.get("russian", []):
            widget.configure(style="Accent.TButton" if self.language == "ru" else "Language.TButton")

    def _load_language(self) -> str:
        try:
            value = json.loads(SETTINGS_FILE.read_text(encoding="utf-8")).get("language", "en")
            return value if value in TRANSLATIONS else "en"
        except (OSError, ValueError, AttributeError):
            return "en"

    def _set_language(self, language: str) -> None:
        self.language = language
        self.language_var.set(language)
        try:
            SETTINGS_FILE.write_text(json.dumps({"language": language}), encoding="utf-8")
        except OSError:
            pass
        self._refresh_text()

    def _set_english(self) -> None:
        self._set_language("en")

    def _set_russian(self) -> None:
        self._set_language("ru")

    def add_files(self) -> None:
        paths = filedialog.askopenfilenames(title=self._t("choose_images"), filetypes=[(self._t("image_types"), " ".join(f"*{extension}" for extension in sorted(SUPPORTED_EXTENSIONS))), (self._t("all_files"), "*.*")])
        self._add_paths(Path(path) for path in paths)

    def add_folder(self) -> None:
        selected = filedialog.askdirectory(title=self._t("choose_folder"))
        if not selected:
            return
        folder = Path(selected)
        self._add_paths(path for path in sorted(folder.iterdir()) if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS)

    def _add_paths(self, paths: Iterable[Path]) -> None:
        existing = set(self.files)
        added = False
        for path in paths:
            if path not in existing:
                self.files.append(path)
                existing.add(path)
                self.file_list.insert(END, str(path))
                added = True
        if added:
            self.empty_label.place_forget()
            self.status.set(self._t("selected", count=len(self.files)))
        elif not self.files:
            self.status.set(self._t("ready"))

    def clear_files(self) -> None:
        if self.busy:
            return
        self.files.clear()
        self.file_list.delete(0, END)
        self.empty_label.place(relx=0.5, rely=0.5, anchor="center")
        self.progress.configure(value=0)
        self._refresh_text()

    def choose_output(self) -> None:
        selected = filedialog.askdirectory(title=self._t("choose_output"), initialdir=str(self.output_dir))
        if selected:
            self.output_dir = Path(selected)
            self.output_label.configure(text=str(self.output_dir))

    def start_processing(self) -> None:
        if self.busy:
            return
        if not self.files:
            messagebox.showinfo(self._t("no_images"), self._t("add_first"))
            return
        self.busy = True
        self.processing_files = tuple(self.files)
        self.processing_output_dir = self.output_dir
        self._set_processing_controls(False)
        self.progress.configure(maximum=len(self.processing_files), value=0)
        self.status.set(self._t("loading"))
        threading.Thread(target=self._process_in_background, daemon=True).start()

    def _set_processing_controls(self, enabled: bool) -> None:
        for key in ("add_images", "add_folder", "clear", "change", "check_updates"):
            self._button_set_enabled(key, enabled)
        self.process_button.configure(state="normal" if enabled else "disabled")

    def _process_in_background(self) -> None:
        files = self.processing_files
        output_dir = self.processing_output_dir
        try:
            from PIL import Image
            from rembg import new_session, remove
            if self.session is None:
                self.session = new_session("u2net")
            output_dir.mkdir(parents=True, exist_ok=True)
            failed: list[str] = []
            for index, input_path in enumerate(files, start=1):
                destination = output_dir / f"{input_path.stem}_nobg.png"
                try:
                    result_bytes = remove(input_path.read_bytes(), session=self.session)
                    with Image.open(BytesIO(result_bytes)) as result:
                        clean_result = remove_halo(result, soft_threshold=40)
                        crop_transparent(clean_result, padding=20).save(
                            destination, format="PNG", optimize=True
                        )
                    self.root.after(0, self._update_progress, index, self._t("done_item", name=input_path.name))
                except Exception as error:
                    failed.append(f"{input_path.name}: {error}")
                    self.root.after(0, self._update_progress, index, self._t("failed_item", name=input_path.name))
            self.root.after(0, self._processing_finished, failed)
        except Exception as error:
            details = "".join(traceback.format_exception_only(type(error), error)).strip()
            self.root.after(0, self._processing_failed, details)

    def _update_progress(self, value: int, text: str) -> None:
        self.progress.configure(value=value)
        self.status.set(text)

    def _processing_finished(self, failed: list[str]) -> None:
        self.busy = False
        self._set_processing_controls(True)
        if failed:
            self.status.set(self._t("finished_errors", done=len(self.processing_files) - len(failed), total=len(self.processing_files)))
            messagebox.showwarning(self._t("processing_finished"), self._t("some_failed", items="\n".join(failed[:8])))
        else:
            self.status.set(self._t("done", count=len(self.processing_files)))
            messagebox.showinfo(self._t("success"), self._t("saved_to", path=self.processing_output_dir))

    def _processing_failed(self, details: str) -> None:
        self.busy = False
        self._set_processing_controls(True)
        self.status.set(self._t("model_failed"))
        messagebox.showerror(self._t("could_not_start"), self._t("model_error", details=details))

    def check_for_updates(self) -> None:
        if self.busy:
            return
        self.status.set(self._t("checking_updates"))
        self._button_set_enabled("check_updates", False)
        threading.Thread(target=self._check_updates_background, daemon=True).start()

    def _check_updates_background(self) -> None:
        try:
            request = urllib.request.Request(GITHUB_LATEST_RELEASE_API, headers={"User-Agent": "background-remover"})
            with urllib.request.urlopen(request, timeout=6) as response:
                payload = json.loads(response.read().decode("utf-8"))
            latest = str(payload.get("tag_name", "")).lstrip("v")
            if not latest:
                raise ValueError("GitHub response did not contain a release tag")
            self.root.after(0, self._update_check_finished, latest)
        except (OSError, ValueError, json.JSONDecodeError, urllib.error.URLError):
            self.root.after(0, self._update_check_failed)

    def _button_set_enabled(self, key: str, enabled: bool) -> None:
        for widget in self._text_widgets.get(key, []):
            widget.configure(state="normal" if enabled else "disabled")

    def _update_check_finished(self, latest: str) -> None:
        self._button_set_enabled("check_updates", True)
        if version_key(latest) > version_key(APP_VERSION):
            self.status.set(self._t("update_available", version=latest))
            if messagebox.askyesno(self._t("update_title"), f"{self._t('update_available', version=latest)}\n\n{GITHUB_RELEASES_URL}\n\n{self._t('open_releases')}" ):
                self._open_releases_page()
        else:
            self.status.set(self._t("up_to_date", version=APP_VERSION))
            messagebox.showinfo(self._t("update_title"), self._t("up_to_date", version=APP_VERSION))

    def _update_check_failed(self) -> None:
        self._button_set_enabled("check_updates", True)
        self.status.set(self._t("update_error"))
        messagebox.showwarning(self._t("update_title"), self._t("update_error"))

    def _open_releases_page(self) -> None:
        import webbrowser
        webbrowser.open(GITHUB_RELEASES_URL)


def main() -> None:
    root = Tk()
    BackgroundRemoverApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
