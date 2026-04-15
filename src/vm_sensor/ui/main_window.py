import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from vm_sensor.config import (
    MODEL_DIR,
    OUTPUT_DIR,
    PREVIEW_HEIGHT,
    PREVIEW_WIDTH,
    REFRESH_INTERVAL_MS,
    WINDOW_SIZE,
    WINDOW_TITLE,
)
from vm_sensor.ui.Shared_Param import AppState
from vm_sensor.models import SegmentResult, SegmentSettings
from vm_sensor.services.basler_camera_service import BaslerCameraService, BaslerDeviceInfo
from vm_sensor.services.camera_service import CameraService
from vm_sensor.services.image_source_service import ImageFolderService
from vm_sensor.services.motor_service import MotorControllerService
from vm_sensor.services.motor_service import ModbusRTUService
from vm_sensor.services.segment_service import YoloSegmenter
from vm_sensor.services.storage_service import StorageService
from vm_sensor.utils.image_utils import to_photo_image
from vm_sensor.reg_mapping import RegisterMap

class MainWindow:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title(WINDOW_TITLE)
        self.root.geometry(WINDOW_SIZE)
        self.root.minsize(1320, 840)
        self._last_log_len = 0

        self.camera_service = CameraService(camera_index=0)
        self.basler_service = BaslerCameraService()
        self.folder_service = ImageFolderService()
        self.motor_service = MotorControllerService(RegisterMap())
        self.state = AppState()
        self.segmenter = YoloSegmenter()
        self.storage_service = StorageService(OUTPUT_DIR)

        self.basler_devices: list[BaslerDeviceInfo] = []
        self.active_source_type = "camera"
        self.active_camera_backend = "opencv"
        self.current_frame = self.camera_service.read_frame()
        self.segment_result: SegmentResult | None = None
        self.realtime_photo = None
        self.segment_photo = None
        self.motor_photo = None

        self.status_var = tk.StringVar(value="Ready.")
        self.segment_mode_var = tk.StringVar(value=self.segmenter.status_message)
        self.last_saved_var = tk.StringVar(value="No saved capture yet.")
        self.model_path_var = tk.StringVar(value="")
        self.source_summary_var = tk.StringVar(value="Source: OpenCV camera #0")
        self.basler_sdk_var = tk.StringVar(value=self.basler_service.sdk_status())

        self.source_type_var = tk.StringVar(value="camera")
        self.camera_backend_var = tk.StringVar(value="opencv")
        self.basler_device_var = tk.StringVar(value="")
        self.image_folder_var = tk.StringVar(value="")
        self.camera_index_var = tk.IntVar(value=0)
        self.confidence_var = tk.DoubleVar(value=0.40)
        self.threshold_var = tk.IntVar(value=120)
        self.blur_var = tk.IntVar(value=5)
        self.min_area_var = tk.IntVar(value=800)
        self.overlay_alpha_var = tk.DoubleVar(value=0.45)

        self.save_yolo_var = tk.BooleanVar(value=False)
        self.save_json_var = tk.BooleanVar(value=False)

        self.com_port_var = tk.StringVar(value="")
        self.baudrate_var = tk.StringVar(value="115200")
        self.jog_step_var = tk.DoubleVar(value=1.0)
        # self.speed_x_var = tk.DoubleVar(value=20.0)
        # self.speed_y_var = tk.DoubleVar(value=20.0)
        # self.speed_z_var = tk.DoubleVar(value=10.0)
        self.motor_status_var = tk.StringVar(value=self.motor_service.status_message)
        self.motor_position_var = tk.StringVar(value=self._format_motor_positions())
        # self.abs_x_var = tk.DoubleVar(value=0.0)
        # self.abs_y_var = tk.DoubleVar(value=0.0)
        # self.abs_z_var = tk.DoubleVar(value=0.0)

        self._configure_style()
        self._build_ui()

        self.camera_service.start()
        self._refresh_basler_devices(silent=True)
        self._refresh_com_ports(silent=True)
        self._update_source_widgets()
        self._refresh_motor_widgets()
        self._refresh_realtime()
        self._refresh_saved_list()
        self._update_motor_log_ui()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def run(self) -> None:
        self.root.mainloop()

    def _configure_style(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("TNotebook", background="#e9ecef")
        style.configure("TFrame", background="#f5f6f8")
        style.configure("TLabelframe", background="#f5f6f8")
        style.configure("TLabelframe.Label", font=("Segoe UI", 10, "bold"))
        style.configure("Header.TLabel", font=("Segoe UI", 11, "bold"))
        style.configure("Status.TLabel", background="#f5f6f8", foreground="#1f2933")
        style.configure("Primary.TButton", padding=(10, 6))

    def _build_ui(self) -> None:
        shell = ttk.Frame(self.root, padding=12)
        shell.pack(fill="both", expand=True)

        notebook = ttk.Notebook(shell)
        notebook.pack(fill="both", expand=True)

        self.main_tab = ttk.Frame(notebook, padding=12)
        self.motor_tab = ttk.Frame(notebook, padding=12)
        self.dataset_tab = ttk.Frame(notebook, padding=12)
        self.settings_tab = ttk.Frame(notebook, padding=12)

        notebook.add(self.main_tab, text="Main")
        notebook.add(self.motor_tab, text="Motor")
        notebook.add(self.dataset_tab, text="Dataset")
        notebook.add(self.settings_tab, text="Settings")

        self._build_main_tab()
        self._build_motor_tab()
        self._build_dataset_tab()
        self._build_settings_tab()

        footer = ttk.Frame(shell, padding=(0, 10, 0, 0))
        footer.pack(fill="x")
        ttk.Label(footer, textvariable=self.status_var, style="Status.TLabel").pack(
            side="left", fill="x", expand=True
        )
        ttk.Label(footer, textvariable=self.last_saved_var, style="Status.TLabel").pack(
            side="right"
        )

    def _build_main_tab(self) -> None:
        self.main_tab.columnconfigure(0, weight=1)
        self.main_tab.rowconfigure(0, weight=1)

        viewers = ttk.Frame(self.main_tab)
        viewers.grid(row=0, column=0, sticky="nsew")
        viewers.columnconfigure(0, weight=1)
        viewers.columnconfigure(1, weight=1)
        viewers.rowconfigure(0, weight=1)

        realtime_box = ttk.LabelFrame(viewers, text="Realtime View", padding=10)
        realtime_box.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        realtime_box.columnconfigure(0, weight=1)
        realtime_box.rowconfigure(0, weight=1)

        segment_box = ttk.LabelFrame(viewers, text="Segment View", padding=10)
        segment_box.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        segment_box.columnconfigure(0, weight=1)
        segment_box.rowconfigure(0, weight=1)

        self.realtime_label = ttk.Label(realtime_box, anchor="center")
        self.realtime_label.grid(row=0, column=0, sticky="nsew")

        self.segment_label = ttk.Label(segment_box, anchor="center")
        self.segment_label.grid(row=0, column=0, sticky="nsew")

        action_bar = ttk.Frame(self.main_tab, padding=(0, 12, 0, 8))
        action_bar.grid(row=1, column=0, sticky="ew")
        action_bar.columnconfigure(7, weight=1)

        ttk.Button(
            action_bar,
            text="Capture",
            style="Primary.TButton",
            command=self._capture_segment,
        ).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(
            action_bar,
            text="Save",
            style="Primary.TButton",
            command=self._save_capture,
        ).grid(row=0, column=1, padx=(0, 8))

        self.prev_image_button = ttk.Button(
            action_bar,
            text="Prev Image",
            command=self._previous_folder_image,
        )
        self.prev_image_button.grid(row=0, column=2, padx=(0, 8))

        self.next_image_button = ttk.Button(
            action_bar,
            text="Next Image",
            command=self._next_folder_image,
        )
        self.next_image_button.grid(row=0, column=3, padx=(0, 16))

        ttk.Checkbutton(
            action_bar,
            text="Save YOLO txt",
            variable=self.save_yolo_var,
        ).grid(row=0, column=4, padx=(0, 8))
        ttk.Checkbutton(
            action_bar,
            text="Save JSON",
            variable=self.save_json_var,
        ).grid(row=0, column=5, padx=(0, 8))

        ttk.Label(
            action_bar,
            textvariable=self.segment_mode_var,
            style="Status.TLabel",
        ).grid(row=0, column=6, sticky="w", padx=(16, 0))

        ttk.Label(
            action_bar,
            textvariable=self.source_summary_var,
            style="Status.TLabel",
        ).grid(row=1, column=0, columnspan=8, sticky="w", pady=(8, 0))

        tuning_box = ttk.LabelFrame(self.main_tab, text="Tuning Controls", padding=12)
        tuning_box.grid(row=2, column=0, sticky="ew")
        tuning_box.columnconfigure(1, weight=1)

        self._add_scale_row(tuning_box, 0, "Confidence", self.confidence_var, 0.05, 1.0, 0.05)
        self._add_scale_row(tuning_box, 1, "Threshold", self.threshold_var, 0, 255, 1)
        self._add_scale_row(tuning_box, 2, "Blur Kernel", self.blur_var, 1, 31, 2)
        self._add_scale_row(tuning_box, 3, "Min Area", self.min_area_var, 100, 10000, 100)
        self._add_scale_row(tuning_box, 4, "Overlay Alpha", self.overlay_alpha_var, 0.1, 0.9, 0.05)
    def _build_motor_tab(self) -> None:
        self.motor_tab.columnconfigure(0, weight=1)
        self.motor_tab.columnconfigure(1, weight=1)
        self.motor_tab.rowconfigure(0, weight=1)
        self.motor_tab.rowconfigure(4, weight=1)

        connection_box = ttk.LabelFrame(self.motor_tab, text="COM Connection", padding=12)
        connection_box.grid(row=0, column=0, sticky="ew", padx=(0, 8), pady=(0, 8))
        connection_box.columnconfigure(1, weight=1)

        ttk.Label(connection_box, text="COM port").grid(row=0, column=0, sticky="w")
        self.com_port_combo = ttk.Combobox(
            connection_box,
            textvariable=self.com_port_var,
            state="readonly",
        )
        self.com_port_combo.grid(row=0, column=1, sticky="ew", padx=8)
        ttk.Button(connection_box, text="Refresh Ports", command=self._refresh_com_ports).grid(
            row=0, column=2, sticky="w"
        )

        ttk.Label(connection_box, text="Baudrate").grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.baudrate_combo = ttk.Combobox(
            connection_box,
            textvariable=self.baudrate_var,
            values=["9600", "19200", "38400", "57600", "115200"],
            state="readonly",
            width=12,
        )
        self.baudrate_combo.grid(row=1, column=1, sticky="w", padx=8, pady=(10, 0))
        ttk.Button(
            connection_box,
            text="Connect",
            style="Primary.TButton",
            command=self._connect_motor,
        ).grid(row=1, column=2, sticky="w", pady=(10, 0))
        ttk.Button(
            connection_box,
            text="Disconnect",
            command=self._disconnect_motor,
        ).grid(row=1, column=3, sticky="w", padx=(8, 0), pady=(10, 0))

        ttk.Label(
            connection_box,
            textvariable=self.motor_status_var,
            style="Status.TLabel",
            wraplength=500,
            justify="left",
        ).grid(row=2, column=0, columnspan=4, sticky="w", pady=(10, 0))

        action_box = ttk.LabelFrame(self.motor_tab, text="Motion Actions", padding=12)
        action_box.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(0, 8))

        ttk.Button(action_box, text="Start", style="Primary.TButton", command=self._motor_start).grid(
            row=0, column=0, padx=(0, 8)
        )
        ttk.Button(action_box, text="Stop", style="Primary.TButton", command=self._motor_stop).grid(
            row=0, column=1, padx=(0, 8)
        )
        ttk.Button(action_box, text="Home", style="Primary.TButton", command=self._motor_home).grid(
            row=0, column=2
        )
        # ===== Container chia đôi =====
        jog_container = ttk.Frame(self.motor_tab)
        jog_container.grid(row=2, column=0, sticky="ew", padx=(0, 8), pady=(0, 8))

        jog_container.columnconfigure(0, weight=1)
        jog_container.columnconfigure(1, weight=1)
        jog_box = ttk.LabelFrame(jog_container, text="Jog XYZ", padding=12)
        jog_box.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        abs_box = ttk.LabelFrame(jog_container, text="Absolute Move", padding=12)
        abs_box.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        # jog_box = ttk.LabelFrame(self.motor_tab, text="Jog XYZ", padding=12)
        # jog_box.grid(row=2, column=0, sticky="ew", padx=(0, 8), pady=(0, 8))
        # abs_box = ttk.LabelFrame(self.motor_tab, text="Absolute Move", padding=12)
        # abs_box.grid(row=2, column=1, sticky="ew", padx=(8, 0), pady=(0, 8))

        ttk.Label(abs_box, text="Position X").grid(row=0, column=0, sticky="w")
        ttk.Entry(abs_box, textvariable=self.state.abs_x_var, width=10).grid(row=0, column=1, padx=8)

        ttk.Label(abs_box, text="Position Y").grid(row=1, column=0, sticky="w")
        ttk.Entry(abs_box, textvariable=self.state.abs_y_var, width=10).grid(row=1, column=1, padx=8)

        ttk.Label(abs_box, text="Position Z").grid(row=2, column=0, sticky="w")
        ttk.Entry(abs_box, textvariable=self.state.abs_z_var, width=10).grid(row=2, column=1, padx=8)
        ttk.Button(
            abs_box,
            text="Move To Position",
            style="Primary.TButton",
            command=self._move_absolute
        ).grid(row=3, column=0, columnspan=2, pady=(12, 0), sticky="w")
        ttk.Label(jog_box, text="Jog step").grid(row=0, column=0, sticky="w")
        ttk.Spinbox(
            jog_box,
            from_=0.01,
            to=1000.0,
            increment=0.1,
            textvariable=self.jog_step_var,
            width=10,
        ).grid(row=0, column=1, sticky="w", padx=(8, 0))
        ttk.Label(
            jog_box,
            text="(unit placeholder: mm / pulse)",
            style="Status.TLabel",
        ).grid(row=0, column=2, sticky="w", padx=(12, 0))

        for row_index, axis_name in enumerate(("X", "Y", "Z"), start=1):
            pady = (10 if row_index == 1 else 8, 0)

            ttk.Label(jog_box, text=f"Axis {axis_name}", width=12).grid(
                row=row_index, column=0, sticky="w", pady=pady
            )

            axis = axis_name.lower()

            # ===== Nút "-" =====
            btn_minus = ttk.Button(jog_box, text=f"{axis_name}-")
            btn_minus.grid(row=row_index, column=1, padx=(0, 8), pady=pady)

            btn_minus.bind("<ButtonPress-1>",
                lambda e, a=axis: self._motor_jog_press(a, -1)
            )
            btn_minus.bind("<ButtonRelease-1>",
                lambda e, a=axis: self._motor_jog_release(a, -1)
            )
            btn_minus.bind("<Leave>",   # 🔥 chống miss release
                lambda e, a=axis: self._motor_jog_release(a, -1)
            )

            # ===== Nút "+" =====
            btn_plus = ttk.Button(jog_box, text=f"{axis_name}+")
            btn_plus.grid(row=row_index, column=2, pady=pady)

            btn_plus.bind("<ButtonPress-1>",
                lambda e, a=axis: self._motor_jog_press(a, 1)
            )
            btn_plus.bind("<ButtonRelease-1>",
                lambda e, a=axis: self._motor_jog_release(a, 1)
            )
            btn_plus.bind("<Leave>",
                lambda e, a=axis: self._motor_jog_release(a, 1)
            )

        speed_box = ttk.LabelFrame(self.motor_tab, text="Axis Speed", padding=12)
        speed_box.grid(row=3, column=0, sticky="ew", padx=(0, 8), pady=(0, 8))
        speed_box.columnconfigure(1, weight=1)
        
        self._add_motor_speed_row(speed_box, 0, "Speed X", self.state.speed_x)
        self._add_motor_speed_row(speed_box, 1, "Speed Y", self.state.speed_y)
        self._add_motor_speed_row(speed_box, 2, "Speed Z", self.state.speed_z)

        ttk.Button(
            speed_box,
            text="Apply Speed",
            style="Primary.TButton",
            command=self._apply_motor_speeds,
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(10, 0))

        preview_box = ttk.LabelFrame(self.motor_tab, text="Camera Position Preview", padding=12)
        preview_box.grid(row=0, column=1, rowspan=2, sticky="nsew", pady=(0, 8))
        preview_box.columnconfigure(0, weight=1)
        preview_box.rowconfigure(1, weight=1)

        ttk.Label(
            preview_box,
            text="Preview follows the active camera source so you can see where Z is looking.",
            style="Status.TLabel",
            wraplength=520,
            justify="left",
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        self.motor_camera_label = ttk.Label(preview_box, anchor="center")
        self.motor_camera_label.grid(row=1, column=0, sticky="nsew")

        ttk.Label(
            preview_box,
            textvariable=self.source_summary_var,
            style="Status.TLabel",
        ).grid(row=2, column=0, sticky="w", pady=(8, 0))

        position_box = ttk.LabelFrame(self.motor_tab, text="Axis Position", padding=12)
        position_box.grid(row=2, column=1, sticky="ew", pady=(0, 8))
        ttk.Label(position_box, textvariable=self.motor_position_var, font=("Consolas", 11)).grid(
            row=0, column=0, sticky="w"
        )
        

        # ===== MAIN FRAME =====
        log_box = ttk.Frame(self.motor_tab, padding=0)
        log_box.grid(row=3, column=1, rowspan=2, sticky="nsew")
        log_box.columnconfigure(0, weight=1)
        log_box.rowconfigure(1, weight=1)

        # ===== HEADER =====
        header = ttk.Frame(log_box)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        header.columnconfigure(0, weight=1)

        # Title bên trái
        ttk.Label(header, text="Command Log", font=("Segoe UI", 10, "bold")).grid(
            row=0, column=0, sticky="w"
        )

        # Combobox bên phải
        self.refresh_var = tk.StringVar(value="100 ms")

        self.refresh_combo = ttk.Combobox(
            header,
            textvariable=self.refresh_var,
            values=["10 ms", "50 ms", "100 ms", "200 ms", "500 ms", "1000 ms"],
            width=10,
            state="readonly"
        )
        self.refresh_combo.grid(row=0, column=1, sticky="e", padx=(5, 0))
        self.refresh_combo.bind("<<ComboboxSelected>>", self.on_refresh_change)   
        # ===== TEXT BOX =====
        self.motor_log_text = ScrolledText(
            log_box,
            font=("Consolas", 10),
            height=12,
            wrap="word",
        )
        self.motor_log_text.grid(row=1, column=0, sticky="nsew")
        self.motor_log_text.configure(state="disabled")
    

    def _build_dataset_tab(self) -> None:
        self.dataset_tab.columnconfigure(0, weight=1)
        self.dataset_tab.rowconfigure(1, weight=1)

        ttk.Label(self.dataset_tab, text="Saved outputs", style="Header.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 8)
        )

        self.saved_listbox = tk.Listbox(
            self.dataset_tab,
            font=("Consolas", 10),
            height=20,
            activestyle="none",
        )
        self.saved_listbox.grid(row=1, column=0, sticky="nsew")

        info_box = ttk.Frame(self.dataset_tab, padding=(0, 12, 0, 0))
        info_box.grid(row=2, column=0, sticky="ew")
        ttk.Label(info_box, text=f"Output folder: {OUTPUT_DIR}", style="Status.TLabel").pack(
            side="left"
        )
        ttk.Button(info_box, text="Refresh List", command=self._refresh_saved_list).pack(
            side="right"
        )

    def _build_settings_tab(self) -> None:
        self.settings_tab.columnconfigure(0, weight=1)

        source_box = ttk.LabelFrame(self.settings_tab, text="Source", padding=12)
        source_box.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        source_box.columnconfigure(1, weight=1)
        source_box.columnconfigure(2, weight=1)

        ttk.Label(source_box, text="Input source").grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(
            source_box,
            text="Camera",
            value="camera",
            variable=self.source_type_var,
            command=self._update_source_widgets,
        ).grid(row=0, column=1, sticky="w")
        ttk.Radiobutton(
            source_box,
            text="Image Folder",
            value="folder",
            variable=self.source_type_var,
            command=self._update_source_widgets,
        ).grid(row=0, column=2, sticky="w", padx=(12, 0))

        ttk.Label(source_box, text="Folder path").grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.folder_entry = ttk.Entry(source_box, textvariable=self.image_folder_var)
        self.folder_entry.grid(row=1, column=1, sticky="ew", padx=8, pady=(10, 0))
        self.folder_browse_button = ttk.Button(
            source_box,
            text="Browse",
            command=self._browse_image_folder,
        )
        self.folder_browse_button.grid(row=1, column=2, sticky="w", pady=(10, 0))
        self.source_apply_button = ttk.Button(
            source_box,
            text="Apply Source",
            command=self._apply_source,
        )
        self.source_apply_button.grid(row=1, column=3, sticky="w", padx=(8, 0), pady=(10, 0))

        ttk.Label(
            source_box,
            text="Supported image formats: jpg, jpeg, png, bmp, tif, tiff, webp",
            style="Status.TLabel",
        ).grid(row=2, column=0, columnspan=4, sticky="w", pady=(10, 0))
        model_box = ttk.LabelFrame(self.settings_tab, text="YOLO Model", padding=12)
        model_box.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        model_box.columnconfigure(1, weight=1)

        ttk.Label(model_box, text="Model path").grid(row=0, column=0, sticky="w")
        ttk.Entry(model_box, textvariable=self.model_path_var).grid(
            row=0, column=1, sticky="ew", padx=8
        )
        ttk.Button(model_box, text="Browse", command=self._browse_model).grid(
            row=0, column=2, padx=(0, 8)
        )
        ttk.Button(model_box, text="Load Model", command=self._load_model).grid(
            row=0, column=3
        )

        ttk.Label(model_box, text=f"Model folder: {MODEL_DIR}", style="Status.TLabel").grid(
            row=1, column=0, columnspan=4, sticky="w", pady=(10, 0)
        )

        camera_box = ttk.LabelFrame(self.settings_tab, text="Camera", padding=12)
        camera_box.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        camera_box.columnconfigure(1, weight=1)

        ttk.Label(camera_box, text="Camera backend").grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(
            camera_box,
            text="OpenCV / USB",
            value="opencv",
            variable=self.camera_backend_var,
            command=self._update_source_widgets,
        ).grid(row=0, column=1, sticky="w")
        ttk.Radiobutton(
            camera_box,
            text="Basler Vision",
            value="basler",
            variable=self.camera_backend_var,
            command=self._update_source_widgets,
        ).grid(row=0, column=2, sticky="w", padx=(12, 0))

        ttk.Label(camera_box, text="Camera index").grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.camera_index_spin = ttk.Spinbox(
            camera_box,
            from_=0,
            to=10,
            textvariable=self.camera_index_var,
            width=10,
        )
        self.camera_index_spin.grid(row=1, column=1, sticky="w", padx=8, pady=(10, 0))

        ttk.Label(camera_box, text="Basler device").grid(row=2, column=0, sticky="w", pady=(10, 0))
        self.basler_device_combo = ttk.Combobox(
            camera_box,
            textvariable=self.basler_device_var,
            state="readonly",
        )
        self.basler_device_combo.grid(row=2, column=1, sticky="ew", padx=8, pady=(10, 0))
        self.basler_refresh_button = ttk.Button(
            camera_box,
            text="Refresh Devices",
            command=self._refresh_basler_devices,
        )
        self.basler_refresh_button.grid(row=2, column=2, sticky="w", pady=(10, 0))

        ttk.Label(
            camera_box,
            textvariable=self.basler_sdk_var,
            style="Status.TLabel",
            wraplength=900,
            justify="left",
        ).grid(row=3, column=0, columnspan=3, sticky="w", pady=(10, 0))

        self.apply_camera_button = ttk.Button(
            camera_box,
            text="Apply Camera",
            command=self._apply_camera_connection,
        )
        self.apply_camera_button.grid(row=4, column=0, sticky="w", pady=(10, 0))

        ttk.Label(
            camera_box,
            text=(
                "Use OpenCV for USB webcams. Use Basler Vision after installing pypylon "
                "and refreshing the detected devices."
            ),
            style="Status.TLabel",
            wraplength=900,
            justify="left",
        ).grid(row=4, column=1, columnspan=2, sticky="w", pady=(10, 0))

        hint_box = ttk.LabelFrame(self.settings_tab, text="Notes", padding=12)
        hint_box.grid(row=3, column=0, sticky="ew")

        ttk.Label(
            hint_box,
            text=(
                "If no YOLO model is loaded, the app still works with a contour-based "
                "segmentation demo so the UI flow can be tested first."
            ),
            wraplength=1000,
            justify="left",
            style="Status.TLabel",
        ).grid(row=0, column=0, sticky="w")

    def _add_scale_row(
        self,
        parent: ttk.LabelFrame,
        row: int,
        title: str,
        variable: tk.IntVar | tk.DoubleVar,
        minimum: float,
        maximum: float,
        resolution: float,
    ) -> None:
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

    def _add_motor_speed_row(
        self,
        parent: ttk.LabelFrame,
        row: int,
        title: str,
        variable: tk.DoubleVar,
    ) -> None:
        ttk.Label(parent, text=title, width=12).grid(
            row=row, column=0, sticky="w", padx=(0, 12), pady=4
        )

        scale = tk.Scale(
            parent,
            variable=variable,
            from_=0.1,
            to=200.0,
            orient="horizontal",
            resolution=0.1,
            showvalue=True,
            length=250,
            highlightthickness=0,
        )
        scale.grid(row=row, column=1, sticky="ew", pady=4)

    def _capture_segment(self) -> None:
        settings = self._current_settings()
        frame = self.current_frame.copy()

        self.segment_result = self.segmenter.segment(frame, settings)
        self.segment_mode_var.set(self.segmenter.status_message)
        self._render_segment(self.segment_result.overlay_frame)
        self.status_var.set(
            f"Captured frame and processed segment with {self.segment_result.mode} mode."
        )

    def _save_capture(self) -> None:
        if self.segment_result is None:
            messagebox.showinfo("Save", "Capture a frame before saving.")
            return

        saved_paths = self.storage_service.save_capture(
            self.segment_result,
            save_yolo=self.save_yolo_var.get(),
            save_json=self.save_json_var.get(),
        )
        self._refresh_saved_list()

        self.last_saved_var.set(f"Saved: {saved_paths['segment_image'].name}")
        self.status_var.set("Capture saved successfully.")

        saved_summary = "\n".join(f"- {path}" for path in saved_paths.values())
        messagebox.showinfo("Saved", saved_summary)

    def _browse_image_folder(self) -> None:
        selected = filedialog.askdirectory(
            title="Select image folder",
            initialdir=self.image_folder_var.get().strip() or str(OUTPUT_DIR.parent),
        )
        if selected:
            self.image_folder_var.set(selected)

    def _apply_source(self) -> None:
        selected_source = self.source_type_var.get()

        if selected_source == "camera":
            success, message = self._activate_camera_source()
            self.status_var.set(message)
            if not success:
                messagebox.showwarning("Camera source", message)
            return

        folder_path = self.image_folder_var.get().strip()
        if not folder_path:
            messagebox.showinfo("Source", "Choose an image folder first.")
            return

        self.active_source_type = "folder"
        self.camera_service.release()
        self.basler_service.release()
        success, message = self.folder_service.load_folder(folder_path)
        self.current_frame = self.folder_service.read_frame()
        self._render_realtime(self.current_frame)
        self.status_var.set(message)
        self._update_source_widgets()

        if not success:
            messagebox.showwarning("Folder source", message)
    def _activate_camera_source(self) -> tuple[bool, str]:
        self.active_source_type = "camera"
        selected_backend = self.camera_backend_var.get()

        if selected_backend == "opencv":
            self.basler_service.release()
            success = self.camera_service.set_camera_index(self.camera_index_var.get())
            self.active_camera_backend = "opencv"
            self.current_frame = self.camera_service.read_frame()
            self._render_realtime(self.current_frame)

            if success:
                message = f"Connected to OpenCV camera #{self.camera_index_var.get()}."
            else:
                message = f"Camera #{self.camera_index_var.get()} is not available."

            self._update_source_widgets()
            return success, message

        self.camera_service.release()
        if not self.basler_devices:
            self._refresh_basler_devices(silent=True)

        selected_serial = self._selected_basler_serial()
        success, message = self.basler_service.connect(selected_serial)
        self.active_camera_backend = "basler"
        self.current_frame = self.basler_service.read_frame()
        self._render_realtime(self.current_frame)
        self._update_basler_status_label(message)
        self._update_source_widgets()
        return success, message

    def _apply_camera_connection(self) -> None:
        if self.source_type_var.get() != "camera":
            self.status_var.set(
                "Camera settings saved. Select source Camera and click Apply Source to use them."
            )
            return

        success, message = self._activate_camera_source()
        self.status_var.set(message)
        if not success:
            messagebox.showwarning("Camera", message)

    def _previous_folder_image(self) -> None:
        if self.active_source_type != "folder":
            self.status_var.set("Prev/Next only works when source is Image Folder.")
            return

        self.current_frame = self.folder_service.previous_image()
        self._render_realtime(self.current_frame)
        self.status_var.set(self.folder_service.summary())
        self._update_source_widgets()

    def _next_folder_image(self) -> None:
        if self.active_source_type != "folder":
            self.status_var.set("Prev/Next only works when source is Image Folder.")
            return

        self.current_frame = self.folder_service.next_image()
        self._render_realtime(self.current_frame)
        self.status_var.set(self.folder_service.summary())
        self._update_source_widgets()

    def _refresh_basler_devices(self, silent: bool = False) -> None:
        previous_serial = self._selected_basler_serial()
        self.basler_devices, message = self.basler_service.list_devices()

        labels = [device.display_name for device in self.basler_devices]
        self.basler_device_combo["values"] = labels

        if not labels:
            self.basler_device_var.set("")
        else:
            matching_label = next(
                (
                    device.display_name
                    for device in self.basler_devices
                    if device.serial_number == previous_serial
                ),
                labels[0],
            )
            self.basler_device_var.set(matching_label)

        self._update_basler_status_label(message)
        self._update_source_widgets()
        if not silent:
            self.status_var.set(message)

    def _update_basler_status_label(self, message: str) -> None:
        sdk_status = self.basler_service.sdk_status()
        if message == sdk_status:
            self.basler_sdk_var.set(message)
            return

        self.basler_sdk_var.set(f"{sdk_status} {message}")

    def _selected_basler_serial(self) -> str | None:
        selected_label = self.basler_device_var.get().strip()
        if not selected_label:
            return None

        for device in self.basler_devices:
            if device.display_name == selected_label:
                return device.serial_number or None

        return None

    def _refresh_com_ports(self, silent: bool = False) -> None:
        ports, message = self.motor_service.list_ports()
        print("PORTS:", ports)
        previous_port = self.com_port_var.get().strip()
        self.com_port_combo["values"] = ports

        if previous_port in ports:
            self.com_port_var.set(previous_port)
        elif ports:
            self.com_port_var.set(ports[0])
        else:
            self.com_port_var.set("")

        self.motor_status_var.set(message)
        self._refresh_motor_widgets()
        if not silent:
            self.status_var.set(message)

    def _connect_motor(self) -> None:
        try:
            baudrate = int(self.baudrate_var.get())
        except ValueError:
            messagebox.showwarning("Motor", "Invalid baudrate.")
            return

        ok, message = self.motor_service.connect(
            port=self.com_port_var.get().strip(),
            baudrate=baudrate,
            timeout=0.2,
        )
        self.motor_status_var.set(message)
        self.status_var.set(message)
        self._refresh_motor_widgets()
        if not ok:
            messagebox.showwarning("Motor", message)

    def _disconnect_motor(self) -> None:
        _, message = self.motor_service.disconnect()
        self.motor_status_var.set(message)
        self.status_var.set(message)
        self._refresh_motor_widgets()

    def _motor_start(self) -> None:
        self._handle_motor_result(self.motor_service.start())

    def _motor_stop(self) -> None:
        self._handle_motor_result(self.motor_service.stop())

    def _motor_home(self) -> None:
        self._handle_motor_result(self.motor_service.home())

    # def _motor_jog(self, axis: str, direction: int) -> None:
    #     step = max(0.01, float(self.jog_step_var.get()))
    #     self._handle_motor_result(self.motor_service.jog(axis, direction, step))

    def _move_absolute(self):
        try:
            x = int(self.state.abs_x_var.get())
            y = int(self.state.abs_y_var.get())
            z = int(self.state.abs_z_var.get())
            sp_x =  int(self.state.speed_x.get())
            sp_y = int(self.state.speed_y.get())
            sp_z = int (self.state.speed_z.get())
            # ===== LIMIT =====
            X_MIN, X_MAX = 0, 50000
            Y_MIN, Y_MAX = 0, 50000
            Z_MIN, Z_MAX = 0, 20000
            if not (X_MIN <= x <= X_MAX):
                raise ValueError(f"X must be in range [{X_MIN}, {X_MAX}]")

            if not (Y_MIN <= y <= Y_MAX):
                raise ValueError(f"Y must be in range [{Y_MIN}, {Y_MAX}]")

            if not (Z_MIN <= z <= Z_MAX):
                raise ValueError(f"Z must be in range [{Z_MIN}, {Z_MAX}]")
            print("MOVE _ABS_ POsistion")       
            self.motor_service.enqueue_move_absolute(x, y, z, sp_x, sp_y ,sp_z  )
        except ValueError as e:
            messagebox.showerror("Invalid Input", str(e))
            
        except Exception as e:
            messagebox.showerror("Error", str(e))
        

    def _apply_motor_speeds(self) -> None:
        result = self.motor_service.set_all_speeds(
            self.state.speed_x.get(),
            self.state.speed_y.get(),
            self.state.speed_z.get(),
        )
        self._handle_motor_result(result)

    def _handle_motor_result(self, result: tuple[bool, str]) -> None:
        _, message = result
        self.motor_status_var.set(message)
        self.status_var.set(message)
        self._refresh_motor_widgets()

    def _refresh_motor_widgets(self) -> None:
        snapshot = self.motor_service.snapshot()
        positions = snapshot["positions"]
        self.motor_position_var.set(
            f"X: {positions['x']:.3f}    Y: {positions['y']:.3f}    Z: {positions['z']:.3f}"
        )

        self.motor_log_text.configure(state="normal")
        self.motor_log_text.delete("1.0", tk.END)
        if self.motor_service.modbus:
            for line in self.motor_service.modbus.get_recent_log():
                self.motor_log_text.insert(tk.END, f"{line}\n")
        self.motor_log_text.see(tk.END)
        self.motor_log_text.configure(state="disabled")
    def _browse_model(self) -> None:
        selected = filedialog.askopenfilename(
            title="Select YOLO segmentation model",
            initialdir=str(MODEL_DIR),
            filetypes=[("PyTorch model", "*.pt"), ("All files", "*.*")],
        )
        if selected:
            self.model_path_var.set(selected)

    def _load_model(self) -> None:
        model_path = self.model_path_var.get().strip()
        if not model_path:
            messagebox.showinfo("Load model", "Choose a model path first.")
            return

        message = self.segmenter.load_model(model_path)
        self.segment_mode_var.set(message)
        self.status_var.set(message)

    def _current_settings(self) -> SegmentSettings:
        return SegmentSettings(
            confidence=round(self.confidence_var.get(), 2),
            threshold=int(self.threshold_var.get()),
            blur_kernel=int(self.blur_var.get()),
            min_area=int(self.min_area_var.get()),
            overlay_alpha=round(self.overlay_alpha_var.get(), 2),
            source_type=self.active_source_type,
            camera_backend=self.active_camera_backend,
            camera_index=int(self.camera_index_var.get()),
            basler_serial=self._selected_basler_serial(),
            image_folder=self.image_folder_var.get().strip() or None,
            model_path=self.model_path_var.get().strip() or None,
        )

    def _refresh_realtime(self) -> None:
        if self.active_source_type == "camera":
            if self.active_camera_backend == "basler":
                self.current_frame = self.basler_service.read_frame()
            else:
                self.current_frame = self.camera_service.read_frame()
        else:
            self.current_frame = self.folder_service.last_frame.copy()

        self._render_realtime(self.current_frame)
        self.root.after(REFRESH_INTERVAL_MS, self._refresh_realtime)

    def _render_realtime(self, frame) -> None:
        self.realtime_photo = to_photo_image(frame, PREVIEW_WIDTH, PREVIEW_HEIGHT)
        self.realtime_label.configure(image=self.realtime_photo)
        self._render_motor_camera(frame)

    def _render_segment(self, frame) -> None:
        self.segment_photo = to_photo_image(frame, PREVIEW_WIDTH, PREVIEW_HEIGHT)
        self.segment_label.configure(image=self.segment_photo)

    def _render_motor_camera(self, frame) -> None:
        self.motor_photo = to_photo_image(frame, PREVIEW_WIDTH, PREVIEW_HEIGHT)
        self.motor_camera_label.configure(image=self.motor_photo)

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

    def _update_source_widgets(self) -> None:
        selected_is_folder = self.source_type_var.get() == "folder"
        selected_is_camera = not selected_is_folder
        selected_is_basler = selected_is_camera and self.camera_backend_var.get() == "basler"
        active_has_folder_images = (
            self.active_source_type == "folder" and bool(self.folder_service.image_paths)
        )

        if selected_is_folder:
            self.folder_entry.state(["!disabled"])
            self.folder_browse_button.state(["!disabled"])
        else:
            self.folder_entry.state(["disabled"])
            self.folder_browse_button.state(["disabled"])

        if selected_is_camera and not selected_is_basler:
            self.camera_index_spin.state(["!disabled"])
        else:
            self.camera_index_spin.state(["disabled"])

        if selected_is_camera and selected_is_basler:
            self.basler_device_combo.state(["!disabled"])
            self.basler_refresh_button.state(["!disabled"])
        else:
            self.basler_device_combo.state(["disabled"])
            self.basler_refresh_button.state(["disabled"])

        if selected_is_camera:
            self.apply_camera_button.state(["!disabled"])
        else:
            self.apply_camera_button.state(["disabled"])

        if active_has_folder_images:
            self.prev_image_button.state(["!disabled"])
            self.next_image_button.state(["!disabled"])
        else:
            self.prev_image_button.state(["disabled"])
            self.next_image_button.state(["disabled"])

        self.source_summary_var.set(self._source_summary())

    def _source_summary(self) -> str:
        if self.active_source_type == "camera":
            if self.active_camera_backend == "basler":
                if self.basler_service.connected_device is not None:
                    return f"Source: Basler {self.basler_service.connected_device.display_name}"

                selected_label = self.basler_device_var.get().strip()
                if selected_label:
                    return f"Source: Basler selected - {selected_label}"
                return "Source: Basler camera not connected"

            return f"Source: OpenCV camera #{self.camera_index_var.get()}"

        if self.folder_service.image_paths:
            return f"Source: {self.folder_service.summary()}"

        folder_path = self.image_folder_var.get().strip()
        if folder_path:
            return f"Source: Folder selected - {folder_path}"
        return "Source: Folder not selected"

    def _format_motor_positions(self) -> str:
        positions = self.motor_service.snapshot()["positions"]
        
        return f"X: {positions['x']:.3f}    Y: {positions['y']:.3f}    Z: {positions['z']:.3f}"
    
    def _update_motor_log_ui(self):
        if self.motor_service.modbus:
            log_queue = self.motor_service.modbus.log_queue

            self.motor_log_text.configure(state="normal")

            while not log_queue.empty():
                line = log_queue.get()
                self.motor_log_text.insert(tk.END, line + "\n")

            self.motor_log_text.see(tk.END)
            self.motor_log_text.configure(state="disabled")
    
        self.root.after(16, self._update_motor_log_ui)  # 🔥 50ms là đẹp

    def on_refresh_change(self, event):
        interval = int(self.refresh_var.get().split()[0])
        self.motor_service.set_refresh_interval(interval)
        print("New refresh:", interval)

        

    def _motor_jog_press(self, axis: str, direction: int):
        if not self.motor_service or not self.motor_service.is_connected():
            return

        self.motor_service.enqueue_jog(axis, direction, True)


    def _motor_jog_release(self, axis: str, direction: int):
        if not self.motor_service or not self.motor_service.is_connected():
            return

        self.motor_service.enqueue_jog(axis, direction, False) 

    def _on_close(self) -> None:
        self.camera_service.release()
        self.basler_service.release()
        self.motor_service.disconnect()
        self.root.destroy()
