#!/usr/bin/env python3
"""Local GUI application for removing image backgrounds."""

from __future__ import annotations

import os
import sys
import threading
import traceback
from collections.abc import Iterable
from io import BytesIO
from pathlib import Path
from tkinter import END, Listbox, StringVar, Tk, filedialog, messagebox
from tkinter import ttk


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
# Keep generated files in a user-writable location. This matters for Debian
# installs, where APP_DIR is normally under /usr/lib.
DEFAULT_OUTPUT_DIR = Path.home() / "Background Remover" / "output"
SUPPORTED_EXTENSIONS = {".bmp", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}

# rembg reads U2NET_HOME when creating its session. In packaged builds this points
# to the bundled, read-only model extracted by PyInstaller.
if not MODEL_DIR.exists() and not getattr(sys, "frozen", False):
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
os.environ["U2NET_HOME"] = str(MODEL_DIR)


class BackgroundRemoverApp:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.root.title("Background Remover — Local")
        self.root.geometry("720x560")
        self.root.minsize(620, 460)

        self.files: list[Path] = []
        self.session: object | None = None
        self.busy = False
        self.output_dir = DEFAULT_OUTPUT_DIR
        self.status = StringVar(value="Choose one or more images")

        self._build_ui()

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, padding=24)
        container.pack(fill="both", expand=True)

        ttk.Label(
            container,
            text="Background Remover",
            font=("Segoe UI", 22, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            container,
            text="Runs locally • u2net model • transparent PNG output",
        ).pack(anchor="w", pady=(4, 20))

        actions = ttk.Frame(container)
        actions.pack(fill="x")
        ttk.Button(actions, text="Add images", command=self.add_files).pack(side="left")
        ttk.Button(
            actions, text="Add folder", command=self.add_folder
        ).pack(side="left", padx=(8, 0))
        ttk.Button(
            actions, text="Clear list", command=self.clear_files
        ).pack(side="right")

        list_frame = ttk.LabelFrame(container, text="Images to process", padding=10)
        list_frame.pack(fill="both", expand=True, pady=16)
        self.file_list = Listbox(
            list_frame,
            selectmode="extended",
            activestyle="none",
            borderwidth=0,
            highlightthickness=0,
            font=("Segoe UI", 10),
        )
        scrollbar = ttk.Scrollbar(
            list_frame, orient="vertical", command=self.file_list.yview
        )
        self.file_list.configure(yscrollcommand=scrollbar.set)
        self.file_list.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        output_row = ttk.Frame(container)
        output_row.pack(fill="x", pady=(0, 12))
        ttk.Label(output_row, text="Output folder:").pack(side="left")
        self.output_label = ttk.Label(
            output_row, text=str(self.output_dir), foreground="#555555"
        )
        self.output_label.pack(side="left", padx=8)
        ttk.Button(output_row, text="Change", command=self.choose_output).pack(
            side="right"
        )

        self.progress = ttk.Progressbar(container, mode="determinate")
        self.progress.pack(fill="x", pady=(0, 8))
        ttk.Label(container, textvariable=self.status).pack(anchor="w")

        self.process_button = ttk.Button(
            container,
            text="Remove background",
            command=self.start_processing,
        )
        self.process_button.pack(fill="x", pady=(16, 0), ipady=7)

    def add_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Choose images",
            filetypes=[
                (
                    "Images",
                    " ".join(f"*{extension}" for extension in sorted(SUPPORTED_EXTENSIONS)),
                ),
                ("All files", "*.*"),
            ],
        )
        self._add_paths(Path(path) for path in paths)

    def add_folder(self) -> None:
        selected = filedialog.askdirectory(title="Choose an image folder")
        if not selected:
            return
        folder = Path(selected)
        self._add_paths(
            path
            for path in sorted(folder.iterdir())
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
        )

    def _add_paths(self, paths: Iterable[Path]) -> None:
        existing = set(self.files)
        for path in paths:
            if path not in existing:
                self.files.append(path)
                existing.add(path)
                self.file_list.insert(END, str(path))
        self.status.set(f"Selected images: {len(self.files)}")

    def clear_files(self) -> None:
        if self.busy:
            return
        self.files.clear()
        self.file_list.delete(0, END)
        self.progress.configure(value=0)
        self.status.set("Choose one or more images")

    def choose_output(self) -> None:
        selected = filedialog.askdirectory(
            title="Choose an output folder", initialdir=str(self.output_dir)
        )
        if selected:
            self.output_dir = Path(selected)
            self.output_label.configure(text=str(self.output_dir))

    def start_processing(self) -> None:
        if self.busy:
            return
        if not self.files:
            messagebox.showinfo("No images", "Add an image or folder first.")
            return

        self.busy = True
        self.process_button.configure(state="disabled")
        self.progress.configure(maximum=len(self.files), value=0)
        self.status.set("Loading the u2net model...")
        threading.Thread(target=self._process_in_background, daemon=True).start()

    def _process_in_background(self) -> None:
        try:
            from PIL import Image
            from rembg import new_session, remove

            if self.session is None:
                self.session = new_session("u2net")

            self.output_dir.mkdir(parents=True, exist_ok=True)
            failed: list[str] = []
            for index, input_path in enumerate(self.files, start=1):
                destination = self.output_dir / f"{input_path.stem}_nobg.png"
                try:
                    result_bytes = remove(input_path.read_bytes(), session=self.session)
                    with Image.open(BytesIO(result_bytes)) as result:
                        result.convert("RGBA").save(
                            destination, format="PNG", optimize=True
                        )
                    self.root.after(
                        0, self._update_progress, index, f"Done: {input_path.name}"
                    )
                except Exception as error:  # keep processing remaining files
                    failed.append(f"{input_path.name}: {error}")
                    self.root.after(
                        0, self._update_progress, index, f"Failed: {input_path.name}"
                    )

            self.root.after(0, self._processing_finished, failed)
        except Exception as error:
            details = "".join(traceback.format_exception_only(type(error), error)).strip()
            self.root.after(0, self._processing_failed, details)

    def _update_progress(self, value: int, text: str) -> None:
        self.progress.configure(value=value)
        self.status.set(text)

    def _processing_finished(self, failed: list[str]) -> None:
        self.busy = False
        self.process_button.configure(state="normal")
        if failed:
            self.status.set(
                f"Finished with errors: {len(self.files) - len(failed)} of {len(self.files)}"
            )
            messagebox.showwarning(
                "Processing finished",
                "Some files could not be processed:\n\n" + "\n".join(failed[:8]),
            )
        else:
            self.status.set(f"Done: {len(self.files)} images")
            messagebox.showinfo(
                "Done",
                f"Files were saved to:\n{self.output_dir}",
            )

    def _processing_failed(self, details: str) -> None:
        self.busy = False
        self.process_button.configure(state="normal")
        self.status.set("Model loading failed")
        messagebox.showerror(
            "Could not start processing",
            "The bundled u2net model could not be loaded.\n\n" + details,
        )


def main() -> None:
    root = Tk()
    try:
        ttk.Style(root).theme_use("vista")
    except Exception:
        pass
    BackgroundRemoverApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
