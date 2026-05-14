import time
import threading
from tkinter import messagebox

class TrayScanHandler:
    def __init__(self, app):
        self.app = app
        self.is_running = False
        self._stop_event = threading.Event()

    def calculate_grid_points(self, p1, p2, p3):
        """
        Nội suy tọa độ cho Grid 15 cột x 5 hàng.
        P1: Góc trên - trái (Gốc)
        P2: Góc trên - phải (Xác định trục X và độ rộng cột)
        P3: Góc dưới - trái (Xác định trục Y và độ cao hàng)
        
        Trả về danh sách các điểm {x, y, z} theo thứ tự chạy hình con rắn (Snake pattern).
        """
        rows = 5
        cols = 15
        
        points = []
        
        # Tính toán vector đơn vị cho mỗi bước (step vector)
        # Giả định P1 -> P2 là hướng Cột (15 cột tương ứng 14 khoảng chia)
        # Giả định P1 -> P3 là hướng Hàng (5 hàng tương ứng 4 khoảng chia)
        
        step_x = {k: (p2[k] - p1[k]) / (cols - 1) for k in ['x', 'y', 'z']}
        step_y = {k: (p3[k] - p1[k]) / (rows - 1) for k in ['x', 'y', 'z']}
        
        for r in range(rows):
            row_points = []
            for c in range(cols):
                # Tọa độ nội suy: P = P1 + r*StepY + c*StepX
                pt = {
                    'x': round(p1['x'] + r * step_y['x'] + c * step_x['x']),
                    'y': round(p1['y'] + r * step_y['y'] + c * step_x['y']),
                    'z': round(p1['z'] + r * step_y['z'] + c * step_x['z'])
                }
                row_points.append(pt)
            
            # Pattern: Row 0 chạy 0->14, Row 1 chạy 14->0 (Snake/Zig-zag)
            if r % 2 != 0:
                row_points.reverse()
                
            points.extend(row_points)
            
        return points

    def start_scan(self, tray_index):
        if self.is_running:
            messagebox.showwarning("Warning", "A scan is already in progress.")
            return
            
        try:
            # Lấy dữ liệu từ MotorWindow
            if tray_index >= len(self.app.motor_tab.tray_data):
                messagebox.showerror("Error", f"Tray {tray_index + 1} not found.")
                return

            tray = self.app.motor_tab.tray_data[tray_index]
            # Mỗi tray có 3 điểm P1, P2, P3
            # Dữ liệu lưu trong StringVar/IntVar
            p1 = {k: float(tray[0][k].get()) for k in ['x', 'y', 'z']}
            p2 = {k: float(tray[1][k].get()) for k in ['x', 'y', 'z']}
            p3 = {k: float(tray[2][k].get()) for k in ['x', 'y', 'z']}
            
            grid = self.calculate_grid_points(p1, p2, p3)
            
            self._current_tray_index = tray_index
            self._stop_event.clear()
            thread = threading.Thread(target=self._scan_executor, args=(grid,), daemon=True)
            thread.start()
            
        except Exception as e:
            messagebox.showerror("Data Error", f"Vui lòng kiểm tra tọa độ tray: {e}")

    def stop_scan(self):
        self._stop_event.set()
        self.app.status_var.set("Scanning stopped by user.")

    def _scan_executor(self, grid):
        self.is_running = True
        self.app.status_var.set("Scanning... [BUSY]")
        
        try:
            # Lấy tốc độ hiện tại từ AppState
            sp_x = int(self.app.state.speed_x.get()) or 2000
            sp_y = int(self.app.state.speed_y.get()) or 2000
            sp_z = int(self.app.state.speed_z.get()) or 1000
            
            start_time = time.time()
            self.app.main_tab.machine_status_var.set("RUNNING")

            for i, pt in enumerate(grid):
                if self._stop_event.is_set():
                    break
                
                # Hiển thị tiến trình trên Status Bar
                self.app.status_var.set(f"Tray Scanning: Point {i+1}/{len(grid)} - Coord: {pt['x']},{pt['y']},{pt['z']}")
                self.app.main_tab.item_count_var.set(f"{i+1} / {len(grid)}")
                
                # Cập nhật màu sắc trên Canvas Tray Map
                # Phải đoán xem đang ở khay nào dựa trên tray_index (0 hoặc 1)
                # i là index trong grid (0..74)
                # Trình tự: row 0..4, col 0..14
                # Do pattern snake nên phải cẩn thận khi map ngược lại index vẽ
                # Nhưng tạm thời ta chỉ cần đổi màu dựa trên tags đã gắn: tags=f"tray_{t}_cell_{r}_{c}"
                # Để đơn giản, ta lặp qua grid theo r, c và tìm tag
                # Vì grid được tạo bởi 5 rows * 15 cols, ta có thể tính ngược r, c
                r = i // 15
                c_snake = i % 15
                c = c_snake if r % 2 == 0 else (14 - c_snake)
                
                tray_tag = f"tray_{self._current_tray_index}_cell_{r}_{c}"
                self.app.main_tab.tray_canvas.itemconfig(tray_tag, fill="#28a745") # Green
                
                # Gửi lệnh di chuyển
                self.app.motor_service.enqueue_move_absolute(
                    int(pt['x']), int(pt['y']), int(pt['z']),
                    sp_x, sp_y, sp_z
                )
                self.app.motor_service.enqueue_set_absolute()
                
                # Cập nhật Cycle Time tạm tính
                self.app.main_tab.cycle_time_var.set(f"{time.time() - start_time:.2f}s")
                
                time.sleep(2) 
                
            if not self._stop_event.is_set():
                self.app.status_var.set("Scan Completed successfully.")
                self.app.main_tab.machine_status_var.set("IDLE")
                messagebox.showinfo("Done", "Tray scan process completed.")
        except Exception as e:
            self.app.status_var.set(f"Scan interrupted: {e}")
            self.app.main_tab.machine_status_var.set("ERROR")
        finally:
            self.is_running = False
