import tkinter as tk
from tkinter import messagebox, filedialog, ttk
from vm_sensor.config import MODEL_DIR, OUTPUT_DIR
from vm_sensor.models import SegmentSettings
from vm_sensor.ui.base_window import BaseWindow
from vm_sensor.services.basler_camera_service import BaslerDeviceInfo

class SettingWindow(BaseWindow):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.basler_devices: list[BaslerDeviceInfo] = []
        
        # --- Motor COM Vars ---
        self.com_port_var = tk.StringVar(value="")
        self.baudrate_var = tk.StringVar(value="115200")
        self.motor_status_var = tk.StringVar(value=self.app.motor_service.status_message)
        
        # --- Vision Vars ---
        self.source_type_var = tk.StringVar(value="camera")
        self.camera_backend_var = tk.StringVar(value="opencv")
        self.basler_device_var = tk.StringVar(value="")
        self.image_folder_var = tk.StringVar(value="")
        self.camera_index_var = tk.IntVar(value=0)
        
        self.model_path_var = tk.StringVar(value="")
        self.source_summary_var = tk.StringVar(value="Source: OpenCV camera #0")
        self.basler_sdk_var = tk.StringVar(value=self.app.basler_service.sdk_status())
        
        self._build_ui()
        self._refresh_basler_devices(silent=True)
        self._refresh_com_ports(silent=True)
        self._update_source_widgets()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)

        # ---------------------
        # COM CONNECTION
        # ---------------------
        connection_box = ttk.LabelFrame(self, text="COM Connection", padding=12)
        connection_box.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        connection_box.columnconfigure(1, weight=1)

        ttk.Label(connection_box, text="COM port").grid(row=0, column=0, sticky="w")
        self.com_port_combo = ttk.Combobox(
            connection_box,
            textvariable=self.com_port_var,
            state="readonly",
        )
        self.com_port_combo.grid(row=0, column=1, sticky="ew", padx=8)

        ttk.Button(connection_box, text="Refresh Ports", command=self._refresh_com_ports).grid(
            row=0, column=2
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
        ).grid(row=1, column=2, pady=(10, 0))

        ttk.Button(
            connection_box,
            text="Disconnect",
            command=self._disconnect_motor,
        ).grid(row=1, column=3, padx=(8, 0), pady=(10, 0))

        ttk.Label(
            connection_box,
            textvariable=self.motor_status_var,
            style="Status.TLabel",
            wraplength=500,
        ).grid(row=2, column=0, columnspan=4, sticky="w", pady=(10, 0))

        # ---------------------
        # SOURCE
        # ---------------------
        source_box = ttk.LabelFrame(self, text="Source", padding=12)
        source_box.grid(row=1, column=0, sticky="ew", pady=(0, 12))
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

        # ---------------------
        # YOLO MODEL
        # ---------------------
        model_box = ttk.LabelFrame(self, text="YOLO Model", padding=12)
        model_box.grid(row=2, column=0, sticky="ew", pady=(0, 12))
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

        # ---------------------
        # CAMERA BACKEND
        # ---------------------
        camera_box = ttk.LabelFrame(self, text="Camera", padding=12)
        camera_box.grid(row=3, column=0, sticky="ew", pady=(0, 12))
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

    # --- COM CONNECTION LOGIC ---
    def _refresh_com_ports(self, silent: bool = False) -> None:
        ports, message = self.app.motor_service.list_ports()
        previous_port = self.com_port_var.get().strip()
        self.com_port_combo["values"] = ports
        if previous_port in ports:
            self.com_port_var.set(previous_port)
        elif ports:
            self.com_port_var.set(ports[0])
        else:
            self.com_port_var.set("")
        self.motor_status_var.set(message)
        if not silent:
            self.app.status_var.set(message)

    def _connect_motor(self) -> None:
        try:
            baudrate = int(self.baudrate_var.get())
        except ValueError:
            messagebox.showwarning("Motor", "Invalid baudrate.")
            return

        ok, message = self.app.motor_service.connect(
            port=self.com_port_var.get().strip(), baudrate=baudrate, timeout=0.2,
        )
        self.motor_status_var.set(message)
        self.app.status_var.set(message)
        
        if self.app.motor_service:
            if hasattr(self.app, 'motor_tab'):
                self.app.motor_service.ui_callback = self.app.motor_tab._update_input_ui
        self.app.motor_service.start_worker() 
        if not ok:
            messagebox.showwarning("Motor", message)

    def _disconnect_motor(self) -> None:
        _, message = self.app.motor_service.disconnect()
        self.motor_status_var.set(message)
        self.app.status_var.set(message)


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
            self.app.status_var.set(message)
            if not success:
                messagebox.showwarning("Camera source", message)
            return

        folder_path = self.image_folder_var.get().strip()
        if not folder_path:
            messagebox.showinfo("Source", "Choose an image folder first.")
            return

        self.app.active_source_type = "folder"
        self.app.camera_service.release()
        self.app.basler_service.release()
        success, message = self.app.folder_service.load_folder(folder_path)
        self.app.current_frame = self.app.folder_service.read_frame()
        self.app.main_tab._render_realtime(self.app.current_frame)
        self.app.status_var.set(message)
        self._update_source_widgets()

        if not success:
            messagebox.showwarning("Folder source", message)

    def _activate_camera_source(self) -> tuple[bool, str]:
        self.app.active_source_type = "camera"
        selected_backend = self.camera_backend_var.get()

        if selected_backend == "opencv":
            self.app.basler_service.release()
            success = self.app.camera_service.set_camera_index(self.camera_index_var.get())
            self.app.active_camera_backend = "opencv"
            self.app.current_frame = self.app.camera_service.read_frame()
            self.app.main_tab._render_realtime(self.app.current_frame)

            if success:
                message = f"Connected to OpenCV camera #{self.camera_index_var.get()}."
            else:
                message = f"Camera #{self.camera_index_var.get()} is not available."

            self._update_source_widgets()
            return success, message

        self.app.camera_service.release()
        if not self.basler_devices:
            self._refresh_basler_devices(silent=True)

        selected_serial = self._selected_basler_serial()
        success, message = self.app.basler_service.connect(selected_serial)
        self.app.active_camera_backend = "basler"
        self.app.current_frame = self.app.basler_service.read_frame()
        self.app.main_tab._render_realtime(self.app.current_frame)
        self._update_basler_status_label(message)
        self._update_source_widgets()
        return success, message

    def _apply_camera_connection(self) -> None:
        if self.source_type_var.get() != "camera":
            self.app.status_var.set(
                "Camera settings saved. Select source Camera and click Apply Source to use them."
            )
            return

        success, message = self._activate_camera_source()
        self.app.status_var.set(message)
        if not success:
            messagebox.showwarning("Camera", message)

    def _refresh_basler_devices(self, silent: bool = False) -> None:
        previous_serial = self._selected_basler_serial()
        self.basler_devices, message = self.app.basler_service.list_devices()

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
            self.app.status_var.set(message)

    def _update_basler_status_label(self, message: str) -> None:
        sdk_status = self.app.basler_service.sdk_status()
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

        message = self.app.segmenter.load_model(model_path)
        self.app.main_tab.segment_mode_var.set(message)
        self.app.status_var.set(message)

    def _current_settings(self, confidence, threshold, blur, min_area, alpha) -> SegmentSettings:
        # Lấy file hiện tại để pass sang segment
        return SegmentSettings(
            confidence=round(confidence, 2),
            threshold=int(threshold),
            blur_kernel=int(blur),
            min_area=int(min_area),
            overlay_alpha=round(alpha, 2),
            source_type=self.app.active_source_type,
            camera_backend=self.app.active_camera_backend,
            camera_index=int(self.camera_index_var.get()),
            basler_serial=self._selected_basler_serial(),
            image_folder=self.image_folder_var.get().strip() or None,
            model_path=self.model_path_var.get().strip() or None,
        )

    def _update_source_widgets(self) -> None:
        selected_is_folder = self.source_type_var.get() == "folder"
        selected_is_camera = not selected_is_folder
        selected_is_basler = selected_is_camera and self.camera_backend_var.get() == "basler"
        active_has_folder_images = (
            self.app.active_source_type == "folder" and bool(self.app.folder_service.image_paths)
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

        # VisionWindow has the next/prev buttons, handle dynamically
        if active_has_folder_images:
            if hasattr(self.app, 'main_tab'): 
               self.app.main_tab.prev_image_button.state(["!disabled"])
               self.app.main_tab.next_image_button.state(["!disabled"])
        else:
            if hasattr(self.app, 'main_tab'): 
               self.app.main_tab.prev_image_button.state(["disabled"])
               self.app.main_tab.next_image_button.state(["disabled"])

        self.source_summary_var.set(self._source_summary())
        if hasattr(self.app, 'main_tab'):
            self.app.main_tab.source_summary_var.set(self.source_summary_var.get())

    def _source_summary(self) -> str:
        if self.app.active_source_type == "camera":
            if self.app.active_camera_backend == "basler":
                if self.app.basler_service.connected_device is not None:
                    return f"Source: Basler {self.app.basler_service.connected_device.display_name}"

                selected_label = self.basler_device_var.get().strip()
                if selected_label:
                    return f"Source: Basler selected - {selected_label}"
                return "Source: Basler camera not connected"

            return f"Source: OpenCV camera #{self.camera_index_var.get()}"

        if self.app.folder_service.image_paths:
            return f"Source: {self.app.folder_service.summary()}"

        folder_path = self.image_folder_var.get().strip()
        if folder_path:
            return f"Source: Folder selected - {folder_path}"
        return "Source: Folder not selected"
