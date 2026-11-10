"""
014_fifo_sizing.py - lecture 014: will a 64-entry device FIFO overflow?

Model (time in microseconds):
  - The device writes one byte every `t_in` us during a burst of `burst` bytes.
  - The "not empty" line asserts when the first byte lands. The host starts reading
    `latency` us later (interrupt latency + time until the reading thread runs).
  - Once started, the host removes one byte every `t_out` us while the FIFO is non-empty.
Peak occupancy is what must fit in the FIFO.
"""


def peak_occupancy(burst, t_in, t_out, latency):
    arrivals = [i * t_in for i in range(burst)]       # when each byte lands
    occupancy = peak = 0
    next_read = latency                                # host's first read time
    a = 0
    while a < len(arrivals) or occupancy > 0:
        next_arrival = arrivals[a] if a < len(arrivals) else float("inf")
        if next_arrival <= next_read or occupancy == 0:
            occupancy += 1
            a += 1
            peak = max(peak, occupancy)
            if occupancy == 1 and next_read < next_arrival:
                next_read = next_arrival               # host idle: reads as soon as data exists
        else:
            occupancy -= 1
            next_read += t_out
    return peak


def closed_form(burst, t_in, t_out, latency):
    """Bytes that arrive before the first read, then net growth while draining (if any)."""
    before = min(burst, latency // t_in + 1)
    if t_out <= t_in:                 # host at least as fast as device: backlog only shrinks
        return before
    rest = burst - before             # host slower: backlog keeps growing during the burst
    return before + rest - int(rest * t_in / t_out)


if __name__ == "__main__":
    print(f"{'burst':>6} {'t_in':>5} {'t_out':>6} {'latency':>8} {'peak':>5} {'formula':>8}  fits in 64?")
    cases = [
        (200, 10, 2,   100),     # fast host, short latency
        (200, 10, 2,   600),     # same host, a scheduling delay of 0.6 ms
        (200, 10, 2,  1000),     # 1 ms delay: overflow even though the host is 5x faster
        (200, 10, 12,  100),     # host slower than device: backlog grows across the burst
        (40,  10, 12, 2000),     # short burst: a long delay is fine if the burst fits
    ]
    for c in cases:
        p, f = peak_occupancy(*c), closed_form(*c)
        print(f"{c[0]:>6} {c[1]:>5} {c[2]:>6} {c[3]:>8} {p:>5} {f:>8}  {'yes' if p <= 64 else 'NO - overflow'}")
