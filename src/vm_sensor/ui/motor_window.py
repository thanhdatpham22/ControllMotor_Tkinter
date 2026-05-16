import os
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
from tkinter.scrolledtext import ScrolledText
from vm_sensor.ui.base_window import BaseWindow
from vm_sensor.utils.image_utils import to_photo_image
from vm_sensor.config import PREVIEW_WIDTH, PREVIEW_HEIGHT

class MotorWindow(BaseWindow):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        
        self.jog_step_var = tk.DoubleVar(value=1.0)
        self.motor_position_var = tk.StringVar(value=self._format_motor_positions())
        self.refresh_var = tk.StringVar(value="100 ms")

        # Local photos/refs
        self.motor_photo = None
        self.input_labels = []
        self.output_buttons = []
        
        # State variables for Teach Điểm
        self.tray_data = []

        self._build_ui()
        self._refresh_motor_widgets()
        self._autoload_teach_points()
        self._update_motor_log_ui()

    def _build_ui(self) -> None:
        # ================= ROOT LAYOUT =================
        self.columnconfigure(0, weight=1, uniform="motor")
        self.columnconfigure(1, weight=1, uniform="motor")
        self.rowconfigure(0, weight=1)

        left_panel = ttk.Frame(self)
        right_panel = ttk.Frame(self)

        right_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left_panel.grid(row=0, column=1, sticky="nsew")

        # ================= LEFT PANEL =================
        left_panel.columnconfigure(0, weight=1)
        
        left_panel.rowconfigure(0, weight=0)  # action
        left_panel.rowconfigure(1, weight=0)  # jog 
        left_panel.rowconfigure(2, weight=2)  # teach points
        left_panel.rowconfigure(3, weight=1)  # speed
        left_panel.rowconfigure(4, weight=2)  # IO
        
        # ===== Action =====
        action_box = ttk.LabelFrame(left_panel, text="Motion Actions", padding=12)
        action_box.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        ttk.Button(action_box, text="Start", style="Primary.TButton", command=self._motor_start).grid(
            row=0, column=0, padx=5
        )
        ttk.Button(action_box, text="Stop", style="Primary.TButton", command=self._motor_stop).grid(
            row=0, column=1, padx=5
        )
        ttk.Button(action_box, text="Home", style="Primary.TButton", command=self._motor_home).grid(
            row=0, column=2, padx=5
        )

        # ===== Jog + Absolute =====
        jog_container = ttk.Frame(left_panel)
        jog_container.grid(row=1, column=0, sticky="nsew", pady=(0, 8))
        jog_container.columnconfigure(0, weight=1)
        jog_container.columnconfigure(1, weight=1)
        jog_container.rowconfigure(0, weight=1)

        jog_box = ttk.LabelFrame(jog_container, text="Jog XYZ", padding=12)
        abs_box = ttk.LabelFrame(jog_container, text="Absolute Move", padding=12)

        jog_box.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        abs_box.grid(row=0, column=1, sticky="nsew")

        jog_box.columnconfigure(1, weight=1)
        jog_box.columnconfigure(2, weight=1)
        abs_box.columnconfigure(0, weight=1)
        abs_box.columnconfigure(1, weight=1)

        for i in range(4): jog_box.rowconfigure(i, weight=1)
        for i in range(5): abs_box.rowconfigure(i, weight=1)

        # --- Absolute ---
        ttk.Label(abs_box, text="Position X").grid(row=0, column=0, sticky="w")
        ttk.Entry(abs_box, textvariable=self.app.state.abs_x_var, width=10).grid(row=0, column=1, sticky="ew")

        ttk.Label(abs_box, text="Position Y").grid(row=1, column=0, sticky="w")
        ttk.Entry(abs_box, textvariable=self.app.state.abs_y_var, width=10).grid(row=1, column=1, sticky="ew")

        ttk.Label(abs_box, text="Position Z").grid(row=2, column=0, sticky="w")
        ttk.Entry(abs_box, textvariable=self.app.state.abs_z_var, width=10).grid(row=2, column=1, sticky="ew")

        ttk.Button(
            abs_box,
            text="Set Position",
            style="Primary.TButton",
            command=self._set_absolute,
        ).grid(row=3, column=0, pady=(10, 0), sticky="ew", padx=(0, 5))

        ttk.Button(
            abs_box,
            text="Move To Position",
            style="Primary.TButton",
            command=self._move_absolute,
        ).grid(row=3, column=1, pady=(10, 0), sticky="ew", padx=(5, 0))

        # --- Jog ---
        # ttk.Label(jog_box, text="Jog step").grid(row=0, column=0, sticky="w")
        # ttk.Spinbox(
        #     jog_box,
        #     from_=0.01,
        #     to=1000.0,
        #     increment=0.1,
        #     textvariable=self.jog_step_var,
        #     width=10,
        # ).grid(row=0, column=1, sticky="w")

        for i, axis in enumerate(("X", "Y", "Z"), start=1):
            ttk.Label(jog_box, text=f"Axis: {axis}").grid(row=i, column=0, sticky="w", pady=(8, 0), padx=(0, 20))

            a = axis.lower()

            btn_minus = ttk.Button(jog_box, text=f"{axis}-", width=10, padding=(10, 10))
            btn_minus.grid(row=i, column=1, padx=(0, 6), pady=(8, 0), sticky="w")
            btn_minus.bind("<ButtonPress-1>", lambda e, a=a: self._motor_jog_press(a, -1))
            btn_minus.bind("<ButtonRelease-1>", lambda e, a=a: self._motor_jog_release(a, -1))
            btn_minus.bind("<Leave>", lambda e, a=a: self._motor_jog_release(a, -1))

            btn_plus = ttk.Button(jog_box, text=f"{axis}+", width=10, padding=(10, 10))
            btn_plus.grid(row=i, column=2, pady=(8, 0), sticky="w")
            btn_plus.bind("<ButtonPress-1>", lambda e, a=a: self._motor_jog_press(a, 1))
            btn_plus.bind("<ButtonRelease-1>", lambda e, a=a: self._motor_jog_release(a, 1))
            btn_plus.bind("<Leave>", lambda e, a=a: self._motor_jog_release(a, 1))
            
        # ===== TEACH POINTS (NEW) =====
        self.teach_container = ttk.LabelFrame(left_panel, padding=8)
        self.teach_container.grid(row=2, column=0, sticky="nsew", pady=(0, 8))
        self.teach_container.columnconfigure(0, weight=1)
        self.teach_container.rowconfigure(1, weight=1)

        # Custom header widget for LabelFrame (Title + Buttons on the border)
        header_frame = ttk.Frame(self.teach_container)
        ttk.Label(header_frame, text="Teach Trays", font=("Segoe UI", 10, "bold")).pack(side="left")
        
        ttk.Button(header_frame, text="Save TXT", command=self._save_teach_points, width=10).pack(side="right", padx=(5, 0))
        ttk.Button(header_frame, text="Load TXT", command=self._load_teach_points, width=10).pack(side="right", padx=(20, 0))
        
        self.teach_container.configure(labelwidget=header_frame)

        # Create a scrollable canvas for trays if there are many
        canvas = tk.Canvas(self.teach_container, highlightthickness=0, height=180)
        scrollbar = ttk.Scrollbar(self.teach_container, orient="vertical", command=canvas.yview)
        
        self.trays_frame = ttk.Frame(canvas)
        self.trays_frame.columnconfigure(0, weight=1)
        self.trays_frame.columnconfigure(1, weight=1)
        self.trays_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig("all", width=e.width))
        canvas.create_window((0, 0), window=self.trays_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.grid(row=1, column=0, sticky="nsew")
        scrollbar.grid(row=1, column=1, sticky="ns")

        # Initialize Default Trays
        self._add_tray_ui()
        self._add_tray_ui()

        # ===== Speed =====
        speed_box = ttk.LabelFrame(left_panel, text="Axis Speed", padding=12)
        speed_box.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        speed_box.columnconfigure(1, weight=1)

        self._add_motor_speed_row(speed_box, 0, "Speed X", self.app.state.speed_x)
        self._add_motor_speed_row(speed_box, 1, "Speed Y", self.app.state.speed_y)
        self._add_motor_speed_row(speed_box, 2, "Speed Z", self.app.state.speed_z)

        # ===== IO =====
        io_box = ttk.LabelFrame(left_panel, text="I/O Signals", padding=12)
        io_box.grid(row=4, column=0, sticky="nsew", pady=(0, 8))
        io_box.columnconfigure(0, weight=1)
        io_box.rowconfigure(1, weight=1)

        ttk.Label(io_box, text="I/O status", style="Status.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 8)
        )

        io_body = ttk.Frame(io_box)
        io_body.grid(row=1, column=0, sticky="nsew")
        io_body.columnconfigure(0, weight=1)
        io_body.rowconfigure(0, weight=1)

        iocanvas = tk.Canvas(io_body, highlightthickness=0, height=170)
        ioscrollbar = ttk.Scrollbar(io_body, orient="vertical", command=iocanvas.yview)

        scroll_frame = ttk.Frame(iocanvas)
        for i in range(8):
            scroll_frame.columnconfigure(i, weight=1)

        def _on_scroll_frame_configure(event):
            iocanvas.configure(scrollregion=iocanvas.bbox("all"))

        scroll_frame.bind("<Configure>", _on_scroll_frame_configure)
        def _on_canvas_configure(event):
            iocanvas.itemconfig("all", width=event.width)

        iocanvas.bind("<Configure>", _on_canvas_configure)

        iocanvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        iocanvas.configure(yscrollcommand=ioscrollbar.set)

        iocanvas.grid(row=0, column=0, sticky="nsew")
        ioscrollbar.grid(row=0, column=1, sticky="ns")

        # ===== Input =====
        ttk.Label(scroll_frame, text="INPUT", font=("Segoe UI", 10, "bold"))\
        .grid(row=0, column=0, columnspan=4, sticky="w")

        for i in range(24):
            name = self.app.motor_service.map.INPUT_NAMES.get(i+1, f"IN{i+1}")
            lbl = tk.Label(
                scroll_frame,
                text=name,
                width=10,
                relief="solid",
                bg="gray",   # OFF
                fg="white",
                font=("Segoe UI", 8)
            )
            lbl.grid(row=1 + i // 4,column=i % 4, padx=2, pady=2, sticky="ew")
            self.input_labels.append(lbl)

        # ===== Output =====
        ttk.Label(scroll_frame, text="OUTPUT", font=("Segoe UI", 10, "bold"))\
        .grid(row=0, column=4, columnspan=4, sticky="w")

        self.output_states = [False] * 24

        def toggle_output(idx: int) -> None:
            self.app.motor_service.toggle_output(idx)
            self._update_output_ui()

        for i in range(24):
            name = self.app.motor_service.map.OUTPUT_NAMES.get(i+1, f"OUT{i+1}")
            btn = tk.Button(
                scroll_frame,
                text=name,
                width=10,
                bg="lightgray",
                command=lambda i=i: toggle_output(i),
                font=("Segoe UI", 8)
            )
            btn.grid(row=1 + i // 4,
                     column=4 + (i % 4), padx=2, pady=2, sticky="ew")
            self.output_buttons.append(btn)

        # ================= RIGHT PANEL =================
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(0, weight=2)  # preview 
        right_panel.rowconfigure(1, weight=0)
        right_panel.rowconfigure(2, weight=1)  # log

        # ===== Preview =====
        preview_box = ttk.LabelFrame(right_panel, text="Camera Preview", padding=12)
        preview_box.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        preview_box.columnconfigure(0, weight=1)
        preview_box.rowconfigure(0, weight=1)

        self.motor_camera_label = ttk.Label(preview_box, anchor="center")
        self.motor_camera_label.grid(row=0, column=0, sticky="nsew")

        # ===== Position =====
        position_box = ttk.LabelFrame(right_panel, text="Axis Position", padding=12)
        position_box.grid(row=1, column=0, sticky="ew", pady=(0, 8))

        ttk.Label(
            position_box,
            textvariable=self.motor_position_var,
            font=("Consolas", 11),
        ).grid(row=0, column=0, sticky="w")

        # ===== Log =====
        log_box = ttk.Frame(right_panel)
        log_box.grid(row=2, column=0, sticky="nsew")
        log_box.columnconfigure(0, weight=1)
        log_box.rowconfigure(1, weight=1)

        header = ttk.Frame(log_box)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        ttk.Label(header, text="Command Log", font=("Segoe UI", 10, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        
        self.refresh_combo = ttk.Combobox(
            header,
            textvariable=self.refresh_var,
            values=["1 ms","10 ms", "50 ms", "100 ms", "200 ms", "500 ms", "1000 ms"],
            width=10,
            state="readonly",
        )
        self.refresh_combo.grid(row=0, column=1, sticky="e")
        self.refresh_combo.bind("<<ComboboxSelected>>", self.on_refresh_change)

        self.motor_log_text = ScrolledText(
            log_box,
            font=("Consolas", 10),
            wrap="word",
        )
        self.motor_log_text.grid(row=1, column=0, sticky="nsew")
        self.motor_log_text.configure(state="disabled")

    def _add_motor_speed_row(self, parent: ttk.LabelFrame, row: int, title: str, variable: tk.DoubleVar) -> None:
        ttk.Label(parent, text=title).grid(
            row=row, column=0, sticky="w", padx=(0, 12), pady=4
        )
        scale = tk.Scale(
            parent,
            variable=variable,
            from_=0,
            to= 50000,
            orient="horizontal",
            resolution=1,
            showvalue=True,
            highlightthickness=0,
        )
        scale.grid(row=row, column=1, sticky="ew", pady=4)

    def _motor_start(self) -> None:
         self.app.motor_service.enqueue_start(self)

    def _motor_stop(self) -> None:
        self._handle_motor_result(self.app.motor_service.stop())

    def _motor_home(self) -> None:
        self._handle_motor_result(self.app.motor_service.home())

    def _set_absolute(self):
        try:
            x = int(self.app.state.abs_x_var.get())
            y = int(self.app.state.abs_y_var.get())
            z = int(self.app.state.abs_z_var.get())
            sp_x = int(self.app.state.speed_x.get())
            sp_y = int(self.app.state.speed_y.get())
            sp_z = int(self.app.state.speed_z.get())
            # ===== LIMIT =====
            X_MIN, X_MAX = 0, 55000
            Y_MIN, Y_MAX = 0, 33500
            Z_MIN, Z_MAX = 0, 20000
            if not (X_MIN <= x <= X_MAX):
                raise ValueError(f"X must be in range [{X_MIN}, {X_MAX}]")
            if not (Y_MIN <= y <= Y_MAX):
                raise ValueError(f"Y must be in range [{Y_MIN}, {Y_MAX}]")
            if not (Z_MIN <= z <= Z_MAX):
                raise ValueError(f"Z must be in range [{Z_MIN}, {Z_MAX}]")
            
            self.app.motor_service.enqueue_move_absolute(x, y, z, sp_x, sp_y, sp_z)
        except ValueError as e:
            messagebox.showerror("Invalid Input", str(e))
        except Exception as e:
            messagebox.showerror("Error", str(e))
            
    def _move_absolute(self):
        if not self.app.motor_service or not self.app.motor_service.is_connected():
            return
        self.app.motor_service.enqueue_set_absolute()

    def _apply_motor_speeds(self) -> None:
        result = self.app.motor_service.set_all_speeds(
            self.app.state.speed_x.get(),
            self.app.state.speed_y.get(),
            self.app.state.speed_z.get(),
        )
        self._handle_motor_result(result)

    def _handle_motor_result(self, result: tuple[bool, str]) -> None:
        _, message = result
        self.app.status_var.set(message)  # Hiển thị lên thanh status bar cố định
        self._refresh_motor_widgets()

    def _refresh_motor_widgets(self) -> None:
        snapshot = self.app.motor_service.snapshot()
        positions = snapshot["positions"]
        self.motor_position_var.set(
            f"X: {positions['x']}    Y: {positions['y']}    Z: {positions['z']}"
        )

        self.motor_log_text.configure(state="normal")
        self.motor_log_text.delete("1.0", tk.END)
        if self.app.motor_service.modbus:
            for line in self.app.motor_service.modbus.get_recent_log():
                self.motor_log_text.insert(tk.END, f"{line}\n")
        self.motor_log_text.see(tk.END)
        self.motor_log_text.configure(state="disabled")

    def _format_motor_positions(self) -> str:
        positions = self.app.motor_service.snapshot()["positions"]
        return f"X: {positions['x']}    Y: {positions['y']}    Z: {positions['z']}"

    def on_refresh_change(self, event):
        interval = int(self.refresh_var.get().split()[0])
        self.app.motor_service.set_refresh_interval(interval)

    def _update_motor_log_ui(self):
        if self.app.motor_service.modbus:
            log_queue = self.app.motor_service.modbus.log_queue
            new_text = self._format_motor_positions()

            if new_text != self.motor_position_var.get():
                self.motor_position_var.set(new_text)
            self.motor_log_text.configure(state="normal")

            while not log_queue.empty():
                line = log_queue.get()
                self.motor_log_text.insert(tk.END, line + "\n")

            self.motor_log_text.see(tk.END)
            self.motor_log_text.configure(state="disabled")

            if hasattr(self.app.motor_service, "input_states"):
                self._update_input_ui(self.app.motor_service.input_states)
            self._update_output_ui()

        self.after(50, self._update_motor_log_ui) 

    def _motor_jog_press(self, axis: str, direction: int):
        if not self.app.motor_service or not self.app.motor_service.is_connected():
            return
        self.app.motor_service.enqueue_jog(axis, direction, True)

    def _motor_jog_release(self, axis: str, direction: int):
        if not self.app.motor_service or not self.app.motor_service.is_connected():
            return
        self.app.motor_service.enqueue_jog(axis, direction, False) 

    def _update_input_ui(self, inputs):
        for i, val in enumerate(inputs):
            if i < len(self.input_labels):
                self.input_labels[i].config(
                    bg="green" if val else "gray"
                )

    def _update_output_ui(self):
        if hasattr(self.app.motor_service, "output_states"):
            for i, state in enumerate(self.app.motor_service.output_states):
                # Ensure we don't index out of bounds
                if i < len(self.output_buttons):
                    btn = self.output_buttons[i]
                    btn.config(bg="green" if state else "lightgray")

    def _render_motor_camera(self, frame) -> None:
        self.motor_photo = to_photo_image(frame, PREVIEW_WIDTH, PREVIEW_HEIGHT)
        self.motor_camera_label.configure(image=self.motor_photo)

    def _add_tray_ui(self):
        tray_index = len(self.tray_data)

        tray_frame = ttk.Frame(self.trays_frame)
        grid_row = tray_index // 2
        grid_col = tray_index % 2
        tray_frame.grid(row=grid_row, column=grid_col, sticky="nsew", padx=4, pady=4)

        header_btn = ttk.Button(tray_frame, text=f"▼ Tray {tray_index + 1}", cursor="hand2")
        header_btn.pack(fill="x")

        body_frame = ttk.Frame(tray_frame, padding=(10, 5))
        body_frame.pack(fill="x")

        # Toggle collapse/expand
        # def toggle_tray(f=body_frame, b=header_btn, idx=tray_index + 1):
        #     if f.winfo_ismapped():
        #         f.pack_forget()
        #         b.configure(text=f"► Tray {idx}")
        #     else:
        #         f.pack(fill="x")
        #         b.configure(text=f"▼ Tray {idx}")

        # header_btn.configure(command=toggle_tray)

        # Action Buttons for Scan
        action_row = ttk.Frame(body_frame)
        action_row.pack(fill="x", pady=(5, 10))

        ttk.Button(
            action_row,
            text="▶ Start Scan (15x5)",
            style="Primary.TButton",
            command=lambda idx=tray_index: self.app.scan_handler.start_scan(idx)
        ).pack(side="left", padx=5)

        ttk.Button(
            action_row,
            text="⏹ Stop",
            command=self.app.scan_handler.stop_scan
        ).pack(side="left", padx=5)

        # Points
        points_vars = []
        for p in range(1, 4):
            row_frame = ttk.Frame(body_frame)
            row_frame.pack(fill="x", pady=2)

            ttk.Label(row_frame, text=f"P{p}", width=3, font=("Segoe UI", 9, "bold")).pack(side="left")
            x_var = tk.IntVar(value=0)
            y_var = tk.IntVar(value=0)
            z_var = tk.IntVar(value=0)

            ttk.Label(row_frame, text="X").pack(side="left", padx=(5,2))
            ttk.Entry(row_frame, textvariable=x_var, width=6).pack(side="left")
            ttk.Label(row_frame, text="Y").pack(side="left", padx=(5,2))
            ttk.Entry(row_frame, textvariable=y_var, width=6).pack(side="left")
            ttk.Label(row_frame, text="Z").pack(side="left", padx=(5,2))
            ttk.Entry(row_frame, textvariable=z_var, width=6).pack(side="left")

            def get_pos(xv=x_var, yv=y_var, zv=z_var):
                pos = self.app.motor_service.snapshot()["positions"]
                xv.set(str(pos['x']))
                yv.set(str(pos['y']))
                zv.set(str(pos['z']))

            def move_to(xv=x_var, yv=y_var, zv=z_var):
                try:
                    x = int(xv.get())
                    y = int(yv.get())
                    z = int(zv.get())
                    sp_x = int(self.app.state.speed_x.get())
                    sp_y = int(self.app.state.speed_y.get())
                    sp_z = int(self.app.state.speed_z.get())

                    X_MIN, X_MAX = 0, 55000
                    Y_MIN, Y_MAX = 0, 33500
                    Z_MIN, Z_MAX = 0, 20000
                    if not (X_MIN <= x <= X_MAX):
                        raise ValueError(f"X must be in range [{X_MIN}, {X_MAX}]")
                    if not (Y_MIN <= y <= Y_MAX):
                        raise ValueError(f"Y must be in range [{Y_MIN}, {Y_MAX}]")
                    if not (Z_MIN <= z <= Z_MAX):
                        raise ValueError(f"Z must be in range [{Z_MIN}, {Z_MAX}]")

                    self.app.motor_service.enqueue_move_absolute(x, y, z, sp_x, sp_y, sp_z)
                    self._move_absolute()
                except ValueError as e:
                    messagebox.showerror("Invalid Input", str(e))
                except Exception as e:
                    messagebox.showerror("Error", str(e))

            ttk.Button(row_frame, text="Move", command=move_to, width=6).pack(side="right", padx=(5,0))
            ttk.Button(row_frame, text="Get Pos", command=get_pos, width=8).pack(side="right", padx=(5,0))
            points_vars.append({"x": x_var, "y": y_var, "z": z_var})

        self.tray_data.append(points_vars)

    def _autoload_teach_points(self):
        # Tự động tìm tệp trong thư mục Teach_Point ở thư mục gốc
        default_dir = os.path.join(os.getcwd(), "Teach_Point")
        if os.path.exists(default_dir):
            files = [f for f in os.listdir(default_dir) if f.endswith(".txt")]
            if files:
                # Ưu tiên load tệp origin_point.txt nếu có, nếu không thì load tệp đầu tiên
                target = "origin_point.txt" if "origin_point.txt" in files else files[0]
                filepath = os.path.join(default_dir, target)
                self._load_teach_points(filepath, show_msg=False)

    def _load_teach_points(self, filepath=None, show_msg=True):
        if not filepath:
            filepath = filedialog.askopenfilename(
                filetypes=[("Text files", "*.txt")],
                title="Load Teach Points"
            )
        
        if not filepath:
            return

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = [l.strip() for l in f.readlines() if l.strip()]
            
            line_idx = 0
                
            for tray in self.tray_data:
                for pt in tray:
                    if line_idx < len(lines):
                        parts = lines[line_idx].split(',')
                        if len(parts) >= 3:
                            pt["x"].set(parts[0].strip())
                            pt["y"].set(parts[1].strip())
                            pt["z"].set(parts[2].strip())
                    else:
                        pt["x"].set("0")
                        pt["y"].set("0")
                        pt["z"].set("0")
                    line_idx += 1
                    
            if show_msg:
                messagebox.showinfo("Success", f"Loaded {len(lines)} points successfully.")
        except Exception as e:
            if show_msg:
                messagebox.showerror("Error", f"Failed to load:\n{str(e)}")

    def _save_teach_points(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")],
            title="Save Teach Points"
        )
        if not filepath:
            return

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                for t_idx, tray in enumerate(self.tray_data):
                    for p_idx, pt in enumerate(tray):
                        x = pt["x"].get()
                        y = pt["y"].get()
                        z = pt["z"].get()
                        f.write(f"{x},{y},{z}\n")
            messagebox.showinfo("Success", f"Teach points saved successfully to {os.path.basename(filepath)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save:\n{str(e)}")
