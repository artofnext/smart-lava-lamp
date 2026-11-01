import time
import asyncio
from machine import Pin
import onewire
import ds18x20

class Sensor:
    def __init__(self, pin_num):
        self.pin = Pin(pin_num)
        self.ow = onewire.OneWire(self.pin)
        self.ds = ds18x20.DS18X20(self.ow)
        self.rom = None
        self.last_temp = None
        self.last_valid_time = None
        self.scan()

    def scan(self):
        try:
            roms = self.ds.scan()
            if roms:
                self.rom = roms[0]
                return True
        except Exception:
            pass
        self.rom = None
        return False

    async def read(self):
        """Asynchronously trigger conversion, wait 750ms without blocking, and read."""
        if not self.rom:
            if not self.scan():
                return None
        try:
            self.ds.convert_temp()
        except Exception:
            self.rom = None
            return None

        await asyncio.sleep_ms(750)

        try:
            t = self.ds.read_temp(self.rom)
            # DS18B20 power-on reset is 85.0C before 1st conversion; -127.0C is bus disconnect
            if (t == 85.0 and self.last_temp is None) or t == -127.0 or t < -20.0 or t > 125.0:
                return None
            self.last_temp = round(t, 2)
            self.last_valid_time = time.time()
            return self.last_temp
        except Exception:
            self.rom = None
            return None

