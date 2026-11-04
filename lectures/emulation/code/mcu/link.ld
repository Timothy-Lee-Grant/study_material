/* lm3s6965: 256 KB flash at 0x00000000, 64 KB SRAM at 0x20000000 */
MEMORY { FLASH (rx) : ORIGIN = 0x00000000, LENGTH = 256K
         RAM  (rwx) : ORIGIN = 0x20000000, LENGTH = 64K }
_estack = ORIGIN(RAM) + LENGTH(RAM);
SECTIONS {
  .text : { KEEP(*(.isr_vector)) *(.text*) *(.rodata*) } > FLASH
  _sidata = LOADADDR(.data);
  .data : { _sdata = .; *(.data*) _edata = .; } > RAM AT > FLASH
  .bss  : { _sbss = .; *(.bss*) *(COMMON) _ebss = .; } > RAM
}
