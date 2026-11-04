CC = arm-none-eabi-gcc
CFLAGS = -mcpu=cortex-m3 -mthumb -O1 -g -ffreestanding -nostdlib -Wall -Wextra
thermostat.elf: startup.c main.c link.ld
	$(CC) $(CFLAGS) -T link.ld startup.c main.c -o $@
run: thermostat.elf
	qemu-system-arm -M lm3s6965evb -nographic -kernel thermostat.elf
clean:
	rm -f thermostat.elf
