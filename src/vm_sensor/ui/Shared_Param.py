import tkinter as tk

from typing import TypedDict
class AppState():
    def __init__(self):
        #======== Motor Var =============================
        self.abs_x_var = tk.DoubleVar(value=0)
        self.abs_y_var = tk.DoubleVar(value=0)
        self.abs_z_var = tk.DoubleVar(value=0)

        self.speed_x = tk.DoubleVar(value=20000)
        self.speed_y = tk.DoubleVar(value=20000)
        self.speed_z = tk.DoubleVar(value=5000)

        self.max_x = 50000
        self.max_y = 33500
        self.max_Z = 18000
        #======== Vision Var =============================
        self.confidence_var = tk.DoubleVar(value=0.40)
        self.threshold_var = tk.IntVar(value=120)
        self.blur_var = tk.IntVar(value=5)
        self.min_area_var = tk.IntVar(value=800)
        self.overlay_alpha_var = tk.DoubleVar(value=0.45)

