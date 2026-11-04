# debug.gdb - attach to QEMU's gdb stub, stop in the decision function, inspect state and peripheral registers.
#   terminal 1: qemu-system-arm -M lm3s6965evb -nographic -kernel thermostat.elf -s -S
#   terminal 2: gdb-multiarch -q -x debug.gdb thermostat.elf
target remote :1234
break fan_should_run
continue
info registers pc sp
print temp
print override_pressed
# Read the GPIO data register exactly as the firmware does (an MMIO read goes to QEMU's PL061 model)
print/x *(unsigned int *)0x400043FC
