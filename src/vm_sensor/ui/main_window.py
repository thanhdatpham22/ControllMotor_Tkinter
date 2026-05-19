import tkinter as tk
from tkinter import ttk

from vm_sensor.config import (
    OUTPUT_DIR,
    REFRESH_INTERVAL_MS,
    WINDOW_SIZE,
    WINDOW_TITLE,
)
from vm_sensor.ui.Shared_Param import AppState
from vm_sensor.services.basler_camera_service import BaslerCameraService
from vm_sensor.services.camera_service import CameraService
from vm_sensor.services.image_source_service import ImageFolderService
from vm_sensor.services.motor_service import MotorControllerService
from vm_sensor.services.segment_service import YoloSegmenter
from vm_sensor.services.storage_service import StorageService
from vm_sensor.services.auth_service import AuthService
from vm_sensor.reg_mapping import RegisterMap
from vm_sensor.logic.handler import TrayScanHandler

from vm_sensor.ui.dataset_window import DatasetWindow
from vm_sensor.ui.setting_window import SettingWindow
from vm_sensor.ui.motor_window import MotorWindow
from vm_sensor.ui.vision_window import VisionWindow


class MainWindow:
    def __init__(self) -> None:
        self.root = tk.Tk()
        # self.root = ThemedTk(theme="yaru")
        self.root.title(WINDOW_TITLE)
        self.root.geometry(WINDOW_SIZE)
        self.root.minsize(1650, 840)

        # Services
        self.camera_service = CameraService(camera_index=0)
        self.basler_service = BaslerCameraService()
        self.folder_service = ImageFolderService()
        self.motor_service = MotorControllerService(RegisterMap())
        self.state = AppState()
        self.segmenter = YoloSegmenter()
        self.storage_service = StorageService(OUTPUT_DIR)
        self.auth_service = AuthService()
        self.scan_handler = TrayScanHandler(self)

        # Shared Global State
        self.active_source_type = "camera"
        self.active_camera_backend = "opencv"
        self.current_frame = self.camera_service.read_frame()

        self.status_var = tk.StringVar(value="Ready.")
        self.last_saved_var = tk.StringVar(value="No saved capture yet.")
        self.prev_input_states = [False] * 24

        # Common configuration styles
        self._configure_style()
        
        # Build UI and assign Tabs
        self._build_ui()

        # Start background operations
        self.camera_service.start()
        self._refresh_realtime_loop()

        # Trace status changes to highlight footer
        self.status_var.trace_add("write", self._on_status_change)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def run(self) -> None:
        self.root.mainloop()

    def _configure_style(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
            # style.theme_use("vista")
        except tk.TclError:
            pass
        # style = ThemedStyle(self.root)   # ← khác với ttk.Style()

        style.configure("TNotebook", background="#e9ecef")
        style.configure("TFrame", background="#f5f6f8")
        style.configure("TLabelframe", background="#f5f6f8")
        style.configure("TLabelframe.Label", font=("Segoe UI", 10, "bold"))
        style.configure("Header.TLabel", font=("Segoe UI", 11, "bold"))
        style.configure("Status.TLabel", background="#f5f6f8", foreground="#1f2933", font=("Segoe UI", 9))
        style.configure("StatusBold.TLabel", background="yellow", foreground="#003366", font=("Segoe UI", 9, "bold"))
        style.configure("Primary.TButton", padding=(10, 6))

    def _build_ui(self) -> None:
        # --- FIXED STATUS BAR (Bottom) ---
        # Pack this first so it stays at the bottom and isn't pushed out by the expanding shell
        footer = ttk.Frame(self.root, relief="flat")
        footer.pack(side="bottom", fill="x")

        # Status Message Label
        self.status_label = ttk.Label(
            footer, 
            textvariable=self.status_var, 
            style="Status.TLabel",
            padding=(10, 5),
            relief="sunken"
        )
        self.status_label.pack(side="left", fill="x", expand=True)

        # Last Saved / Info Label
        info_label = ttk.Label(
            footer, 
            textvariable=self.last_saved_var, 
            style="Status.TLabel",
            padding=(10, 5),
            relief="sunken"
        )
        info_label.pack(side="left", fill="x", expand=True)

        # Sizegrip
        ttk.Sizegrip(footer).pack(side="right", anchor="se")

        # --- MAIN CONTENT AREA ---
        shell = ttk.Frame(self.root, padding=12)
        shell.pack(side="top", fill="both", expand=True)
        
        notebook = ttk.Notebook(shell)
        notebook.pack(fill="both", expand=True)

        # Initialize Sub-windows
        self.settings_tab = SettingWindow(notebook, self)
        self.dataset_tab = DatasetWindow(notebook, self)
        self.motor_tab = MotorWindow(notebook, self)
        self.main_tab = VisionWindow(notebook, self)

        # Re-trigger setting's update source widgets now that main_tab is available
        self.settings_tab._update_source_widgets()

        # Add to notebook
        notebook.add(self.main_tab, text="Main")
        notebook.add(self.motor_tab, text="Motor")
        notebook.add(self.dataset_tab, text="Dataset")
        notebook.add(self.settings_tab, text="Settings")

    def _on_status_change(self, *args) -> None:
        """Flash the status bar when text changes to notify the user."""
        if hasattr(self, 'status_label'):
            self.status_label.configure(style="StatusBold.TLabel")
            # Revert to normal style after 2 seconds
            self.root.after(2000, lambda: self.status_label.configure(style="Status.TLabel"))

    def _refresh_realtime_loop(self) -> None:
        if self.active_source_type == "camera":
            if self.active_camera_backend == "basler":
                self.current_frame = self.basler_service.read_frame()
            else:
                self.current_frame = self.camera_service.read_frame()
        else:
            self.current_frame = self.folder_service.last_frame.copy()

        self.main_tab._render_realtime(self.current_frame)
        self._check_plc_inputs()
        self.root.after(REFRESH_INTERVAL_MS, self._refresh_realtime_loop)

    def _check_plc_inputs(self):
        # We need to ensure motor_service has fetched input states
        if not self.motor_service.is_connected() or len(self.motor_service.input_states) < 7:
            return
            
        current_states = self.motor_service.input_states
        
        # Stop is mapped to input 4 (COIL_INPUT[5])
        # Start is mapped to input 5 (COIL_INPUT[6]) 
        # Reset is mapped to input 6 (COIL_INPUT[7])
        
        # Detect Rising Edges
        start_pressed = current_states[5] and not self.prev_input_states[5]
        stop_pressed = current_states[4] and not self.prev_input_states[4]
        reset_pressed = current_states[6] and not self.prev_input_states[6]
        
        if reset_pressed:
            self.scan_handler.reset_scan()
        elif stop_pressed:
            self.scan_handler.stop_scan()  # stop_scan now acts as pause_scan
        elif start_pressed:
            self.scan_handler.start_scan(self.scan_handler._current_tray_index)
            
        self.prev_input_states = list(current_states)

    def _on_close(self) -> None:
        self.camera_service.release()
        self.basler_service.release()
        self.motor_service.disconnect()
        self.root.destroy()
