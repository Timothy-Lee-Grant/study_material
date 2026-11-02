"""Token bucket rate limiter (lectures/system_design/001 §8.2).

Run: python3 token_bucket.py
"""


class TokenBucket:
    """Allow up to `capacity` requests in a burst, refilled at `rate` tokens per second."""

    def __init__(self, capacity: float, rate: float):
        self.capacity = capacity      # most tokens the bucket can hold (the burst size)
        self.rate = rate              # tokens added per second (the long-run limit)
        self.tokens = capacity        # tokens available right now; start full
        self.last = None              # time of the last update, in seconds

    def allow(self, now: float) -> bool:
        if self.last is not None:
            elapsed = now - self.last
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last = now
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False


class RateLimiter:
    """One bucket per key (user id, API key, IP)."""

    def __init__(self, capacity: float, rate: float):
        self.capacity, self.rate = capacity, rate
        self.buckets = {}

    def allow(self, key: str, now: float) -> bool:
        if key not in self.buckets:
            self.buckets[key] = TokenBucket(self.capacity, self.rate)
        return self.buckets[key].allow(now)


if __name__ == "__main__":
    rl = RateLimiter(capacity=3, rate=1.0)   # burst of 3, then 1 per second
    for t in [0.0, 0.1, 0.2, 0.3, 0.9, 1.3, 1.4, 5.0, 5.0, 5.0, 5.0]:
        print(f"t={t:>4}  alice -> {rl.allow('alice', t)}")
    print("bob at t=0.3 ->", rl.allow("bob", 0.3))
