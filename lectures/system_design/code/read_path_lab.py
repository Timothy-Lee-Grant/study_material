#!/usr/bin/env python3
"""Read-path lab for lectures/system_design/002 (standard library only).

Three experiments, each producing a number the lecture uses:
  1. index   - one lookup by id in a 1,000,000-row table, with and without an index
  2. server  - one Python process serving GET /p/<id> over HTTP: requests/s and where the time goes
  3. cache   - hit rate of an LRU cache under a skewed (Zipf) access pattern, for several sizes

Run all:      python3 read_path_lab.py
Run one:      python3 read_path_lab.py index | server | cache
Numbers depend on your machine. Write your predictions in the lecture's table first.
"""

import bisect
import http.client
import multiprocessing
import os
import random
import sqlite3
import statistics
import sys
import tempfile
import threading
import time
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROWS = 1_000_000


def make_db(path, with_index):
    """A table of pastes: id (8-char text) and a 200-byte body."""
    con = sqlite3.connect(path)
    con.execute("DROP TABLE IF EXISTS pastes")
    con.execute("CREATE TABLE pastes (id TEXT, body TEXT)")
    rng = random.Random(1)
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    ids = ["".join(rng.choice(alphabet) for _ in range(8)) for _ in range(ROWS)]
    body = "x" * 200
    con.executemany("INSERT INTO pastes VALUES (?, ?)", ((i, body) for i in ids))
    if with_index:
        con.execute("CREATE INDEX idx_id ON pastes(id)")
    con.commit()
    return con, ids


def time_lookups(con, ids, n):
    rng = random.Random(2)
    sample = [rng.choice(ids) for _ in range(n)]
    t0 = time.perf_counter()
    for k in sample:
        row = con.execute("SELECT body FROM pastes WHERE id = ?", (k,)).fetchone()
        assert row is not None
    return (time.perf_counter() - t0) / n


def exp_index():
    print("\n=== 1. Lookup by id: full scan vs index (1,000,000 rows) ===")
    with tempfile.TemporaryDirectory() as d:
        con, ids = make_db(os.path.join(d, "noidx.db"), with_index=False)
        no_idx = time_lookups(con, ids, 20)
        con.close()
        con, ids = make_db(os.path.join(d, "idx.db"), with_index=True)
        idx = time_lookups(con, ids, 20_000)
        con.close()
    print(f"without index: {no_idx * 1e3:9.2f} ms per lookup  (reads every row)")
    print(f"with index:    {idx * 1e6:9.2f} us per lookup  (walks a B-tree)")
    print(f"speedup:       {no_idx / idx:9.0f}x")
    print(f"max lookups/s on one thread: without {1 / no_idx:,.0f}   with {1 / idx:,.0f}")


# ------------------------------------------------------------------ server

def client_worker(port, sample, seed, n):
    """One client process: n sequential GETs over one kept-alive connection."""
    rng = random.Random(seed)
    conn = http.client.HTTPConnection("127.0.0.1", port)
    out = []
    for _ in range(n):
        t0 = time.perf_counter()
        conn.request("GET", "/p/" + rng.choice(sample))
        resp = conn.getresponse()
        resp.read()
        out.append(time.perf_counter() - t0)
    conn.close()
    return out


def exp_server():
    print("\n=== 2. One process serving GET /p/<id> (index on, same machine) ===")
    # Variant A: the library default. The response leaves as two small writes
    # (headers, then body), and Nagle's algorithm holds the second one back until
    # the client ACKs the first, which the client delays (delayed ACK, ~40 ms).
    run_server(nodelay=False, clients=8, per_client=100)
    # Variant B: one setting changed: TCP_NODELAY (Nagle off) on the server's sockets.
    run_server(nodelay=True, clients=8, per_client=1500)


def run_server(nodelay, clients, per_client):
    label = "TCP_NODELAY on (Nagle off)" if nodelay else "library default (Nagle on)"
    print(f"--- {label} ---")
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "srv.db")
        con, ids = make_db(path, with_index=True)
        con.close()
        handler_times = []
        local = threading.local()

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"   # keep the connection open between requests
            disable_nagle_algorithm = nodelay

            def do_GET(self):
                t0 = time.perf_counter()
                if not hasattr(local, "con"):
                    local.con = sqlite3.connect(path, check_same_thread=False)
                key = self.path.rsplit("/", 1)[-1]
                row = local.con.execute("SELECT body FROM pastes WHERE id = ?", (key,)).fetchone()
                handler_times.append(time.perf_counter() - t0)
                data = (row[0] if row else "not found").encode()
                self.send_response(200 if row else 404)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        port = server.server_address[1]
        threading.Thread(target=server.serve_forever, daemon=True).start()

        # Clients run in separate processes so they don't compete with the
        # server for this Python process's interpreter lock.
        sample = random.Random(9).sample(ids, 5000)
        t0 = time.perf_counter()
        with multiprocessing.Pool(clients) as pool:
            parts = pool.starmap(client_worker, [(port, sample, s, per_client) for s in range(clients)])
        wall = time.perf_counter() - t0
        latencies = [x for part in parts for x in part]
        server.shutdown()

    total = clients * per_client
    latencies.sort()
    p50 = latencies[len(latencies) // 2]
    p99 = latencies[int(len(latencies) * 0.99)]
    db = statistics.median(handler_times)
    print(f"{total} requests from {clients} concurrent clients in {wall:.2f} s")
    print(f"throughput:          {total / wall:8,.0f} requests/s (one Python process)")
    print(f"latency p50 / p99:   {p50 * 1e3:8.2f} / {p99 * 1e3:.2f} ms (client's view)")
    print(f"database part (p50): {db * 1e6:8.1f} us  = {db / p50 * 100:.1f}% of the median request")


# ------------------------------------------------------------------ cache

class LRU:
    def __init__(self, capacity):
        self.capacity = capacity
        self.data = OrderedDict()

    def get(self, key):
        if key in self.data:
            self.data.move_to_end(key)
            return True
        return False

    def put(self, key):
        self.data[key] = True
        self.data.move_to_end(key)
        if len(self.data) > self.capacity:
            self.data.popitem(last=False)


def zipf_sampler(n_items, s, rng):
    """Item k (1-based) is requested with probability proportional to 1 / k^s."""
    weights = [1.0 / (k ** s) for k in range(1, n_items + 1)]
    cumulative, total = [], 0.0
    for w in weights:
        total += w
        cumulative.append(total)
    return lambda: bisect.bisect_left(cumulative, rng.random() * total)


def exp_cache():
    print("\n=== 3. LRU cache hit rate under skewed access (100,000 pastes) ===")
    n_items, n_requests = 100_000, 1_000_000
    for s in (0.8, 1.0):
        rng = random.Random(3)
        draw = zipf_sampler(n_items, s, rng)
        stream = [draw() for _ in range(n_requests)]
        print(f"skew s = {s}:")
        for pct in (1, 5, 10, 20):
            cache, hits = LRU(n_items * pct // 100), 0
            for k in stream:
                if cache.get(k):
                    hits += 1
                else:
                    cache.put(k)
            print(f"  cache holds {pct:>2}% of pastes -> hit rate {hits / n_requests:6.1%}")


if __name__ == "__main__":
    which = sys.argv[1:] or ["index", "server", "cache"]
    for w in which:
        {"index": exp_index, "server": exp_server, "cache": exp_cache}[w]()
