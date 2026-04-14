import tkinter as tk

from typing import TypedDict
class AppState():
    def __init__(self):
        self.abs_x_var = tk.DoubleVar(value=0)
        self.abs_y_var = tk.DoubleVar(value=0)
        self.abs_z_var = tk.DoubleVar(value=0)

        self.speed_x = tk.DoubleVar(value=5)
        self.speed_y = tk.DoubleVar(value=5)
        self.speed_z = tk.DoubleVar(value=5)


