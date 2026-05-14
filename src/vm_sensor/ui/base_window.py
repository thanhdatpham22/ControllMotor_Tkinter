from tkinter import ttk

class BaseWindow(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=12)

        # app = MainWindow
        self.app = app