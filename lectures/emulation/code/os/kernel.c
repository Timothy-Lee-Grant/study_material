/* kernel.c - a tiny RISC-V "kernel" for QEMU virt: UART output, a system-call trap, timer interrupts.
 * Lecture emulation/001.  Devices (from QEMU's virt machine memory map):
 *   0x10000000  NS16550A UART  (THR = transmit register at +0, LSR = line status at +5)
 *   0x02000000  CLINT          (mtimecmp for hart 0 at +0x4000, mtime at +0xBFF8; 10 MHz)
 *   0x00100000  test finisher  ("sifive_test": writing 0x5555 powers the machine off, so QEMU exits)
 */
#include <stdint.h>

#define UART       ((volatile uint8_t *)0x10000000)
#define MTIMECMP   (*(volatile uint64_t *)0x02004000)
#define MTIME      (*(volatile uint64_t *)0x0200BFF8)
#define POWEROFF   (*(volatile uint32_t *)0x00100000)
#define TICK       5000000ull          /* 0.5 s at the virt CLINT's 10 MHz timebase */

static void putc_(char c) { while ((UART[5] & 0x20) == 0) { } UART[0] = (uint8_t)c; }
static void puts_(const char *s) { while (*s) putc_(*s++); }
static void puthex(uint64_t v) { puts_("0x"); for (int i = 60; i >= 0; i -= 4) putc_("0123456789abcdef"[(v >> i) & 0xF]); }

#define csr_read(r)     ({ uint64_t v; __asm__ volatile("csrr %0, " #r : "=r"(v)); v; })
#define csr_write(r, v) __asm__ volatile("csrw " #r ", %0" :: "r"(v))
#define csr_set(r, v)   __asm__ volatile("csrs " #r ", %0" :: "r"(v))
#define csr_clear(r, v) __asm__ volatile("csrc " #r ", %0" :: "r"(v))

extern void trap_entry(void);
static volatile int ticks;

void trap_handler(void)
{
    uint64_t cause = csr_read(mcause), epc = csr_read(mepc);
    if (cause >> 63) {                              /* top bit set: an interrupt */
        if ((cause & 0xff) == 7) {                  /* 7 = machine timer interrupt */
            ticks++;
            puts_("  [trap] timer interrupt, tick "); putc_((char)('0' + ticks)); puts_("\n");
            MTIMECMP = MTIME + TICK;                /* schedule the next one (this also clears it) */
        }
    } else if (cause == 11) {                       /* 11 = ecall from M-mode: a "system call" */
        puts_("  [trap] ecall (call number in a7), mepc = "); puthex(epc); puts_("\n");
        csr_write(mepc, epc + 4);                   /* resume AFTER the ecall instruction */
    } else {
        puts_("  [trap] unexpected exception, mcause = "); puthex(cause); puts_("\n");
        for (;;) { }
    }
}

void kmain(void)
{
    puts_("tiny kernel: hello from M-mode on QEMU virt\n");
    csr_write(mtvec, (uint64_t)trap_entry);         /* where traps go: like loading an IDT / VBAR */

    puts_("making a system call (ecall)...\n");
    __asm__ volatile("li a7, 64; ecall" ::: "a7");  /* the trap handler runs, then we continue here */
    puts_("back from the system call\n");

    MTIMECMP = MTIME + TICK;
    csr_set(mie, 1u << 7);                          /* enable the machine timer interrupt source */
    csr_set(mstatus, 1u << 3);                      /* global interrupt enable (MIE) */
    while (ticks < 3)
        __asm__ volatile("wfi");                    /* sleep until an interrupt */
    csr_clear(mie, 1u << 7);                        /* stop the timer interrupts */
    puts_("3 ticks done; powering off\n");
    POWEROFF = 0x5555;                              /* QEMU exits with status 0 */
    for (;;) __asm__ volatile("wfi");
}
