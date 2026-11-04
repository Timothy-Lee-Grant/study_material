2026_11_04_13_00-(Emulating-Microcontrollers-And-Devices)

# Lecture 002: Emulating Microcontrollers and External Devices: Running Real Firmware, Injecting Fake Inputs, Checking Outputs

> **For:** Timothy · **Date:** 2026-11-04
> **Prerequisites:** none required; this lecture stands on its own. You should know what memory-mapped registers, a UART and a GPIO pin are (you've written firmware that uses all three).
> **Why this lecture:** you want to know how a microcontroller system can be emulated, and especially how you can feed **fake inputs** (a sensor reading, a button press, a serial message) into the emulated system and **observe** what the firmware does. This lecture explains what is and isn't being emulated, then does it for real: an unmodified Cortex-M3 firmware image runs on QEMU, and a Python script plays the temperature sensor over the serial port and presses a button on a GPIO pin, checking the firmware's decisions after each input. It then shows Renode and Wokwi, tools built specifically for this, and how to choose between emulation, host-side unit tests and real hardware.
> **Companion:** `001-qemu_for_operating_systems.md` covers QEMU for kernels (boot, traps, gdb). Each lecture can be read alone.
> **Verification:** everything in §2–§5 was built and run on 2026-11-04 with QEMU 8.2.2, `arm-none-eabi-gcc` 13.2 and Python 3 on Linux. Code: `code/mcu/`. The Renode and Wokwi examples in §7–§8 use the tools' documented commands but weren't run here. No firmware analogies (the lecture *is* about firmware, so it teaches the mechanism directly).

---

## Core ideas (the answer key)

1. **Emulating a microcontroller means emulating three things:** the CPU core (it executes your firmware's instructions), the memory map (flash, RAM, and where each peripheral's registers are), and **models of the peripherals** (UART, GPIO, timers, I2C...).
2. **The firmware is the unmodified binary** you'd flash to the chip. It can't tell it's emulated, as long as every register it touches behaves like the real one.
3. **A peripheral model is a pair of callbacks on an address range:** when firmware reads a register, the model returns a value; when it writes one, the model updates its state. The model's **other side** connects to the outside world: a socket, a file, a test script.
4. **Fake inputs are injected on that other side.** Bytes into a UART model's receive side; a level onto a GPIO model's input pin; a value into a sensor model's property. The firmware sees them through its normal register reads.
5. **Outputs are observed the same way in reverse:** UART bytes come out of a socket, GPIO output pins can be watched, device-level events can be traced, and gdb can read any register or variable.
6. **QEMU supports a handful of real MCU boards** (Stellaris LM3S6965, STM32 boards, micro:bit, ARM MPS2), with partial peripheral coverage. Its injection tools are general-purpose: chardev sockets for serial, the **qtest** protocol for GPIO lines, gdb for memory and registers, tracing for device events.
7. **Renode** (Antmicro, MIT license) is built for exactly this job: many MCU platforms, models of real sensors with settable properties, buttons with `Press`/`Release`, virtual time, multi-node networks, and Robot Framework tests. **Wokwi** does the same for hobby boards (Arduino, ESP32, Raspberry Pi Pico) with virtual parts and YAML test scenarios.
8. **Emulation tests the firmware's logic and its use of registers, not electrical behavior or precise timing.** Peripheral models are simplified; timing isn't cycle-accurate; analog effects don't exist.
9. **Use three layers of testing:** host-side unit tests with a fake hardware layer (fastest, for logic), emulation (the real binary and real register usage, automated), and hardware-in-the-loop (real electrical behavior and timing).

---

## Table of Contents

- [0. The problem](#0-the-problem)
- [1. What gets emulated](#1-what-gets-emulated)
- [2. The firmware under test](#2-the-firmware-under-test)
- [3. The injection channels QEMU gives you](#3-the-injection-channels-qemu-gives-you)
- [4. The test harness and what it showed](#4-the-test-harness-and-what-it-showed)
- [5. Inside the GPIO model: what "injecting" actually does](#5-inside-the-gpio-model-what-injecting-actually-does)
- [6. Watching from the debugger](#6-watching-from-the-debugger)
- [7. Renode: a framework built for device emulation](#7-renode-a-framework-built-for-device-emulation)
- [8. Wokwi: virtual parts and scenario files](#8-wokwi-virtual-parts-and-scenario-files)
- [9. What emulation can't tell you, and how to choose](#9-what-emulation-cant-tell-you-and-how-to-choose)
- [Misconceptions](#misconceptions)
- [Self-check questions](#self-check-questions)
- [Sources](#sources)

---

## 0. The problem

**Test a thermostat firmware without the hardware.**

A Cortex-M3 microcontroller runs a thermostat:
- a temperature sensor sends readings as text lines (`temp=57`) over UART0;
- an "override" button is wired to GPIO port A, pin 0;
- the firmware turns a fan **on** when the temperature is **above 50** or the button is held, **off** otherwise, and logs every decision over UART0.

Write an automated test that runs the **real firmware binary**, feeds it a sequence of sensor readings and button presses, and checks after each input that the firmware made the right decision. No board, no sensor, no button.

---

## 1. What gets emulated

```
          ┌────────────── emulator (QEMU / Renode / Wokwi) ──────────────┐
          │                                                               │
 firmware │  CPU core model ── executes thermostat.elf, instruction by    │
 binary ──┼─►                  instruction                                │
          │       │ loads/stores to addresses                             │
          │       ▼                                                       │
          │  memory map:  0x00000000 flash   0x20000000 RAM               │
          │               0x40004000 GPIO A model ◄──── input pins ◄──────┼── test: "pin 0 = 1"
          │               0x4000C000 UART0 model  ◄──── RX bytes   ◄──────┼── test: "temp=57\n"
          │                                        ────► TX bytes  ───────┼─► test: reads "FAN ON"
          └───────────────────────────────────────────────────────────────┘
```

- **The CPU core model** executes Thumb-2 instructions exactly as the real Cortex-M3 would (QEMU translates them to host instructions; lecture 001 §1).
- **The memory map** matches the real chip: the firmware's linker script and register addresses are unchanged.
- **Each peripheral model** implements the registers software sees. When the firmware reads `UART0_FR` to check "receive FIFO empty?", the UART model answers from its own state. That state changes when bytes arrive on the model's **outside** connection.

This is the whole trick behind "fake inputs": **the firmware only ever sees registers, and the emulator decides what those registers contain.**

**QEMU's MCU boards** (from `qemu-system-arm -M help`, QEMU 8.2):

```
lm3s6965evb          Stellaris LM3S6965EVB (Cortex-M3)       ← this lecture
lm3s811evb           Stellaris LM3S811EVB (Cortex-M3)
microbit             BBC micro:bit (Cortex-M0)
mps2-an385           ARM MPS2 with AN385 FPGA image for Cortex-M3
netduino2            Netduino 2 Machine (Cortex-M3)
netduinoplus2        Netduino Plus 2 Machine (Cortex-M4)
olimex-stm32-h405    Olimex STM32-H405 (Cortex-M4)
stm32vldiscovery     ST STM32VLDISCOVERY (Cortex-M3)
```

Peripheral coverage is partial. On the LM3S6965 board, QEMU's device tree (`info qom-tree`) lists the GPIO ports, UARTs, timers, I2C, SPI, an OLED display and a "gamepad", and also several `unimplemented-device` entries: address ranges where QEMU only logs accesses. Firmware that depends on one of those won't work. That's the main limit of QEMU for MCUs, and the main reason Renode exists (§7).

---

## 2. The firmware under test

Files in `code/mcu/`: `startup.c` (vector table and reset handler), `link.ld` (flash at 0, RAM at 0x20000000), `main.c`, `Makefile`. It's bare-metal C, no libraries, no SDK. The register addresses are the chip's real ones.

```c
#define REG(addr)     (*(volatile uint32_t *)(addr))
#define UART0_DR      REG(0x4000C000)      /* data: write = transmit, read = next received byte */
#define UART0_FR      REG(0x4000C018)      /* flags: bit 4 RXFE = receive FIFO empty           */
#define UART_FR_RXFE  (1u << 4)
#define GPIOA_DATA    REG(0x400043FC)      /* all 8 pins of port A                              */
#define THRESHOLD 50

static int fan_should_run(int temp, int override_pressed)
{
    return override_pressed || temp > THRESHOLD;
}

int main(void)
{
    ...
    puts_("thermostat: boot\r\n");
    for (;;) {
        button = GPIOA_DATA & 1;                      /* 1. poll the button pin             */
        if (button != last_button) { ...log "button: pressed/released"... }

        if (rx_ready()) { ...collect a line; on "temp=N", parse and log "temp: N"... }   /* 2. sensor */

        int want = fan_should_run(temp, button);      /* 3. decide                          */
        if (want != fan) { fan = want; puts_(fan ? "FAN ON\r\n" : "FAN OFF\r\n"); }
    }
}
```

Build and run it by hand:

```
$ make
$ qemu-system-arm -M lm3s6965evb -nographic -kernel thermostat.elf
thermostat: boot
temp=57            ← you type this (the terminal is UART0)
temp: 57
FAN ON
```

(Ctrl-a x quits.) Typing into the terminal is already "injecting a fake input": your keystrokes go into the UART model's receive FIFO, and the firmware reads them through `UART0_DR`. The next step is to have a program do it.

**The `.elf` loads directly.** `-kernel thermostat.elf` makes QEMU load the ELF's segments into the emulated flash and RAM. The Cortex-M3 model then does what the real chip does at reset: read word 0 of flash as the initial stack pointer and word 1 as the reset handler address, and start executing.

---

## 3. The injection channels QEMU gives you

| What you want to fake or watch | QEMU mechanism | How |
|---|---|---|
| Serial data in and out (a sensor, a host PC, a modem) | **chardev** backend for the UART | `-serial tcp:127.0.0.1:5555,server=on,wait=on` (or `pty`, `file:`, `stdio`, `pipe:`) |
| A digital input pin (button, switch, "data ready" line) | **qtest** protocol: `set_irq_in` | `-qtest tcp:127.0.0.1:5556,server=on,wait=off`, then send `set_irq_in <device> <gpio-name> <n> <level>` |
| Watching an output pin (LED, relay) | **qtest**: `irq_intercept_out` | QEMU then sends `IRQ raise N` / `IRQ lower N` messages when the pin changes |
| Any register or memory value; stopping on events | **gdb stub** | `-s -S`, then gdb: `print`, `set var`, `x`, breakpoints, watchpoints |
| Device-level events (what the model saw) | **tracing** | `-trace pl061_input_change` (list them with `-trace help`) |
| Stopping, resetting, reading physical memory | **monitor / QMP** | `-monitor`, `-qmp`: `stop`, `cont`, `system_reset`, `xp` |
| Pass/fail result straight to the host | **semihosting** | `-semihosting`: firmware calls `SYS_EXIT` with a status code, QEMU exits with it (useful for unit tests that run *inside* the emulator) |

**qtest** is QEMU's own device-testing protocol: a line-based request/response channel. The commands used here (from QEMU's documentation):

```
> set_irq_in QOM-PATH NAME NUM LEVEL     force a GPIO-in pin of a device to a level      < OK
> irq_intercept_out QOM-PATH             report a device's GPIO-out pin changes          < OK
> readl ADDR  /  writel ADDR VALUE       read/write 32-bit guest memory                   < OK [VALUE]
```

**QOM-PATH** is the device's path in QEMU's object tree. You find it with the monitor:

```
(qemu) info qom-tree        → /machine/unattached/device[8] (pl061_luminary) ... device[14]
(qemu) info mtree           → 0x40004000-0x40004fff: pl061   (the first one = port A)
```

The seven `pl061_luminary` devices are GPIO ports A–G, created in order, so port A is `device[8]` in this QEMU version. Each has eight input lines named `unnamed-gpio-in[0..7]`. (These paths can change between QEMU versions; look them up again if a newer QEMU rejects them.)

---

## 4. The test harness and what it showed

`code/mcu/inject.py` starts QEMU with the UART on one TCP socket and qtest on another, then runs a script of inputs and expected outputs.

```python
class Board:
    def __init__(self, elf):
        self.qemu = subprocess.Popen([
            "qemu-system-arm", "-M", "lm3s6965evb", "-kernel", elf,
            "-display", "none", "-monitor", "none",
            "-serial", f"tcp:127.0.0.1:{UART_PORT},server=on,wait=on",   # QEMU waits for us before starting
            "-qtest", f"tcp:127.0.0.1:{QTEST_PORT},server=on,wait=off",
            "-qtest-log", "/dev/null",
        ])
        ...

    def sensor(self, temp):                       # fake sensor: a line into UART0's RX side
        self.uart.sendall(f"temp={temp}\n".encode())

    def button(self, pressed):                    # fake button: drive GPIO A pin 0
        self.qt_file.write(f"set_irq_in {GPIOA} unnamed-gpio-in 0 {1 if pressed else 0}\n")
        self.qt_file.flush()
        assert self.qt_file.readline().strip() == "OK"

    def expect(self, text, timeout=2.0):          # observe: wait until UART0's TX output contains text
        ...
```

The test sequence, one input and one expected reaction per step:

```python
steps = [
    ("sensor 20",          lambda: b.sensor(20),     "temp: 20"),
    ("sensor 57 (> 50)",   lambda: b.sensor(57),     "FAN ON"),
    ("sensor 45",          lambda: b.sensor(45),     "FAN OFF"),
    ("press button",       lambda: b.button(True),   "FAN ON"),
    ("sensor -5, held",    lambda: b.sensor(-5),     "temp: -5"),
    ("release button",     lambda: b.button(False),  "FAN OFF"),
]
```

Actual output, with device tracing on (`TRACE=1 python3 inject.py`, run 2026-11-04):

```
pl061_input_change /machine/unattached/device[12] input 0 changed to 1     ← at boot (see below)
pl061_input_change /machine/unattached/device[12] input 1 changed to 1
pl061_input_change /machine/unattached/device[12] input 2 changed to 1
pl061_input_change /machine/unattached/device[12] input 3 changed to 1
pl061_input_change /machine/unattached/device[13] input 1 changed to 1
PASS  sensor 20            -> saw 'temp: 20'
PASS  sensor 57 (> 50)     -> saw 'FAN ON'
PASS  sensor 45            -> saw 'FAN OFF'
pl061_input_change /machine/unattached/device[8] input 0 changed to 1      ← our button press
PASS  press button         -> saw 'FAN ON'
PASS  sensor -5, held      -> saw 'temp: -5'
pl061_input_change /machine/unattached/device[8] input 0 changed to 0      ← our release
PASS  release button       -> saw 'FAN OFF'
all checks passed
```

What each part shows:
- **The firmware never knew.** It polled `GPIOA_DATA` and `UART0_FR` exactly as it would on the board.
- **The trace lines are the GPIO model reporting its own input changes.** Ours appear on `device[8]` (port A) exactly when the harness sent `set_irq_in`. The five lines at boot are QEMU's model of the board's **gamepad**: its five buttons are wired to ports E and F (devices 12 and 13) and idle high, as real pulled-up buttons would. Tracing showed a detail of the board you'd otherwise have to read in a schematic.
- **"sensor -5, held"** checks a combination: the temperature is far below the threshold, but the button is still held, so the fan stays on (no `FAN OFF`).
- **The harness is a normal Python program.** It could just as well be a pytest suite, run in CI on every commit, with no hardware attached.

**Tests you'd add next** (edge cases from the specification, not from the code): exactly 50 (should be OFF: the rule says *above* 50), malformed lines (`temp=`, `tmp=60`, a very long line), a button bounce (press/release/press in quick succession), and readings arriving while the button is held.

---

## 5. Inside the GPIO model: what "injecting" actually does

QEMU's GPIO model for this chip is `hw/gpio/pl061.c` (the Stellaris GPIO is compatible with Arm's PL061). Two functions are enough to see the whole mechanism (QEMU 8.2.2 source, abridged):

```c
/* Called when something outside drives an input pin: here, qtest's set_irq_in. */
static void pl061_set_irq(void *opaque, int irq, int level)
{
    PL061State *s = (PL061State *)opaque;
    uint8_t mask = 1 << irq;
    if ((s->dir & mask) == 0) {          /* only pins configured as inputs follow the outside level */
        s->data &= ~mask;
        if (level)
            s->data |= mask;
        pl061_update(s);                 /* may raise the GPIO interrupt if it's enabled for this pin */
    }
}

/* Called when the firmware READS one of the device's registers. */
static uint64_t pl061_read(void *opaque, hwaddr offset, unsigned size)
{
    PL061State *s = (PL061State *)opaque;
    switch (offset) {
    case 0x0 ... 0x3ff:                  /* DATA: address bits [9:2] select which pins are returned */
        return s->data & (offset >> 2);
    case 0x400:                          /* DIR: direction register */
        return s->dir;
    ...
```

So the chain for one button press is:

```
inject.py: "set_irq_in .../device[8] unnamed-gpio-in 0 1"
   → qtest calls the device's input line 0           → pl061_set_irq(s, 0, 1)
   → s->data bit 0 = 1 (pin is an input)               → pl061_update: interrupt if enabled
firmware: ldr r3, [0x400043FC]                         → pl061_read(s, 0x3FC) → s->data & 0xFF → bit 0 set
   → "button: pressed", fan_should_run(...) = 1         → "FAN ON" written to UART0_DR
   → UART model's write callback → chardev → TCP socket → inject.py's expect("FAN ON")
```

Note the `(offset >> 2)` mask: the firmware reads at offset `0x3FC`, so `0x3FC >> 2 = 0xFF` returns all eight pins. That's a real feature of this GPIO block (address-masked access), and the model reproduces it because firmware depends on it.

**Adding a peripheral QEMU doesn't have** (say, an I2C temperature sensor) means writing a model like this one: a C file that registers a memory region (or an I2C bus device) with read/write callbacks, plus a way for the outside to set its state (a QOM property, a chardev, a QMP command). That's real work in QEMU, which is why tools with ready-made sensor models are attractive.

---

## 6. Watching from the debugger

The gdb stub gives you the other way to observe and inject: stop the CPU anywhere, look at variables and registers, change them.

```
terminal 1:  qemu-system-arm -M lm3s6965evb -nographic -kernel thermostat.elf -s -S
terminal 2:  gdb-multiarch -q -x debug.gdb thermostat.elf
```

`debug.gdb` and its actual output:

```
target remote :1234                       Reset_Handler () at startup.c:9      ← frozen at reset
break fan_should_run                      Breakpoint 1 at 0x218: file main.c, line 39.
continue                                  Breakpoint 1, fan_should_run (override_pressed=0, temp=0) at main.c:39
info registers pc sp                      pc 0x218 <main+348>    sp 0x2000ffa0  ← stack at the top of RAM
print temp                                $1 = 0
print override_pressed                    $2 = 0
print/x *(unsigned int *)0x400043FC       $3 = 0x0                              ← a REGISTER read, through gdb
```

The last line is worth a second look: gdb read the GPIO data register, and that read went through the same `pl061_read` callback as the firmware's reads. With the harness and gdb together you can stop the firmware right after an injected input and see exactly how it got there. (`pc` = `main+348` because the compiler inlined `fan_should_run` into `main`; gdb still knows the source line.)

gdb can inject too: `set var temp = 99` changes a variable; `set {unsigned int}0x20000100 = 5` writes RAM. That's useful for forcing a hard-to-reach state, but it bypasses the input path, so prefer injecting through the peripheral when you want to test the real path.

---

## 7. Renode: a framework built for device emulation

**Renode** is an open-source framework from Antmicro (MIT license) for running **unmodified firmware** on virtual boards and networks of boards. Compared with QEMU, it's designed around the problem in this lecture:

- **Platforms described in text files** (`.repl`): CPU, memory map, and which peripheral models sit where, so you can describe a custom board.
- **Many MCU families** (Cortex-M, RISC-V, and others) with models of their peripherals, plus **models of external parts**: sensors on I2C/SPI with properties you set, buttons, LEDs, radios.
- **Virtual time** that Renode controls, so a test can say "run for 10 ms of emulated time" regardless of the host's speed.
- **Multi-node**: several boards connected by emulated wired or wireless links.
- **Robot Framework integration** for automated tests, with keywords for UART, LEDs, buttons and logs.

**The same kind of test, in Renode's Robot Framework style.** These commands appear in Renode's own test suite (its nRF52840 platform tests):

```robot
*** Test Cases ***
Should Report Alarm When Button Is Pressed
    Execute Command           mach create
    Execute Command           machine LoadPlatformDescription @platforms/cpus/nrf52840.repl
    Execute Command           sysbus LoadELF @thermostat.elf
    Create Terminal Tester    sysbus.uart0
    Start Emulation

    Wait For Line On Uart     thermostat: boot
    Write Line To Uart        temp=57                          # fake sensor over the UART
    Wait For Line On Uart     FAN ON

    Execute Command           sysbus.gpio0.button Press        # fake button
    Execute Command           sysbus.gpio0.button Release

    Execute Command           sysbus.twi1.adxl372 AccelerationX 1    # set a modeled sensor's value
```

(Paths and peripheral names depend on the platform file; the thermostat firmware itself would need porting to that chip's registers. The point is the shape: load, start, inject, wait for output, all in emulated time.)

The key difference from §4: in Renode, `adxl372 AccelerationX 1` sets the value of a **modeled accelerometer**, and the firmware reads it through a **real I2C/SPI transaction** to that model, exactly as it would talk to the physical part. With QEMU you'd have to write that model yourself.

---

## 8. Wokwi: virtual parts and scenario files

**Wokwi** is a simulator for hobby and IoT boards (Arduino, ESP32, Raspberry Pi Pico, STM32) with a browser-based editor and a library of **virtual parts**: buttons, potentiometers, temperature and humidity sensors, displays. A `diagram.json` file describes the board and the wiring. The **Wokwi CLI** runs the same simulation headless for CI, driven by a YAML **automation scenario**:

```yaml
name: 'Thermostat test'
version: 1
steps:
  - wait-serial: 'thermostat: boot'
  - set-control:            # change a virtual part's input
      part-id: btn1
      name: pressed
      value: 1
  - delay: 500ms
  - expect-pin:             # check an output pin
      part-id: esp
      name: 2
      value: 1
  - wait-serial: 'FAN ON'
```

Step types include `delay`, `set-control` (press a button, set a sensor's humidity), `expect-pin`, `wait-serial`, `write-serial`, and `take-screenshot`. Run with `wokwi-cli . --scenario thermostat.test.yaml` (needs a Wokwi CI token). The documentation marks scenarios as alpha. Wokwi is a commercial service (CodeMagic Ltd.) with a free tier; check its terms for CI use.

---

## 9. What emulation can't tell you, and how to choose

**Emulation won't show you:**
- **Electrical behavior:** pull-up values, contact bounce shapes, noise, voltage levels, current draw.
- **Exact timing:** QEMU doesn't model clock cycles, bus wait states or peripheral latency. Code that works only because "the UART is slow enough" can pass in emulation and fail on the chip (and vice versa). Our UART model transmits instantly.
- **Peripheral quirks the model doesn't implement:** errata, undocumented behavior, anything in an `unimplemented-device` range.
- **Analog peripherals** beyond simple value injection (ADC noise, DAC settling).

**Three layers, each catching what the others miss:**

| Layer | What runs | Good for | Misses |
|---|---|---|---|
| **Host unit tests with a fake hardware layer** | your logic compiled for your PC; register access replaced by a fake (`hal_read_button()` returns what the test says) | decision logic, parsing, state machines; thousands of cases in milliseconds | the real binary, real register usage, the compiler for the target |
| **Emulation** (QEMU, Renode, Wokwi) | the **unmodified firmware binary** on a CPU + peripheral models | start-up code, interrupt setup, register-level driver code, end-to-end behavior, CI on every commit | electrical behavior, exact timing, unmodeled peripherals |
| **Hardware-in-the-loop** | the real board, with a test rig driving its pins (relays, a signal generator, a logic analyzer) | timing, electrical behavior, the real sensor | speed, cost, scale |

For this thermostat, a good split is: `fan_should_run` and the line parser in host unit tests (every edge case), the full binary in emulation (boot, UART and GPIO paths, the test sequence in §4), and a short hardware check on the real board before release.

**Choosing the emulator:**

| Need | Pick |
|---|---|
| Your board is one QEMU models, and UART/GPIO-level tests are enough | QEMU (§2–§6), already installed with most toolchains |
| Real sensor models over I2C/SPI, custom boards, virtual time, several connected devices | Renode |
| Arduino / ESP32 / Pico with standard parts, browser editing, quick CI scenarios | Wokwi |
| A peripheral nobody models | write a model (QEMU C device, Renode C#/Python peripheral), or move that test to hardware-in-the-loop |

---

## Misconceptions

| You might think | Reality |
|---|---|
| Emulating an MCU simulates the chip's circuits | It models the CPU's instructions and each peripheral's **register behavior**; no electrical simulation |
| You need a special build of the firmware for emulation | The same binary you'd flash; the emulator reproduces the memory map |
| Fake inputs are injected into the firmware's variables | They're injected into the **peripheral models**; the firmware reads them through its normal registers. (gdb can poke variables, but that skips the input path) |
| If it passes in QEMU, it works on the board | It proves logic and register usage; timing and electrical behavior need hardware |
| QEMU models every peripheral of a supported board | Coverage is partial; some ranges are `unimplemented-device` stubs that only log accesses |
| Emulator time is real time | QEMU's virtual clock follows the host loosely; Renode controls virtual time precisely; neither is cycle-accurate |

---

## Self-check questions

1. Name the three things an MCU emulator must provide for unmodified firmware to run.
<details><summary>Answer</summary>A CPU core model that executes the firmware's instructions, the chip's memory map (flash, RAM, peripheral addresses), and models of the peripherals the firmware uses, which implement their registers' behavior.</details>

2. What is a peripheral model, in terms of code? Where does a fake input enter it?
<details><summary>Answer</summary>Read and write callbacks on the peripheral's address range, plus internal state (for example the GPIO data and direction registers). A fake input enters on the model's outside connection: bytes into a UART model's receive side through its chardev, a level on a GPIO model's input line (qtest set_irq_in), a property of a sensor model. The firmware then sees it through a normal register read.</details>

3. Trace one injected button press from `inject.py` to the firmware's `FAN ON` line coming back to the script.
<details><summary>Answer</summary>inject.py sends `set_irq_in /machine/unattached/device[8] unnamed-gpio-in 0 1` on the qtest socket; QEMU drives input line 0 of the port A GPIO model; pl061_set_irq sets data bit 0 (the pin is an input). The firmware's next read of 0x400043FC calls pl061_read, which returns data & 0xFF with bit 0 set; the firmware logs "button: pressed", fan_should_run returns 1, it writes "FAN ON" to UART0_DR; the UART model's write callback passes the bytes to its TCP chardev; the script's expect("FAN ON") reads them.</details>

4. How did you find the QOM path `device[8]`, and why might it change?
<details><summary>Answer</summary>`info qom-tree` in the monitor lists seven pl061_luminary devices (device[8]..device[14]); `info mtree` shows the first pl061 at 0x40004000, port A's address; they're created in port order. The numbering depends on the order QEMU's board code creates devices, which can change between QEMU versions.</details>

5. The trace showed input changes on devices 12 and 13 at boot. What were they?
<details><summary>Answer</summary>QEMU's model of the board's gamepad: its five buttons are wired to GPIO ports E and F and idle high (pulled up), so the model drives those inputs to 1 at start-up.</details>

6. Why does `-serial tcp:...,server=on,wait=on` matter for the test?
<details><summary>Answer</summary>With wait=on, QEMU doesn't start the machine until the test script connects to the UART socket, so the boot message ("thermostat: boot") isn't sent before anyone is listening. With wait=off the first output was lost and the test failed.</details>

7. What can Renode do for a sensor test that QEMU can't do out of the box?
<details><summary>Answer</summary>Renode ships models of real external parts (for example an ADXL372 accelerometer on I2C/SPI) whose values a test sets with a command (`AccelerationX 1`); the firmware reads them through real bus transactions. It also controls virtual time precisely and has Robot Framework keywords for UART, buttons and LEDs. In QEMU you'd have to write the sensor model yourself.</details>

8. Give two kinds of bugs that pass in emulation but fail on hardware.
<details><summary>Answer</summary>Any two of: timing-dependent code (relying on a peripheral being slow, missing delays after enabling a clock, race conditions that depend on real interrupt latency); electrical issues (missing pull-ups, button bounce, noise); peripheral errata or registers the model doesn't implement; analog behavior of ADCs.</details>

9. For the thermostat, what would you test on the host, in emulation, and on hardware?
<details><summary>Answer</summary>Host: fan_should_run and the line parser with every edge case (exactly 50, negative, malformed input), using a fake hardware layer. Emulation: the real binary end to end (boot, UART and GPIO register paths, the input sequence). Hardware: a short check of the real button (bounce, pull-up), the real sensor link, and timing.</details>

---

## Sources

- QEMU documentation: [Arm system emulator (board list)](https://www.qemu.org/docs/master/system/target-arm.html), [Stellaris boards](https://www.qemu.org/docs/master/system/arm/stellaris.html), [QTest device emulation testing framework](https://www.qemu.org/docs/master/devel/testing/qtest.html) (`set_irq_in`, `irq_intercept_out`, `readl`/`writel`, `clock_step`), [Character devices](https://www.qemu.org/docs/master/system/invocation.html), [Tracing](https://www.qemu.org/docs/master/devel/tracing.html), [Semihosting](https://www.qemu.org/docs/master/about/emulation.html#semihosting). Checked 2026-11-04.
- QEMU source, [`hw/gpio/pl061.c` at v8.2.2](https://github.com/qemu/qemu/blob/v8.2.2/hw/gpio/pl061.c) (`pl061_set_irq`, `pl061_read`). Read 2026-11-04.
- Texas Instruments, *Stellaris LM3S6965 Microcontroller Data Sheet* (UART0 at 0x4000C000, GPIO port A at 0x40004000, address-masked GPIODATA).
- [renode/renode](https://github.com/renode/renode) README (Antmicro; MIT; architectures; multi-node; Robot Framework). [Renode testing API](https://renode.readthedocs.io/en/latest/basic/renode-testing-api.html). Renode test [`tests/platforms/NRF52840.robot`](https://opensecura.googlesource.com/3p/renode/renode/+/09e50cf0767f02988f26cbfd68d8ee03e1a0fdf5/tests/platforms/NRF52840.robot) (`sysbus.gpio0.button Press`, `adxl372 AccelerationX`, `Wait For Line On Uart`). Checked 2026-11-04.
- Wokwi docs, [Automation scenarios](https://docs.wokwi.com/wokwi-ci/automation-scenarios) (step types; alpha status; CI token). Checked 2026-11-04.
- Code: `code/mcu/` (QEMU 8.2.2, arm-none-eabi-gcc 13.2, Python 3), run 2026-11-04.
