import serial
import threading
import time
from collections import deque
import queue

class ModbusRTUService:
    def __init__(self, port, baudrate=115200, timeout=0.05):
        self.ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=8,
            parity='N',
            stopbits=1,
            timeout=timeout
        )
        self.lock = threading.Lock()
        self.command_log: deque[str] = deque(maxlen=200)
        self.log_queue = queue.Queue(maxsize=1000)
    # ================= CRC16 =================
    def crc16(self, data: bytes):
        crc = 0xFFFF
        for pos in data:
            crc ^= pos
            for _ in range(8):
                if crc & 1:
                    crc >>= 1
                    crc ^= 0xA001
                else:
                    crc >>= 1
        return crc
    #================VALID_CRC========================
    def validate_crc(self, response):
        if len(response) < 3:
            return False
        data = response[:-2]
        crc_received = response[-2] | (response[-1] << 8)
        crc_calc = self.crc16(data)
        return crc_received == crc_calc
    # ================= Build frame =================
    def build_frame(self, slave_id, function_code, payload: bytes):
        frame = bytes([slave_id, function_code]) + payload
        crc = self.crc16(frame)
        return frame + bytes([crc & 0xFF, (crc >> 8) & 0xFF])

    # ================= Send =================
    def send_request(self, frame: bytes):
        with self.lock:
            self.ser.reset_input_buffer()

            self._log(f"TX: {frame.hex(' ')}")
            self.ser.write(frame)

            # đọc header
            header = self.ser.read(3)
            if len(header) < 3:
                self._log("RX timeout (header)")
                return b''

            byte_count = header[2]

            # đọc data + CRC
            body = self.ser.read(byte_count + 2)

            response = header + body

            self._log(f"RX: {response.hex(' ')}")
            return response
    #===============CHECK=========================
    def check_exception(self, response):
        if len(response) >= 3:
            func = response[1]
            if func & 0x80:
                error_code = response[2]
                raise Exception(f"Modbus Exception: {error_code}")
    # ================= PARSE =================
    def _parse_registers(self, response):
        if len(response) < 5:
            return None
        byte_count = response[2]
        data = response[3:3 + byte_count]
        values = []
        for i in range(0, len(data), 2):
            val = (data[i] << 8) | data[i + 1]
            values.append(val)
        return values

    def _parse_bits(self, response, quantity):
        if len(response) < 5:
            return None
        byte_count = response[2]
        data = response[3:3 + byte_count]

        bits = []
        for byte in data:
            for i in range(8):
                bits.append((byte >> i) & 1)

        return bits[:quantity]

    # ================= 0x01 =================
    def read_coils(self, slave_id, start_addr, quantity):
        payload = bytes([
            start_addr >> 8, start_addr & 0xFF,
            quantity >> 8, quantity & 0xFF
        ])
        frame = self.build_frame(slave_id, 0x01, payload)
        res = self.send_request(frame)
        return self._parse_bits(res, quantity)

    # ================= 0x02 =================
    def read_discrete_inputs(self, slave_id, start_addr, quantity):
        payload = bytes([
            start_addr >> 8, start_addr & 0xFF,
            quantity >> 8, quantity & 0xFF
        ])
        frame = self.build_frame(slave_id, 0x02, payload)
        res = self.send_request(frame)
        return self._parse_bits(res, quantity)

    # ================= 0x03 =================
    def read_holding_registers(self, slave_id, start_addr, quantity):
        payload = bytes([
            start_addr >> 8, start_addr & 0xFF,
            quantity >> 8, quantity & 0xFF
        ])
        frame = self.build_frame(slave_id, 0x03, payload)
        res = self.send_request(frame)
        return self._parse_registers(res)

    # ================= 0x04 =================
    def read_input_registers(self, slave_id, start_addr, quantity):
        payload = bytes([
            start_addr >> 8, start_addr & 0xFF,
            quantity >> 8, quantity & 0xFF
        ])
        frame = self.build_frame(slave_id, 0x04, payload)
        res = self.send_request(frame)
        return self._parse_registers(res)

    # ================= 0x05 =================
    def write_single_coil(self, slave_id, addr, value: bool):
        val = 0xFF00 if value else 0x0000
        payload = bytes([
            addr >> 8, addr & 0xFF,
            val >> 8, val & 0xFF
        ])
        frame = self.build_frame(slave_id, 0x05, payload)
        return self.send_request(frame)

    # ================= 0x06 =================
    def write_single_register(self, slave_id, addr, value):
        payload = bytes([
            addr >> 8, addr & 0xFF,
            value >> 8, value & 0xFF
        ])
        frame = self.build_frame(slave_id, 0x06, payload)
        return self.send_request(frame)

    # ================= 0x0F =================
    def write_multiple_coils(self, slave_id, start_addr, values: list[int]):
        quantity = len(values)
        byte_count = (quantity + 7) // 8

        data_bytes = bytearray(byte_count)
        for i, val in enumerate(values):
            if val:
                data_bytes[i // 8] |= (1 << (i % 8))

        payload = bytes([
            start_addr >> 8, start_addr & 0xFF,
            quantity >> 8, quantity & 0xFF,
            byte_count
        ]) + data_bytes

        frame = self.build_frame(slave_id, 0x0F, payload)
        return self.send_request(frame)

    # ================= 0x10 =================
    def write_multiple_registers(self, slave_id, start_addr, values: list[int]):
        quantity = len(values)
        byte_count = quantity * 2

        data_bytes = bytearray()
        for val in values:
            data_bytes += bytes([val >> 8, val & 0xFF])

        payload = bytes([
            start_addr >> 8, start_addr & 0xFF,
            quantity >> 8, quantity & 0xFF,
            byte_count
        ]) + data_bytes

        frame = self.build_frame(slave_id, 0x10, payload)
        respone = self.send_request(frame)
        return self.check_exception(respone)
    
    # ================= LOG =================
    def get_recent_log(self) -> list[str]:
        return list(self.command_log)
    def _log(self, msg):
        timestamp = time.strftime("%H:%M:%S")
        line = f"[{timestamp}] {msg}"
        self.command_log.append(line)
        try:
            self.log_queue.put_nowait(line)
        except queue.Full:
            pass

    def get_log(self):
        return list(self.command_log)

    def close(self):
        self.ser.close()