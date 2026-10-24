"""Phase 1: scan the 1-Wire bus and print temperature. Run:
uvx mpremote cp firmware/pins.py :pins.py   (once, deploy.ps1 does it)
uvx mpremote run tools/bench/ds18b20_scan.py
Expect exactly one device and a plausible room temperature. Ctrl-C to stop."""
import time
import onewire
import ds18x20
from machine import Pin
import pins

ds = ds18x20.DS18X20(onewire.OneWire(Pin(pins.ONEWIRE)))
roms = ds.scan()
print("devices:", [bytes(r).hex() for r in roms])
if len(roms) != 1:
    raise SystemExit("FAIL: expected exactly 1 device (check wiring and 4.7k pull-up)")

errors = 0
try:
    while True:
        try:
            ds.convert_temp()
            time.sleep_ms(750)
            t = ds.read_temp(roms[0])
            flag = "  <-- SUSPECT" if t in (85.0, -127.0) else ""
            print("%.2f C%s" % (t, flag))
        except Exception as e:
            errors += 1
            print("read error:", e, "(total %d)" % errors)
        time.sleep(1)
except KeyboardInterrupt:
    print("errors:", errors)
