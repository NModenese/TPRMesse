import json
import re

import serial
from serial.tools import list_ports


class MagneticSpringSensor:
    STRUCTURE_REGEX = re.compile(r'^\{"raw":.*?,"dst":.*?,"ocf":.*?,"cof":.*?,"lin":.*?\}$')

    def __init__(self, port=None, baudrate=115200, spring_constant=50.0):
        self.baudrate = baudrate
        self.spring_constant = spring_constant
        self.ser = None
        self.buffer = ""
        self.latest_displacement = None

        self.port = port or self.auto_detect_port()
        self.connect()

    @staticmethod
    def auto_detect_port():
        ports = list_ports.comports()
        for p in ports:
            # Du kannst hier nach Beschreibung filtern, z. B.:
            if "USB" in p.description or "CH340" in p.description or "Serial" in p.description:
                print(f"[Sensor] Auto-detected port: {p.device} ({p.description})")
                return p.device
        raise RuntimeError("Kein geeigneter COM-Port gefunden.")

    def compute_crc16(self, data: str) -> int:
        crc = 0xFFFF
        for ch in data:
            crc ^= ord(ch) << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = ((crc << 1) ^ 0x8005) & 0xFFFF
                else:
                    crc = (crc << 1) & 0xFFFF
        return crc

    def verify_checksum(self, line: str) -> (bool, str):
        if "*" not in line:
            return False, None
        payload, chk = line.rsplit("*", 1)
        try:
            transmitted = int(chk, 16)
        except ValueError:
            return False, None
        computed = self.compute_crc16(payload)
        return transmitted == computed, payload

    def connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
            print(f"[Sensor] Connected to {self.port}")
        except Exception as e:
            print(f"[Sensor] Connection failed: {e}")
            self.ser = None

    def disconnect(self):
        if self.ser:
            self.ser.close()
            self.ser = None

    def _read_new_value(self):
        if not self.ser or not self.ser.in_waiting:
            return

        raw = self.ser.read(self.ser.in_waiting).decode('utf-8', errors='replace')
        self.buffer += raw

        while '\n' in self.buffer:
            line, self.buffer = self.buffer.split('\n', 1)
            line = line.strip()
            if not line:
                continue

            valid, payload = self.verify_checksum(line)
            if not valid or not self.STRUCTURE_REGEX.match(payload):
                continue

            try:
                data = json.loads(payload)
                self.latest_displacement = data["dst"]
            except json.JSONDecodeError:
                continue

    def getCompression(self):
        self._read_new_value()
        return self.latest_displacement
