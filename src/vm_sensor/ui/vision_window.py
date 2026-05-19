import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import numpy as np
from vm_sensor.ui.base_window import BaseWindow
from vm_sensor.utils.image_utils import to_photo_image
from vm_sensor.config import PREVIEW_WIDTH, PREVIEW_HEIGHT
from vm_sensor.models import SegmentResult

class VisionWindow(BaseWindow):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        
        self.segment_mode_var = tk.StringVar(value=self.app.segmenter.status_message)
        
        self.save_yolo_var = tk.BooleanVar(value=False)
        self.save_json_var = tk.BooleanVar(value=False)
        self.source_summary_var = tk.StringVar(value="Source: OpenCV camera #0")

        self.segment_result: SegmentResult | None = None
        self.realtime_photo = None
        self.segment_photo = None
        
        self.cell_colors = {}

        self._build_ui()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=3)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        left_side = ttk.Frame(self, padding=0)
        left_side.grid(row=0, column=0, sticky="nsew")
        left_side.columnconfigure(0, weight=1)
        left_side.rowconfigure(0, weight=1)

        # ================= RIGHT SIDE: TUNING & MONITORING =================
        right_side = ttk.Frame(self, padding=0)
        right_side.grid(row=0, column=1, sticky="nsew", padx=(5,5), pady=(0,0))
        right_side.columnconfigure(0, weight=1)
        right_side.rowconfigure(0, weight=0)
        right_side.rowconfigure(1, weight=0)
        right_side.rowconfigure(2, weight=1)
        
        # ================= LEFT SIDE: IMAGES & TRAYS =================
        viewers = ttk.Frame(left_side)
        viewers.grid(row=0, column=0, sticky="nsew", pady=(0, 0))
        viewers.columnconfigure(0, weight=1)
        viewers.columnconfigure(1, weight=1)
        viewers.rowconfigure(0, weight=0) # row for images (fixed height)
        viewers.rowconfigure(1, weight=1) # row for trays (stretches vertically)

        realtime_box = ttk.LabelFrame(viewers, text="Realtime View", padding=5)
        realtime_box.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        segment_box = ttk.LabelFrame(viewers, text="Segment View", padding=5)
        segment_box.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

        # Set preview dimensions to exactly match camera resolution (659x494)
        self.p_w, self.p_h = 659, 494
        self.realtime_label = ttk.Label(realtime_box, anchor="center")
        self.realtime_label.pack(fill="both", expand=True)
        self.segment_label = ttk.Label(segment_box, anchor="center")
        self.segment_label.pack(fill="both", expand=True)

        # Initialize segment view with a "None" placeholder of 659x494 at startup
        placeholder = np.zeros((494, 659, 3), dtype=np.uint8)
        placeholder[:] = (26, 26, 26)
        cv2.putText(
            placeholder,
            "None",
            (290, 260),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.5,
            (100, 100, 100),
            2,
            cv2.LINE_AA,
        )
        self.segment_photo = to_photo_image(placeholder, 659, 494)
        self.segment_label.configure(image=self.segment_photo)

        # Tray Map 1 under Realtime View
        tray1_box = ttk.LabelFrame(viewers, text="Tray Map 1 (15x5)", padding=0)
        tray1_box.grid(row=1, column=0, sticky="nsew", padx=(0, 4), pady=(0, 0))
        self.tray_canvas1 = tk.Canvas(tray1_box, bg="#1a1a1a", height=180)
        self.tray_canvas1.pack(fill="both", expand=True)

        # Tray Map 2 under Segment View
        tray2_box = ttk.LabelFrame(viewers, text="Tray Map 2 (15x5)", padding=0)
        tray2_box.grid(row=1, column=1, sticky="nsew", padx=(4, 0), pady=(0, 0))
        self.tray_canvas2 = tk.Canvas(tray2_box, bg="#1a1a1a", height=180)
        self.tray_canvas2.pack(fill="both", expand=True)

        # Action Buttons on Right Side
        button_frame = ttk.Frame(right_side, padding=(0, 5))
        button_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        ttk.Button(button_frame, text="Capture", style="Primary.TButton", command=self._capture_segment).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Save", style="Primary.TButton", command=self._save_capture).pack(side="left", padx=5)
        self.prev_image_button = ttk.Button(button_frame, text="Prev", command=self._previous_folder_image)
        self.prev_image_button.pack(side="left", padx=5)
        self.next_image_button = ttk.Button(button_frame, text="Next", command=self._next_folder_image)
        self.next_image_button.pack(side="left", padx=5)

        ttk.Checkbutton(button_frame, text="Save YOLO txt", variable=self.save_yolo_var).pack(side="left", padx=(10, 5))
        ttk.Checkbutton(button_frame, text="Save JSON", variable=self.save_json_var).pack(side="left", padx=5)
        
        # Tuning Box on Right Side
        tuning_box = ttk.LabelFrame(right_side, text="Tuning Controls", padding=10)
        tuning_box.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        tuning_box.columnconfigure(1, weight=1)

        self._add_scale_row(tuning_box, 0, "Confidence", self.app.state.confidence_var, 0.05, 1.0, 0.05)
        self._add_scale_row(tuning_box, 1, "Threshold", self.app.state.threshold_var, 0, 255, 1)
        self._add_scale_row(tuning_box, 2, "Blur Kernel", self.app.state.blur_var, 1, 31, 2)
        self._add_scale_row(tuning_box, 3, "Min Area", self.app.state.min_area_var, 100, 10000, 100)
        self._add_scale_row(tuning_box, 4, "Overlay Alpha", self.app.state.overlay_alpha_var, 0.1, 0.9, 0.05)

        # Status Box (Machine Monitoring) on Right Side
        status_box = ttk.LabelFrame(right_side, text="Machine Monitoring", padding=10)
        status_box.grid(row=2, column=0, sticky="nsew")
        status_box.columnconfigure(1, weight=1)

        self.cycle_time_var = tk.StringVar(value="0.00s")
        self.machine_status_var = tk.StringVar(value="IDLE")
        self.item_count_var = tk.StringVar(value="0 / 150")

        self._add_info_row(status_box, 0, "Machine State:", self.machine_status_var, "#007bff")
        self._add_info_row(status_box, 1, "Cycle Time:", self.cycle_time_var, "#28a745")
        self._add_info_row(status_box, 2, "Total Count:", self.item_count_var, "#fd7e14")
        self._add_info_row(status_box, 3, "AI Model:", self.segment_mode_var, "#6f42c1")

        # Redraw tray maps dynamically on resize
        self.tray_canvas1.bind("<Configure>", lambda e: self._draw_single_tray(self.tray_canvas1, 0))
        self.tray_canvas2.bind("<Configure>", lambda e: self._draw_single_tray(self.tray_canvas2, 1))

    def _add_info_row(self, parent, row, label, var, color):
        ttk.Label(parent, text=label, font=("Segoe UI", 10)).grid(row=row, column=0, sticky="w", pady=5)
        val_lbl = tk.Label(parent, textvariable=var, font=("Segoe UI", 11, "bold"), fg=color, bg="#f5f6f8")
        val_lbl.grid(row=row, column=1, sticky="w", padx=10, pady=5)

    def update_cell_color(self, tray_index, r, c, color):
        self.cell_colors[(tray_index, r, c)] = color
        tag = f"tray_{tray_index}_cell_{r}_{c}"
        if tray_index == 0:
            self.tray_canvas1.itemconfig(tag, fill=color)
        else:
            self.tray_canvas2.itemconfig(tag, fill=color)
        
    def reset_tray_colors(self, tray_index):
        for r in range(5):
            for c in range(15):
                self.cell_colors[(tray_index, r, c)] = "#2a2a2a"
                tag = f"tray_{tray_index}_cell_{r}_{c}"
                if tray_index == 0:
                    self.tray_canvas1.itemconfig(tag, fill="#2a2a2a")
                else:
                    self.tray_canvas2.itemconfig(tag, fill="#2a2a2a")

    def _draw_single_tray(self, canvas, tray_index):
        canvas.delete("all")
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w < 10: return
        
        rows = 5
        cols = 15
        padding_l = 25
        padding_t = 20
        
        tray_h = h - padding_t - 5
        tray_w = w - padding_l - 5
        
        cell_w = tray_w / cols
        cell_h = tray_h / rows
        
        # Title of Tray
        # canvas.create_text(10, 12, text=f"TRAY {tray_index + 1}", fill="white", font=("Segoe UI", 9, "bold"), anchor="sw")
        
        # Col Headers (C1..C15)
        for c in range(cols):
            cx = padding_l + c * cell_w + cell_w / 2
            canvas.create_text(cx, 12, text=f"C{c+1}", fill="#aaa", font=("Segoe UI", 7))
            
        # Row Headers (R1..R5)
        for r in range(rows):
            cy = padding_t + r * cell_h + cell_h / 2
            canvas.create_text(12, cy, text=f"R{r+1}", fill="#aaa", font=("Segoe UI", 7))

        for r in range(rows):
            for c in range(cols):
                x1 = padding_l + c * cell_w
                y1 = padding_t + r * cell_h
                x2 = x1 + cell_w
                y2 = y1 + cell_h
                
                default_color = "#2a2a2a"
                color = self.cell_colors.get((tray_index, r, c), default_color)
                canvas.create_rectangle(x1, y1, x2, y2, outline="#555", fill=color, tags=f"tray_{tray_index}_cell_{r}_{c}")
                canvas.create_oval(x1+cell_w/2-2, y1+cell_h/2-2, x1+cell_w/2+2, y1+cell_h/2+2, fill="#777")

    def _add_scale_row(self, parent: ttk.LabelFrame, row: int, title: str, variable: tk.IntVar | tk.DoubleVar, minimum: float, maximum: float, resolution: float) -> None:
        ttk.Label(parent, text=title, width=14).grid(
            row=row, column=0, sticky="w", padx=(0, 12), pady=4
        )
        scale = tk.Scale(
            parent,
            variable=variable,
            from_=minimum,
            to=maximum,
            orient="horizontal",
            resolution=resolution,
            showvalue=True,
            length=430,
            highlightthickness=0,
        )
        scale.grid(row=row, column=1, sticky="ew", pady=4)

    def _capture_segment(self) -> None:
        settings = self.app.settings_tab._current_settings(
            self.app.state.confidence_var.get(),
            self.app.state.threshold_var.get(),
            self.app.state.blur_var.get(),
            self.app.state.min_area_var.get(),
            self.app.state.overlay_alpha_var.get()
        )
        frame = self.app.current_frame.copy()

        self.segment_result = self.app.segmenter.segment(frame, settings)
        # self.segment_mode_var.set(self.app.segmenter.status_message)
        self._render_segment(self.segment_result.overlay_frame)
        self.app.status_var.set(
            f"Captured frame and processed segment with {self.segment_result.mode} mode."
        )

    def _save_capture(self) -> None:
        if self.segment_result is None:
            messagebox.showinfo("Save", "Capture a frame before saving.")
            return

        saved_paths = self.app.storage_service.save_capture(
            self.segment_result,
            save_yolo=self.save_yolo_var.get(),
            save_json=self.save_json_var.get(),
        )
        self.app.dataset_tab._refresh_saved_list()

        self.app.last_saved_var.set(f"Saved: {saved_paths['segment_image'].name}")
        self.app.status_var.set("Capture saved successfully.")

        saved_summary = "\n".join(f"- {path}" for path in saved_paths.values())
        messagebox.showinfo("Saved", saved_summary)

    def _previous_folder_image(self) -> None:
        if self.app.active_source_type != "folder":
            self.app.status_var.set("Prev/Next only works when source is Image Folder.")
            return

        self.app.current_frame = self.app.folder_service.previous_image()
        self._render_realtime(self.app.current_frame)
        self.app.status_var.set(self.app.folder_service.summary())
        self.app.settings_tab._update_source_widgets()

    def _next_folder_image(self) -> None:
        if self.app.active_source_type != "folder":
            self.app.status_var.set("Prev/Next only works when source is Image Folder.")
            return

        self.app.current_frame = self.app.folder_service.next_image()
        self._render_realtime(self.app.current_frame)
        self.app.status_var.set(self.app.folder_service.summary())
        self.app.settings_tab._update_source_widgets()

    def _render_realtime(self, frame) -> None:
        self.realtime_photo = to_photo_image(frame, self.p_w, self.p_h)
        self.realtime_label.configure(image=self.realtime_photo)
        if hasattr(self.app, 'motor_tab'):
            self.app.motor_tab._render_motor_camera(frame)

    def _render_segment(self, frame) -> None:
        self.segment_photo = to_photo_image(frame, self.p_w, self.p_h)
        self.segment_label.configure(image=self.segment_photo)