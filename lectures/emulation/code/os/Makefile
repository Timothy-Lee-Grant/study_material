CC = riscv64-unknown-elf-gcc
CFLAGS = -march=rv64imac_zicsr -mabi=lp64 -mcmodel=medany -O1 -g -ffreestanding -nostdlib -Wall -Wextra -Wl,--no-warn-rwx-segments
QEMU = qemu-system-riscv64 -M virt -bios none -nographic -kernel kernel.elf
kernel.elf: entry.S kernel.c link.ld
	$(CC) $(CFLAGS) -T link.ld entry.S kernel.c -o $@
run: kernel.elf
	$(QEMU)
debug: kernel.elf          # then, in another terminal: gdb-multiarch -x debug.gdb kernel.elf
	$(QEMU) -s -S
clean:
	rm -f kernel.elf
