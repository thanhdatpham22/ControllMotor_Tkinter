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
                
                r = i // 15
                c_snake = i % 15
                c = c_snake if r % 2 == 0 else (14 - c_snake)
                
                # Gửi lệnh di chuyển
                self.app.motor_service.enqueue_move_absolute(
                    int(pt['x']), int(pt['y']), int(pt['z']),
                    sp_x, sp_y, sp_z
                )
                self.app.motor_service.enqueue_set_absolute()
                
                # Cập nhật Cycle Time tạm tính
                self.app.main_tab.cycle_time_var.set(f"{time.time() - start_time:.2f}s")
                
                # Dừng 1s theo yêu cầu để ổn định và chụp ảnh
                time.sleep(0.5) 

                # Gọi hàm capture và xử lý ảnh có sẵn từ main_tab
                self.app.main_tab._capture_segment()
                
                # Lấy kết quả
                segment_result = self.app.main_tab.segment_result
                
                if segment_result and len(segment_result.polygons) > 0:
                    color = "#dc3545"  # Red
                else:
                    color = "#28a745"  # Green
                
                def update_grid_color(tr_idx=self._current_tray_index, row=r, col=c, colr=color):
                    self.app.main_tab.update_cell_color(tr_idx, row, col, colr)
                    
                self.app.root.after(0, update_grid_color)
                
            if not self._stop_event.is_set():
                self.app.status_var.set("Scan Completed successfully.")
                self.app.main_tab.machine_status_var.set("IDLE")
                messagebox.showinfo("Done", "Tray scan process completed.")
        except Exception as e:
            self.app.status_var.set(f"Scan interrupted: {e}")
            self.app.main_tab.machine_status_var.set("ERROR")
        finally:
            self.is_running = False
