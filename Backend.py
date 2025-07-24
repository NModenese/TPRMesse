import math
import threading
import time
from typing import Callable

from MagneticSpringSensor import MagneticSpringSensor


class DummyPowerSupply:
    def __init__(self):
        self.current = 0.0
        self.output_on = False

    def setCurrent(self, value: float):
        self.current = value

    def setOutput(self, state: bool):
        self.output_on = bool(state)

    def readCurrent(self) -> float:
        return self.current if self.output_on else 0.0


class DummyElevator:
    def __init__(self):
        self.position = 0.0
        self.running = False

    def startMovement(self):
        self.running = True

    def stopMovement(self):
        self.running = False

    def resetPosition(self):
        self.position = 0.0
        self.running = False

    def update(self):
        if self.running:
            self.position += 0.01  # Simuliere konstantes Anfahren


class DummySpring:
    def __init__(self, elevator: DummyElevator):
        self.elevator = elevator
        self.contact_offset = 0.2  # Ab dieser Höhe beginnt Kontakt

    def getCompression(self) -> float:
        return max(0.0, self.elevator.position - self.contact_offset)


class DummyVoltmeter:
    def __init__(self, elevator: DummyElevator, spring: MagneticSpringSensor):
        self.elevator = elevator
        self.spring = spring

    def measVoltage(self) -> float:
        compression = self.spring.getCompression()
        if compression > 0:
            return 1.5 * (1 - math.exp(-3 * compression))  # Exponentiell ansteigende Spannung
        return 0.0


def calculate_surface_resistance(voltage: float, current: float, area_cm2: float = 5.0) -> float:
    if current <= 0:
        return float('nan')
    resistance = voltage / current
    return resistance * area_cm2 * 1000  # in mΩ·cm²


class MeasurementBackend:
    def __init__(self):
        self.dps = DummyPowerSupply()
        self.elevator = DummyElevator()
        # self.spring = DummySpring(self.elevator)
        self.spring = MagneticSpringSensor()
        self.voltmeter = DummyVoltmeter(self.elevator, self.spring)
        self.running = False
        self.stop_flag = threading.Event()
        self.thread = None

    def start_measurement(self, callback: Callable[[dict], None], on_done: Callable[[], None] = lambda: None):
        if self.running:
            return  # Messung läuft bereits

        def run():
            self.running = True
            self.stop_flag.clear()

            self.dps.setCurrent(1.0)
            self.dps.setOutput(True)
            self.elevator.resetPosition()
            self.elevator.startMovement()

            while not self.stop_flag.is_set():
                self.elevator.update()
                compression = self.spring.getCompression()
                voltage = self.voltmeter.measVoltage()
                current = self.dps.readCurrent()
                resistance = calculate_surface_resistance(voltage, current)

                # Live-Rückgabe an GUI
                callback({
                    "elevator"   : round(self.elevator.position, 3),
                    "compression": round(compression, 3),
                    "voltage"    : round(voltage, 3),
                    "current"    : round(current, 3),
                    "resistance" : round(resistance, 2) if not math.isnan(resistance) else None
                })

                if compression >= 0.5:
                    self.elevator.stopMovement()
                    break

                time.sleep(0.05)

            if not self.stop_flag.is_set():
                time.sleep(1.0)  # 1 Sekunde warten für finale Messung
                voltage = self.voltmeter.measVoltage()
                current = self.dps.readCurrent()
                resistance = calculate_surface_resistance(voltage, current)
                callback({
                    "final"     : True,
                    "voltage"   : round(voltage, 3),
                    "current"   : round(current, 3),
                    "resistance": round(resistance, 2) if not math.isnan(resistance) else None
                })

            # Rückfahren
            self.dps.setOutput(False)
            self.elevator.startMovement()
            while self.elevator.position > 0:
                if self.stop_flag.is_set():
                    break
                self.elevator.position -= 0.02  # Rückwärts schneller
                if self.elevator.position < 0:
                    self.elevator.position = 0.0
                callback({"elevator": round(self.elevator.position, 3)})
                time.sleep(0.05)
            self.elevator.stopMovement()

            self.running = False
            on_done()

        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_flag.set()

    def is_running(self):
        return self.running

    def shutdown(self):
        if self.spring:
            self.spring.disconnect()
