# debug.gdb - debug the tiny kernel through QEMU's gdb stub.
#   terminal 1: make debug          (QEMU starts frozen at the first instruction: -S, gdb stub on :1234: -s)
#   terminal 2: gdb-multiarch -q -x debug.gdb kernel.elf
target remote :1234
info registers pc
break trap_handler
continue
# First trap: the ecall. Look at the CSRs the hardware filled in.
print/x $mcause
print/x $mepc
x/i $mepc
continue
# Second trap: the timer interrupt (top bit of mcause set, low bits = 7)
print/x $mcause
backtrace
