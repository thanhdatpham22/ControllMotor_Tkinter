
import threading
import time
import queue
from typing import Literal
from vm_sensor.services.modbus_service import ModbusRTUService
from vm_sensor.reg_mapping import RegisterMap
from vm_sensor.ui.Shared_Param import AppState 
from typing import TypedDict
AxisName = Literal["x", "y", "z"]
try:
    import serial
    from serial.tools import list_ports
except ImportError:  # pragma: no cover - optional runtime dependency
    serial = None
    list_ports = None
class PositionDict(TypedDict):
    x: float
    y: float
    z: float

class SnapshotDict(TypedDict):
    connected: bool
    connected_port: str | None
    baudrate: int
    positions: PositionDict
    speeds: dict[str, float]
    status: str
class MotorControllerService():
    def __init__(self, reg_map: RegisterMap):
        self.modbus: ModbusRTUService | None = None
        self.connected_port = None
        self.baudrate = 115200
        self.timeout = 0.2
        self.axis_positions = {"x": 0, "y": 0, "z": 0}
        self.axis_speeds: dict[AxisName, float] = {"x": 20.0, "y": 20.0, "z": 10.0}
        self._polling = False
        self.refresh_interval = 100
        self.status_message = "Motor service ready. Waiting for COM connection or mock commands."
        self.map = reg_map
        self.param = AppState()
        self.cmd_queue = queue.Queue()
    def snapshot(self) -> SnapshotDict:
        return {
            "connected": bool(self.is_connected()),
            "connected_port": self.connected_port,
            "baudrate": int(self.baudrate),

            "positions": {
                "x": float(self.axis_positions["x"]),
                "y": float(self.axis_positions["y"]),
                "z": float(self.axis_positions["z"]),
            },

            "speeds": {
                "x": float(self.axis_speeds["x"]),
                "y": float(self.axis_speeds["y"]),
                "z": float(self.axis_speeds["z"]),
            },

            "status": str(self.status_message),
        }
    def list_ports(self) -> tuple[list[str], str]:
        if list_ports is None:
            return [], "pyserial is not installed. COM port scan is unavailable."

        ports = [port.device for port in list_ports.comports()]
        if not ports:
            return [], "No COM port detected."
        print("List Ports: ",list_ports)
        return ports, f"Found {len(ports)} COM port(s)."
    def set_refresh_interval(self, interval_ms: int):
        self.refresh_interval = interval_ms
    def start_worker(self):
        threading.Thread(target=self._worker_loop, daemon=True).start()
        threading.Thread(target=self._poll_loop, daemon=True).start()
    def _worker_loop(self):
        while self._polling:
            func, args = self.cmd_queue.get()
            # print("Have get Queue Signal")
            try:
                func(*args)
            except Exception as e:
                if self.modbus:
                    self.modbus._log(f"Worker error: {e}")

    # ================= CONNECT =================
    def connect(self, port, baudrate=115200, timeout = 0.2):
        try:
            self.modbus = ModbusRTUService(port, baudrate)
            self.connected_port = port
            self.timeout = timeout
            self.modbus._log(f"Connected {port}")
            
            self._polling = True
            self.start_worker()
            self.home()
            return True, "Connected"
        except Exception as e:
            if self.modbus:
                self.modbus._log(f"Connect error: {e}")
            return False, str(e)

    def disconnect(self):
        self._polling = False
        if self.modbus:
            try:
                self.modbus.close()
            except:
                pass
        if self.modbus:
            self.modbus._log("Disconnected")   # ✅ log ở motor
        # self.modbus = None
        self.connected_port = None
        return True, "Disconnected"

    def is_connected(self):
        return self.modbus is not None
    # ================= POLLING =================
    def _poll_loop(self):
        count = 0
        while self._polling:
            # count += 1
            if self.modbus:
                try:
                    res = self.modbus.read_holding_registers(1, 0, 3)
                    if res :
                        values = self.modbus._parse_registers(res)
                        if values:
                            self.axis_positions["x"] = values[0]
                            self.axis_positions["y"] = values[1]
                            self.axis_positions["z"] = values[2]
                            print(f"POS X:{values[0]} Y:{values[1]} Z:{values[2]}")
                            self.modbus._log(f"POS X:{values[0]} Y:{values[1]} Z:{values[2]}")    
                except Exception as e:
                    self.modbus._log(f"Poll error: {e}")
            time.sleep(self.refresh_interval/1000.0)
            # self._stop_event.wait(interval / 1000.0)

    # ================= COMMAND =================
    def home(self) -> tuple [bool, str]:
        if self.modbus:
                self.modbus.write_single_coil(1, self.map.COIL_HOME, True)
        return True ,"GO HOME OK"
    def move_absolute(self, x, y, z, sx, sy, sz):
        try:
            # ===== convert về int 16-bit =====
            def to_uint16(val):
                return int(val) & 0xFFFF

            values = [
                to_uint16(x), to_uint16(sx), 1000,
                to_uint16(y), to_uint16(sy), 1000,
                to_uint16(z), to_uint16(sz), 1000
            ]
            if self.modbus:
                self.modbus.write_multiple_registers(
                    1,
                    self.map.REG_TARGET["x"],
                    values
                )

                # trigger
                self.modbus.write_single_coil(1, self.map.COIL_SET_POINT, True)
                time.sleep(0.05)
                self.modbus.write_single_coil(1, self.map.COIL_SET_POINT, False)

                self.modbus._log(f"Move to X={x}, Y={y}, Z={z}")

        except Exception as e:
            from tkinter import messagebox  
            messagebox.showerror("Move Error", str(e))

    def _jog(self, axis, direction, is_on: bool):
        if not self.modbus:
            return
        addr = self.map.COIL_JOG[(axis, direction)]
        self.modbus.write_single_coil(
            1,
            addr,
            is_on
        )     
    def set_all_speeds(self, sp_X, sp_y, sp_z)-> tuple [bool, str]:

        return True ,"Set_all_speeds ok"

    def move_x(self, value):
        return self._write_reg(0, value)

    def move_y(self, value):
        return self._write_reg(1, value)

    def move_z(self, value):
        return self._write_reg(2, value)

    def start(self):
        return self._write_reg(10, 1)

    def stop(self):
        return self._write_reg(10, 0)
    

    def enqueue_move_absolute(self, x, y, z, sx, sy, sz):
        self.cmd_queue.put((
            self.move_absolute,
            (x, y, z, sx, sy, sz)
        ))
    def enqueue_jog(self, axis, direction, is_on: bool):
        self.cmd_queue.put((
            self._jog,
            (axis, direction, is_on)
        ))



    # ================= LOW LEVEL =================
    def _write_reg(self, addr, value):
        if not self.modbus:
            return False, "Not connected"
        try:
            res = self.modbus.write_single_coil(1, addr, value)
            self.modbus._log(f"WRITE {addr} = {value}")
            return True, "OK"

        except Exception as e:
            self.modbus._log(f"Write error: {e}")
            return False, str(e)

    

