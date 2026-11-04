/* startup.c - minimal Cortex-M3 start-up for QEMU's lm3s6965evb (lecture emulation/002).
 * The CPU reads word 0 of flash as the initial stack pointer and word 1 as the reset handler. */
#include <stdint.h>

extern uint32_t _estack, _sidata, _sdata, _edata, _sbss, _ebss;
int main(void);

void Reset_Handler(void)
{
    uint32_t *src = &_sidata, *dst = &_sdata;
    while (dst < &_edata) *dst++ = *src++;          /* copy initialized data from flash to RAM */
    for (dst = &_sbss; dst < &_ebss; ) *dst++ = 0;  /* zero .bss */
    main();
    for (;;) { }
}

static void Default_Handler(void) { for (;;) { } }

__attribute__((section(".isr_vector"), used))
const void *vector_table[16] = {
    &_estack,          /* 0: initial stack pointer */
    Reset_Handler,     /* 1: reset */
    Default_Handler,   /* 2: NMI */
    Default_Handler,   /* 3: HardFault */
};
