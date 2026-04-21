import tkinter as tk

from typing import TypedDict
class AppState():
    def __init__(self):
        self.abs_x_var = tk.DoubleVar(value=0)
        self.abs_y_var = tk.DoubleVar(value=0)
        self.abs_z_var = tk.DoubleVar(value=0)

        self.speed_x = tk.DoubleVar(value=20000)
        self.speed_y = tk.DoubleVar(value=20000)
        self.speed_z = tk.DoubleVar(value=5000)

        self.max_x = 50000
        self.max_y = 33500
        self.max_Z = 18000


