/* main.c - a tiny "thermostat" firmware for QEMU's lm3s6965evb (lecture emulation/002).
 *
 * Inputs (all injectable from outside the emulator):
 *   - UART0 RX: lines like "temp=57\n" from a "sensor" (a test script on a TCP socket)
 *   - GPIO port A pin 0: an "override" button (driven by the qtest protocol)
 * Output:
 *   - UART0 TX: log lines and "FAN ON" / "FAN OFF" decisions
 *
 * Registers used (Stellaris LM3S6965 datasheet; QEMU models them as PL011 and PL061 blocks):
 *   UART0 base 0x4000C000: DR at +0x000 (data), FR at +0x018 (flags: bit 4 RXFE = RX FIFO empty)
 *   GPIOA base 0x40004000: DATA at +0x3FC (all 8 pins; the address bits [9:2] mask which pins)
 */
#include <stdint.h>

#define REG(addr)     (*(volatile uint32_t *)(addr))
#define UART0_DR      REG(0x4000C000)
#define UART0_FR      REG(0x4000C018)
#define UART_FR_RXFE  (1u << 4)
#define GPIOA_DATA    REG(0x400043FC)

#define THRESHOLD 50

static void putc_(char c) { UART0_DR = (uint32_t)c; }   /* QEMU's UART transmits instantly */
static void puts_(const char *s) { while (*s) putc_(*s++); }
static void putint(int v)
{
    char buf[12]; int i = 0;
    if (v < 0) { putc_('-'); v = -v; }
    do { buf[i++] = (char)('0' + v % 10); v /= 10; } while (v);
    while (i) putc_(buf[--i]);
}

static int  rx_ready(void) { return (UART0_FR & UART_FR_RXFE) == 0; }
static char rx_byte(void)  { return (char)(UART0_DR & 0xFF); }

/* The decision logic: the part you actually want to test. */
static int fan_should_run(int temp, int override_pressed)
{
    return override_pressed || temp > THRESHOLD;
}

int main(void)
{
    char line[32]; int len = 0;
    int temp = 0, fan = 0;
    int button = GPIOA_DATA & 1, last_button = button;

    puts_("thermostat: boot\r\n");
    for (;;) {
        /* 1. button input (GPIO) */
        button = GPIOA_DATA & 1;
        if (button != last_button) {
            puts_(button ? "button: pressed\r\n" : "button: released\r\n");
            last_button = button;
        }

        /* 2. sensor input (UART): collect a line, parse "temp=N" */
        if (rx_ready()) {
            char c = rx_byte();
            if (c == '\n' || c == '\r') {
                line[len] = 0;
                if (len > 5 && line[0] == 't' && line[4] == '=') {
                    int v = 0, i = 5, neg = 0;
                    if (line[i] == '-') { neg = 1; i++; }
                    for (; line[i] >= '0' && line[i] <= '9'; i++) v = v * 10 + (line[i] - '0');
                    temp = neg ? -v : v;
                    puts_("temp: "); putint(temp); puts_("\r\n");
                }
                len = 0;
            } else if (len < (int)sizeof line - 1) {
                line[len++] = c;
            }
        }

        /* 3. decide and report changes */
        int want = fan_should_run(temp, button);
        if (want != fan) {
            fan = want;
            puts_(fan ? "FAN ON\r\n" : "FAN OFF\r\n");
        }
    }
}
