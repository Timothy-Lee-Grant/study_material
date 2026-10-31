"""
020_hash_table_demo.py - lecture 020: what collisions cost, measured.

A minimal separate-chaining hash set that counts how many stored keys each lookup compares.
Run:  python3 020_hash_table_demo.py
"""


class ChainedSet:
    def __init__(self, hash_fn=hash, max_load=0.75):
        self.hash_fn = hash_fn
        self.max_load = max_load
        self.buckets = [[] for _ in range(8)]
        self.count = 0
        self.compares = 0        # total keys compared during lookups
        self.resizes = 0

    def _bucket(self, key):
        return self.buckets[self.hash_fn(key) % len(self.buckets)]

    def __contains__(self, key):
        for k in self._bucket(key):
            self.compares += 1
            if k == key:
                return True
        return False

    def add(self, key):
        if key in self:
            return
        if (self.count + 1) / len(self.buckets) > self.max_load:
            self._grow()
        self._bucket(key).append(key)
        self.count += 1

    def _grow(self):
        old = self.buckets
        self.buckets = [[] for _ in range(2 * len(old))]
        for chain in old:
            for k in chain:
                self._bucket(k).append(k)
        self.resizes += 1


def experiment(label, hash_fn, keys):
    s = ChainedSet(hash_fn)
    for k in keys:
        s.add(k)
    longest = max(len(c) for c in s.buckets)
    print(f"{label:34s} n={len(keys):6d} buckets={len(s.buckets):6d} "
          f"resizes={s.resizes:2d} longest chain={longest:5d} "
          f"compares per add={s.compares / len(keys):8.2f}")


if __name__ == "__main__":
    for n in (1000, 4000):
        keys = list(range(0, 7 * n, 7))
        experiment("good hash (Python's hash)", hash, keys)
        experiment("every key -> same bucket", lambda k: 0, keys)
        experiment("ignores low bits (k // 1024)", lambda k: k // 1024, keys)
    print()
    print("hash(-1) =", hash(-1), " hash(-2) =", hash(-2), "  <- two different ints, same hash")
    print("hash(10**20) % 8 =", hash(10**20) % 8, "  (ints are hashed modulo 2**61 - 1 on 64-bit CPython)")
