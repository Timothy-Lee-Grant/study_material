"""
inject.py - drive the thermostat firmware in QEMU with fake inputs and check its outputs
(lecture emulation/002).

  UART0  <-> TCP socket  : we play the temperature sensor and read the log
  qtest  <-> TCP socket  : we flip GPIO port A pin 0 (the "override button")

Run:  make && python3 inject.py          (TRACE=1 python3 inject.py also logs the GPIO model's events)
"""
import socket
import subprocess
import os
import time

UART_PORT, QTEST_PORT = 5555, 5556
# QOM path of GPIO port A. `info qom-tree` lists seven pl061_luminary devices, device[8]..device[14];
# they are created in port order A..G, and `info mtree` confirms the first sits at 0x40004000 (port A).
GPIOA = "/machine/unattached/device[8]"


def connect(port):
    for _ in range(50):
        try:
            return socket.create_connection(("127.0.0.1", port))
        except OSError:
            time.sleep(0.1)
    raise RuntimeError(f"could not connect to port {port}")


class Board:
    def __init__(self, elf):
        self.qemu = subprocess.Popen([
            "qemu-system-arm", "-M", "lm3s6965evb", "-kernel", elf,
            "-display", "none", "-monitor", "none",
            "-serial", f"tcp:127.0.0.1:{UART_PORT},server=on,wait=on",
            "-qtest", f"tcp:127.0.0.1:{QTEST_PORT},server=on,wait=off",
            "-qtest-log", "/dev/null",           # qtest otherwise echoes every command to stderr
        ] + (["-trace", "pl061_input_change"] if os.environ.get("TRACE") else []))   # device-level log
        self.uart = connect(UART_PORT)
        self.uart.settimeout(0.2)
        self.qt = connect(QTEST_PORT)
        self.qt_file = self.qt.makefile("rw")
        self.log = ""

    # ---- inputs
    def sensor(self, temp):
        self.uart.sendall(f"temp={temp}\n".encode())

    def button(self, pressed):
        # qtest command: set_irq_in <QOM path> <gpio-in name> <line> <level>
        self.qt_file.write(f"set_irq_in {GPIOA} unnamed-gpio-in 0 {1 if pressed else 0}\n")
        self.qt_file.flush()
        reply = self.qt_file.readline().strip()
        assert reply == "OK", reply

    # ---- outputs
    def expect(self, text, timeout=2.0):
        end = time.time() + timeout
        while text not in self.log:
            if time.time() > end:
                raise AssertionError(f"expected {text!r}; log so far:\n{self.log}")
            try:
                self.log += self.uart.recv(4096).decode(errors="replace")
            except socket.timeout:
                pass
        idx = self.log.index(text) + len(text)
        self.log = self.log[idx:]           # consume up to the match

    def close(self):
        self.qemu.kill()
        self.qemu.wait()


if __name__ == "__main__":
    b = Board("thermostat.elf")
    try:
        b.expect("thermostat: boot")
        steps = [
            ("sensor 20",          lambda: b.sensor(20),     "temp: 20"),
            ("sensor 57 (> 50)",   lambda: b.sensor(57),     "FAN ON"),
            ("sensor 45",          lambda: b.sensor(45),     "FAN OFF"),
            ("press button",       lambda: b.button(True),   "FAN ON"),
            ("sensor -5, held",    lambda: b.sensor(-5),     "temp: -5"),
            ("release button",     lambda: b.button(False),  "FAN OFF"),
        ]
        for name, action, want in steps:
            action()
            b.expect(want)
            print(f"PASS  {name:20s} -> saw {want!r}")
        print("all checks passed")
    finally:
        b.close()
