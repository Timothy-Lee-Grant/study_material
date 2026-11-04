# entry.S - first instructions of a tiny RISC-V kernel on QEMU's "virt" machine (lecture emulation/001).
# With -bios none, QEMU's reset code jumps to 0x80000000 in machine mode (M-mode), hart 0 and others alike.
    .section .text.entry
    .globl _start
_start:
    csrr  t0, mhartid          # which CPU core ("hart") am I?
    bnez  t0, park             # only hart 0 runs the kernel; others sleep forever
    la    sp, stack_top        # give hart 0 a stack
    call  kmain
park:
    wfi
    j     park

# Trap entry: the CPU jumps here (mtvec) on any interrupt or exception.
# Hardware has already saved: mepc (where we were), mcause (why), and switched to the trap handler.
# Software must save the registers the C handler may clobber, then restore them and mret.
    .globl trap_entry
    .align 4
trap_entry:
    addi  sp, sp, -128
    sd    ra,  0(sp);  sd t0,  8(sp);  sd t1, 16(sp);  sd t2, 24(sp)
    sd    a0, 32(sp);  sd a1, 40(sp);  sd a2, 48(sp);  sd a3, 56(sp)
    sd    a4, 64(sp);  sd a5, 72(sp);  sd a6, 80(sp);  sd a7, 88(sp)
    sd    t3, 96(sp);  sd t4,104(sp);  sd t5,112(sp);  sd t6,120(sp)
    call  trap_handler
    ld    ra,  0(sp);  ld t0,  8(sp);  ld t1, 16(sp);  ld t2, 24(sp)
    ld    a0, 32(sp);  ld a1, 40(sp);  ld a2, 48(sp);  ld a3, 56(sp)
    ld    a4, 64(sp);  ld a5, 72(sp);  ld a6, 80(sp);  ld a7, 88(sp)
    ld    t3, 96(sp);  ld t4,104(sp);  ld t5,112(sp);  ld t6,120(sp)
    addi  sp, sp, 128
    mret                       # return to mepc, restoring the previous interrupt-enable state

    .section .bss
    .align 4
    .space 4096
stack_top:
