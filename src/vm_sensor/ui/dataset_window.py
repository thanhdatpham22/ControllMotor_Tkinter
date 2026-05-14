import tkinter as tk
from tkinter import ttk

from vm_sensor.config import OUTPUT_DIR
from vm_sensor.ui.base_window import BaseWindow


class DatasetWindow(BaseWindow):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._build_ui()
        self._refresh_saved_list()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        ttk.Label(self, text="Saved outputs", style="Header.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 8)
        )

        self.saved_listbox = tk.Listbox(
            self,
            font=("Consolas", 10),
            height=20,
            activestyle="none",
        )
        self.saved_listbox.grid(row=1, column=0, sticky="nsew")

        info_box = ttk.Frame(self, padding=(0, 12, 0, 0))
        info_box.grid(row=2, column=0, sticky="ew")
        ttk.Label(info_box, text=f"Output folder: {OUTPUT_DIR}", style="Status.TLabel").pack(
            side="left"
        )
        ttk.Button(info_box, text="Refresh List", command=self._refresh_saved_list).pack(
            side="right"
        )

    def _refresh_saved_list(self) -> None:
        self.saved_listbox.delete(0, tk.END)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        items = sorted(
            OUTPUT_DIR.glob("capture_*"),
            key=lambda path: path.stat().st_mtime,
        )
        for item in items[-30:]:
            self.saved_listbox.insert(tk.END, item.name)

        if not items:
            self.saved_listbox.insert(tk.END, "No capture saved yet.")
