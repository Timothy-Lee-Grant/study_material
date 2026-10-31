"""
015_parallel_compress.py - lecture 015: one core vs all cores, and Amdahl's law.

Compresses the same data two ways:
  1. one zlib stream on one core (the whole input is one dependency chain)
  2. split into independent chunks, each compressed on its own worker process
Then compares the measured speedup with Amdahl's prediction.
Run:  python3 015_parallel_compress.py
"""
import os
import time
import zlib
import random
from concurrent.futures import ProcessPoolExecutor

CHUNK = 1 << 20  # 1 MiB per independent chunk


def make_data(mb=48):
    random.seed(1)
    words = [bytes(random.choice(b"abcdefghijklmnop") for _ in range(random.randint(3, 9)))
             for _ in range(5000)]
    out, size = [], 0
    while size < mb << 20:
        w = random.choice(words) + b" "
        out.append(w); size += len(w)
    return b"".join(out)


def compress_chunk(chunk):
    return zlib.compress(chunk, 6)


def amdahl(p, n):
    """Speedup with n cores when a fraction p of the work can run in parallel."""
    return 1 / ((1 - p) + p / n)


if __name__ == "__main__":
    cores = os.cpu_count()
    data = make_data()
    chunks = [data[i:i + CHUNK] for i in range(0, len(data), CHUNK)]

    t0 = time.perf_counter()
    one = zlib.compress(data, 6)
    t_single = time.perf_counter() - t0

    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=cores) as pool:
        parts = list(pool.map(compress_chunk, chunks))
    t_par = time.perf_counter() - t0

    print(f"cores: {cores}, input: {len(data) >> 20} MiB in {len(chunks)} chunks")
    print(f"one stream, one core : {t_single:6.2f} s  ratio {len(data) / len(one):.2f}")
    print(f"chunks, {cores} workers    : {t_par:6.2f} s  ratio {len(data) / sum(map(len, parts)):.2f}")
    print(f"measured speedup     : {t_single / t_par:6.2f}x")
    print()
    print("Amdahl's law, speedup for p = parallel fraction:")
    for p in (0.5, 0.9, 0.95, 0.99):
        print(f"  p={p:4}: " + "  ".join(f"{n:2d} cores {amdahl(p, n):5.2f}x" for n in (2, 4, 8, 12)))
