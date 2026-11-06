2026_11_06_12_30-(The-Read-Path)

# Lecture 002: The Read Path: From One Server to a Read-Heavy System

> **For:** Timothy · **Date:** 2026-11-06
> **Prerequisites:** `001-system_design_orientation.md` §3 (the seven-step skeleton) and §4 (the building-block table). Helpful for §2's trace: `../llm_orchistration/014-HTTP_Request_Lifecycle_And_Networking_Deep_Dive.md` and `../dotnet/005-sockets_websockets_and_yarp_1764.md` (sockets and TCP), `../windows_internals/015-performance_analysis_cpu_and_waits.md` (running vs waiting).
> **Why this lecture:** it's the first lecture of the gradient (`000-gradient_roadmap.md`). Almost every product-design question (URL shortener, news feed, any "design X" where people mostly *look at* things) is shaped by its **read path**: what happens when someone asks for data. This lecture builds a read-heavy system from one machine, adding one piece at a time, each time **because a number forced it**. By the end you'll have derived the standard web skeleton (load balancer, stateless servers, cache, database, object storage, replicas) instead of memorizing it.
> **How to use it:** read §0–§2, then **run the lab** (§3) after writing your predictions. Read the forced moves (§4–§9). Then do practice case `a01` (§12) within a few days: it's close to this lecture's worked case, but its hardest part is deliberately left for you.
> **Verification:** every number in §3 comes from running `code/read_path_lab.py` (Python 3.13, SQLite 3.53, a 2-core Linux container, 2026-11-06). Your Mac will give different numbers; the *ratios* are what matter. Estimates elsewhere are labeled as assumptions.
> **Format notes:** 🟢 = own it, 🔵 = know the contract, ⚫ = black box for now.

---

## Core ideas (the answer key)

1. **A design is a sequence of forced moves.** Start with the simplest system that could work; add load until something breaks (with a number); add the one piece that fixes it; say what it costs. Each box in the final diagram exists because of one of those moves.
2. **One request passes through many actors:** DNS, a TCP connection (and TLS), the server machine's kernel and network stack, a server process and thread, the application code, a database client, the database, and back. Most of the latency a user feels is **waiting** (round trips, queues, locks), not computing.
3. **The first fix is usually inside the box, not more boxes:** an index turns a lookup that reads every row (O(n)) into a walk down a B-tree (O(log n)). Measured: 94.5 ms → 8.8 µs on 1,000,000 rows, about 10,000×.
4. **Measure where the time goes before you fix anything.** In the lab, a 0.07 ms database lookup took 44 ms end to end because of a TCP interaction (Nagle's algorithm + delayed ACK). One setting fixed it: 179 → about 5,000 requests per second.
5. **Many app servers need a load balancer, and a load balancer needs stateless servers:** if a server keeps anything about a user between requests, the next request may land on a server that doesn't have it. So that state moves out, into the database or a cache, and any server can answer any request.
6. **Servers needed = peak requests per second ÷ (per-server capacity × target utilization), plus spares for failures.**
7. **Big, rarely-changing blobs go to object storage; the database keeps small metadata** (id, owner, size, expiry, where the blob is).
8. **Cache-aside:** read the cache; on a miss, read the store and fill the cache. Average latency = `t_cache + (1 − h) × t_store`, and the store sees only `(1 − h)` of the reads. Hit rate `h` depends on how skewed the access pattern is: a cache holding 10% of items got 47% hits at Zipf skew 0.8 and 74% at skew 1.0.
9. **Immutable data is the easiest data to cache.** The hard parts are deletion and expiry (invalidation) and a hot key expiring all at once (a stampede).
10. **Read replicas add read capacity and survive failures, but lag behind the primary.** That breaks *read-your-writes* (you create something and immediately get "not found") unless you route those reads to the primary or fall back to it.
11. **Don't add a box no requirement asks for.** At this scale the metadata fits one database: no sharding, no queues yet. Saying *why not* is part of the answer.

---

## Table of Contents

- [0. How this lecture (and series) teaches](#0-how-this-lecture-and-series-teaches)
- [1. The worked case: a paste-sharing service](#1-the-worked-case-a-paste-sharing-service)
- [2. Version 0: one machine, and one request through it](#2-version-0-one-machine-and-one-request-through-it)
- [3. Lab: measure before you design](#3-lab-measure-before-you-design)
- [4. Requirements and numbers](#4-requirements-and-numbers)
- [5. Forced move 1: an index](#5-forced-move-1-an-index)
- [6. Forced moves 2 and 3: separate the database, then many stateless servers behind a load balancer](#6-forced-moves-2-and-3-separate-the-database-then-many-stateless-servers-behind-a-load-balancer)
- [7. Forced move 4: object storage for the paste bodies](#7-forced-move-4-object-storage-for-the-paste-bodies)
- [8. Forced move 5: a cache](#8-forced-move-5-a-cache)
- [9. Forced move 6: read replicas, and the read-your-writes problem](#9-forced-move-6-read-replicas-and-the-read-your-writes-problem)
- [10. The finished design, as the seven steps](#10-the-finished-design-as-the-seven-steps)
- [11. What we didn't add, and why](#11-what-we-didnt-add-and-why)
- [12. Practice](#12-practice)
- [Misconceptions](#misconceptions)
- [Interview relevance](#interview-relevance)
- [Self-check questions](#self-check-questions)
- [Sources](#sources)

---

## 0. How this lecture (and series) teaches

You said lecture documents make topics click quickly for you, and that's the plan: lectures build the **model**, practice cases make it **fast and spoken**. The two are paired. Each lecture ends with the case to attempt next.

What's different from how system design is usually taught: most courses give you a catalogue of components and a gallery of famous designs. You'd learn what a cache *is*, but not the moment it becomes necessary. This series builds every design by **forced moves**:

```
simplest system that could work
        │
        ▼
add load / a requirement ──► something breaks (a number says so)
        ▲                               │
        │                               ▼
   say what it costs  ◄──  add exactly the piece that fixes it
```

Each lecture also has a **trace** (one request, every actor named), a **lab** that produces the numbers, and **derivations** for every formula, with each symbol defined before it's used. Full plan: `000-gradient_roadmap.md`.

---

## 1. The worked case: a paste-sharing service

**The problem** (it's the classic "Pastebin" question):

> Users paste a block of text (up to 1 MB, about 10 KB on average) and get back a link like `https://paste.example/k3Xp9qLm`. Anyone with the link can read the paste. A paste can have an expiry time; by default it's kept for one year. Pastes can't be edited after they're created, but the author can delete one.
>
> Scale: 10 million new pastes a day. On average each paste is read 100 times, and reads are very uneven: a few pastes are read millions of times, most only a few. Reading a paste should take under 100 ms at the server for 99% of requests (p99). The service should stay up when any single machine fails.

**Why this case:** it's almost all read path (100 reads per write), and it's close to practice case `a01` (URL shortener). One thing is deliberately **left out** here: how to generate a unique short id across many servers. In this lecture, assume a function `new_id()` that returns a fresh, unique 8-character id. Building that function is the deep dive of `a01`, and it's yours to work out there.

---

## 2. Version 0: one machine, and one request through it

The simplest system that could work: **one machine**, running one web server process with the application code, and a database on the same machine.

```
 browser ──── internet ────► [ one machine:  web server process (app code)  ──►  database ]
```

Here's one read, `GET https://paste.example/k3Xp9qLm`, with every actor named. "RTT" means one **round trip time**: a message from the browser to the server and the reply back. Within a city, an RTT is a few milliseconds; across a continent, about 50–100 ms.

| # | Where it runs | Actor | What it does | Waits for |
|---|---|---|---|---|
| 1 | User's computer | Browser | Needs the IP address for `paste.example` | — |
| 2 | User's computer → DNS servers | OS resolver → recursive DNS resolver → the domain's authoritative DNS server | Turn the name into an IP address (usually cached, so often 0 RTT) | Up to a few RTTs on a cold cache |
| 3 | Both machines' kernels | TCP | Three-way handshake to open a connection to port 443 | 1 RTT |
| 4 | Browser + server process | TLS | Agree on keys, check the server's certificate | 1 RTT (TLS 1.3) |
| 5 | Browser → network → server | HTTP | The request bytes (`GET /k3Xp9qLm …`) travel to the server | ½ RTT |
| 6 | Server machine | Network card → kernel TCP stack | Puts the bytes in that connection's socket receive buffer, then wakes the thread waiting on that socket | — |
| 7 | Server process, one thread | Web server (framework) | Reads the bytes from the socket, parses the HTTP request, calls your handler | A free thread (if all are busy, the request **queues**) |
| 8 | Same thread | Your application code | Extracts `k3Xp9qLm`, asks the database client for that row | — |
| 9 | Same thread → database process | Database client library → database | Sends the query over a local socket; the database finds the row (via an index, §5) in memory or on disk | Disk if the page isn't in memory |
| 10 | Same thread | Your code + framework | Builds the HTTP response, writes it to the socket | — |
| 11 | Server kernel → network → browser | TCP | Bytes go back; the browser renders the paste | ½ RTT |

Three things to take from the trace:

1. **A brand-new visitor pays about 3 RTTs before seeing anything** (TCP, TLS, request/response), plus DNS on a cold cache. At 80 ms per RTT, that's about a quarter of a second of pure travel. That's why connections are kept open between requests, and why content gets served from machines near users (a CDN, §8.5). No server-side optimization fixes travel time.
2. **Steps 7 and 9 are where waiting piles up on the server:** waiting for a free thread, a lock, or the disk. When a server is "slow", the request is usually *waiting* somewhere, not *running*. (`windows_internals/015` §1 is the same distinction in a CPU profile.)
3. **The only box we wrote is step 8.** Everything else is a layer someone else built. Knowing what each one does is what lets you say where a slowdown lives.

**Where does Version 0 break?** We don't know yet. Measure first.

---

## 3. Lab: measure before you design

`code/read_path_lab.py` (standard library only) runs three experiments. Each one produces a number that forces a move later in this lecture.

**Before running it, write your predictions** (this has worked for you before; a wrong prediction is the most useful kind):

| Question | Your prediction | Measured (my run) | Your run |
|---|---|---|---|
| Lookup by id in 1,000,000 rows, **no index**: time per lookup? | | 94.5 ms | |
| Same, **with an index**? | | 8.8 µs | |
| One Python server process, library defaults: requests per second? | | 179 | |
| Same, with one TCP setting changed? | | about 5,000 | |
| LRU cache holding 10% of pastes: hit rate? | | 47% (skew 0.8) / 74% (skew 1.0) | |

Run it from the repo root:

```bash
python3 lectures/system_design/code/read_path_lab.py          # all three, about 30 s
python3 lectures/system_design/code/read_path_lab.py server   # just one
```

### 3.1 My output

```
=== 1. Lookup by id: full scan vs index (1,000,000 rows) ===
without index:     94.51 ms per lookup  (reads every row)
with index:         8.84 us per lookup  (walks a B-tree)
speedup:           10697x
max lookups/s on one thread: without 11   with 113,184

=== 2. One process serving GET /p/<id> (index on, same machine) ===
--- library default (Nagle on) ---
800 requests from 8 concurrent clients in 4.48 s
throughput:               179 requests/s (one Python process)
latency p50 / p99:      44.00 / 48.09 ms (client's view)
database part (p50):     70.7 us  = 0.2% of the median request
--- TCP_NODELAY on (Nagle off) ---
12000 requests from 8 concurrent clients in 2.42 s
throughput:             4,963 requests/s (one Python process)
latency p50 / p99:       1.41 / 4.56 ms (client's view)
database part (p50):    557.3 us  = 39.5% of the median request

=== 3. LRU cache hit rate under skewed access (100,000 pastes) ===
skew s = 0.8:
  cache holds  1% of pastes -> hit rate  20.3%
  cache holds  5% of pastes -> hit rate  36.8%
  cache holds 10% of pastes -> hit rate  46.6%
  cache holds 20% of pastes -> hit rate  58.7%
skew s = 1.0:
  cache holds  1% of pastes -> hit rate  50.6%
  cache holds  5% of pastes -> hit rate  66.4%
  cache holds 10% of pastes -> hit rate  73.5%
  cache holds 20% of pastes -> hit rate  80.6%
```

### 3.2 The 44-millisecond mystery (experiment 2)

The database lookup took 0.07 ms, yet every request took 44 ms. **99.8% of the request was something else.** Here's what, derived step by step:

1. Python's `http.server` sends a response as **two writes** to the socket: the headers, then the body.
2. TCP has **Nagle's algorithm** (on by default): if a small segment has been sent and not yet acknowledged, hold any further small data back until the acknowledgment (ACK) arrives. It exists to avoid flooding a network with tiny packets.
3. The client's TCP has **delayed ACK** (also on by default): don't acknowledge right away; wait a little (about 40 ms on Linux) in case there's data to send back, so the ACK can ride along with it.
4. Put 2 and 3 together: the server sends the headers, then holds the body until the headers are ACKed. The client waits for more data before ACKing, which is the body the server is holding. Both wait until the client's delayed-ACK timer fires: **~40 ms**, on every request.
5. Fix: set `TCP_NODELAY` on the server's sockets (turn Nagle off), so the second write goes out immediately. In the lab that's one line: `disable_nagle_algorithm = True`. Result: 44 ms → 1.4 ms per request, 179 → about 5,000 requests per second.

(On macOS the delayed-ACK timing differs, so your number for the first variant may differ. That's part of the experiment.)

**The design lesson isn't about Nagle.** It's that a guess ("the database must be the slow part") would have been wrong by a factor of 500. In a design interview you can't run a profiler, but you can say: *"Before adding capacity, I'd measure where requests spend their time: queueing, the network, the database, or our code."*

### 3.3 Why the database share grew to 40% with Nagle off

With Nagle off, the median database part rose from 0.07 ms to 0.56 ms. The lookup didn't get slower. A Python process runs **one thread at a time** (the interpreter lock), and with 8 requests in flight on a 2-core machine, each handler thread spends most of its "database time" waiting for its turn to run. The number measures *waiting* again. This is also why one Python process tops out at roughly one core's worth of work: to use more cores or more machines, you run **more processes**. That's forced move 3.

---

## 4. Requirements and numbers

Step 1 of the skeleton, for the case in §1.

**Functional:** create a paste (text → link) · read a paste by link · delete your own paste · pastes expire.
**Non-functional:** read p99 < 100 ms at the server · survives the loss of any one machine · reads ≫ writes · a deleted or expired paste must stop being served (within a minute is acceptable).
**Out of scope:** accounts beyond "the author can delete", search, editing, syntax highlighting, analytics.

Now the numbers. Each quantity is named before it's used; 1 day ≈ 10⁵ seconds (exactly 86,400).

1. `writes_per_day = 10⁷`, so `writes_per_second = 10⁷ / 10⁵ = 100` (exact ≈ 116).
2. `reads_per_day = writes_per_day × 100 = 10⁹`, so `reads_per_second = 10⁹ / 10⁵ = 10⁴` (exact ≈ 11,600).
3. Traffic isn't flat over a day. **Assumption:** `peak = 3 × average`, so `peak_reads_per_second ≈ 3 × 10⁴`.
4. `bytes_per_paste ≈ 10 KB = 10⁴ bytes`, so `new_bytes_per_day = 10⁷ × 10⁴ = 10¹¹ bytes = 100 GB`, and `bytes_per_year ≈ 365 × 100 GB ≈ 36.5 TB` (before keeping extra copies).
5. `read_bandwidth = peak_reads_per_second × bytes_per_paste = 3×10⁴ × 10⁴ = 3×10⁸ bytes/s = 300 MB/s` (about 2.4 Gbit/s) leaving the service at peak.

What these numbers decide (always say this part out loud; it's why you computed them):

| Number | Decision it forces | Where |
|---|---|---|
| 30,000 reads/s at peak | More than one server process can handle; a single database would be busy | §6, §8 |
| 36.5 TB per year of paste bodies | Bodies don't belong in a relational database's rows | §7 |
| 300 MB/s outgoing | Serving popular pastes from near the user (CDN) would remove most of it | §8.5 |
| 116 writes/s | Easy for one database. **Writes don't force anything yet.** | §11 |

---

## 5. Forced move 1: an index

**What breaks:** in Version 0, without an index, the lab measured **94.5 ms** per lookup in 1,000,000 rows, about **11 lookups per second**. We need 30,000. And the table grows by 10 million rows a day, so the scan only gets slower.

**Why a lookup without an index is slow:** the database has no way to know where `k3Xp9qLm` is, so it reads every row and compares. Cost grows with the number of rows: O(n).

**What an index is** 🟢: a separate structure, kept sorted by the indexed column, that maps a value to where its row is. Most databases use a **B-tree**: a tree that is very wide (hundreds of keys per node) and therefore very shallow. A node is one disk page (often 4–16 KB).

How deep is it? Derive it:

1. Name the quantities: `rows = 10⁹` (about 100 days of pastes); `keys_per_node ≈ 500` (an assumption: an 8-byte key plus a pointer fits about 500 times in a few KB).
2. Each level multiplies the number of reachable rows by `keys_per_node`: after `d` levels, `500^d` rows are reachable.
3. We need `500^d >= 10⁹`. `500^3 = 1.25×10⁸` (too few), `500^4 = 6.25×10¹⁰` (enough). So `d = 4`.
4. So a lookup among a **billion** rows reads about **4 pages**, and the top levels are almost always already in memory. That's O(log n) with a huge base.

**Measured:** 8.8 µs per lookup, about 10,700× faster.

**What it costs:** every insert also updates the index (writes get a little slower), and the index takes space. For a read-heavy service that's an easy trade.

**In an interview:** you rarely need more than "the paste id is the primary key, so lookups go through the primary-key index: O(log n), a few page reads." Saying it shows you know the first fix is *inside* the box.

---

## 6. Forced moves 2 and 3: separate the database, then many stateless servers behind a load balancer

### 6.1 Forced move 2: put the database on its own machine

**What breaks:** the lab's single Python process handled about 5,000 requests/s; we need 30,000 at peak. More app processes would help, but on one machine they'd fight the database for CPU and memory. The two have different needs: app servers want CPU and are cheap and replaceable; the database wants memory (to keep its hot pages cached) and fast, reliable disks, and it holds the data that matters.

**The move:** the database gets its own machine. App servers connect to it over the datacenter network (about 0.5 ms per round trip).

**What it costs:** every query now crosses the network, which is one more thing that can be slow or fail. In exchange, app servers and the database can be **scaled and replaced independently**. App servers become *disposable*: you can add, remove or restart them freely. That only works if they hold nothing that matters, which is the next move.

### 6.2 Forced move 3: many app servers, a load balancer, and statelessness

**How many servers?** Name the quantities:

- `peak_rps = 3×10⁴` (requests per second at peak, §4)
- `per_server_rps`: what one server handles. The lab measured about 5,000 for one Python process. **Assumption for planning:** a production server (several cores, several processes) handles 10,000.
- `target_utilization = 0.5`: plan to run servers at half capacity, so a traffic spike or a lost server doesn't push the rest over the edge.

Derivation:

1. Capacity you can actually use per server: `per_server_rps × target_utilization = 10,000 × 0.5 = 5,000`.
2. Servers needed: `peak_rps / usable_per_server = 30,000 / 5,000 = 6`.
3. Add spares so losing one machine doesn't matter: `6 + 1 = 7` (more if they're spread across several datacenter zones).

**The load balancer** 🟢: one entry point (one address in DNS) that spreads incoming requests across the healthy app servers.

| Decision | Options | Default answer |
|---|---|---|
| Layer | **L4** (forwards TCP connections; fast, sees only addresses and ports) or **L7** (understands HTTP; can route by path or header, terminate TLS) | L7 for a web API; L4 when raw throughput matters most |
| Algorithm | round robin · least connections · hash of a key (same client → same server) | Least connections (or round robin) for stateless servers |
| Health checks | The LB calls each server's `/health` every few seconds and stops sending traffic to one that fails | Always; it's how "survives one machine failing" actually happens |
| Is the LB a single point of failure? | Yes, unless doubled: two LBs with failover, or a managed cloud LB that's already redundant | Say "a redundant pair or a managed LB" |

**Why statelessness is forced** (trace it):

1. Suppose server A keeps something in its own memory between requests, for example "user 7's delete-confirmation token".
2. User 7's next request arrives at the load balancer, which picks server B (least connections).
3. Server B has never seen the token. The request fails.
4. Fix options: (a) make the LB always send user 7 to server A ("sticky sessions"): this breaks when A dies or is restarted, and uneven users make uneven servers; (b) **move the state out** of the app server, into the database or a shared cache, so any server can answer any request.
5. Option (b) is what "stateless app servers" means. The state still exists. It just lives somewhere every server can reach. 🟢

(`../yarp/006-load_balancing_and_traffic_distribution.md` covers balancing algorithms in a real proxy you've worked with.)

---

## 7. Forced move 4: object storage for the paste bodies

**What breaks:** 36.5 TB of paste bodies per year (§4). Relational databases are built for many small rows that get searched, joined and updated, with every byte living on the database machines (and their replicas). Storing terabytes of large, never-edited text in rows makes backups, replication and recovery slow, and makes the database machines expensive for a job that doesn't need a database.

**The move:** split each paste into two parts:

| Part | Size | Where it lives | Why |
|---|---|---|---|
| **Metadata**: `id`, `created_at`, `expires_at`, `size`, `deleted`, `delete_token_hash`, `object_key` | ~100–200 bytes | The database | Small, looked up by id, updated on delete |
| **Body**: the text itself | ~10 KB average, up to 1 MB | **Object storage** (S3, Azure Blob Storage, Google Cloud Storage): a service that stores blobs by key, replicates them, and scales to petabytes | Written once, read many times, never edited |

🔵 Object storage contract: `put(key, bytes)`, `get(key) -> bytes`, `delete(key)`; durable (copies on several machines); a single read typically takes **tens of milliseconds** (an assumption for planning; it's slower than a cache or a database index lookup, but it holds everything).

**What it costs:** a read is now two hops (metadata, then body), and the slower hop is the body. That's the next thing to fix.

The read path now:

1. App server looks up metadata by id in the database (index, about 1 ms with the network hop).
2. If it doesn't exist, or is deleted or expired → 404.
3. Otherwise, get the body from object storage by `object_key` (tens of ms) → return it.

---

## 8. Forced move 5: a cache

### 8.1 What breaks

Every read now costs a database lookup plus an object-storage fetch (tens of ms), 30,000 times a second at peak. The object store is the slow hop on every single read, and the database is answering 30,000 queries a second that mostly ask for the same popular pastes. The access pattern is very uneven (§1): that unevenness is what a cache exploits.

### 8.2 The move: cache-aside 🟢

A **cache** is a fast in-memory key-value store (Redis or Memcached), on its own machines, shared by all app servers. "Cache-aside" means the **app code** manages it:

1. Read: ask the cache for `paste:k3Xp9qLm`.
2. **Hit:** return the cached value. Done.
3. **Miss:** read metadata from the database and the body from object storage, as in §7.
4. Store the result in the cache with a time-to-live (TTL), then return it.

The cache never talks to the database itself; the app fills it. (The alternatives: *read-through*, where the cache fetches on a miss itself, and *write-through*, where every write also goes into the cache. §9 uses write-through for one specific reason.)

### 8.3 What it buys, as a derivation

Name the quantities:

- `h`: the hit rate, the fraction of reads found in the cache. Valid set: `0 <= h <= 1`.
- `t_cache`: time for one cache lookup, including the network hop. **Assumption:** 1 ms.
- `t_store`: time for the miss path (database + object storage). **Assumption:** 30 ms.

Every read pays `t_cache` (you always check the cache first). Only misses also pay `t_store`. So:

1. A hit costs `t_cache`. A miss costs `t_cache + t_store`.
2. Average = (fraction of hits × cost of a hit) + (fraction of misses × cost of a miss):
   `avg = h × t_cache + (1 − h) × (t_cache + t_store)`
3. Expand: `avg = h × t_cache + (1 − h) × t_cache + (1 − h) × t_store`
4. The first two terms add up to `t_cache`: **`avg = t_cache + (1 − h) × t_store`**
5. And the store only sees misses: **`store_reads_per_second = (1 − h) × reads_per_second`**

With `h = 0.74` (the lab's 10%-sized cache at skew 1.0):

- `avg = 1 + 0.26 × 30 ≈ 8.8 ms` (instead of 31 ms)
- `store_reads_per_second = 0.26 × 30,000 ≈ 7,800` (instead of 30,000)

**About the tail:** the p99 target is 100 ms. Averages hide the slowest requests; here the slowest normal request is a miss at about 31 ms, which is still under target. If the store's own p99 were 150 ms, the cache wouldn't save the p99 (only the average), and you'd need to say so.

**How big should the cache be?** The lab shows the answer depends on *how skewed* the access is: holding 10% of pastes gave 47% hits at skew 0.8 and 74% at skew 1.0. You can't know the skew in an interview, so state an assumption and what it implies:

1. **Assumption:** almost all reads are of pastes from the last 7 days. `hot_pastes = 7 × 10⁷`.
2. `hot_bytes = 7×10⁷ × 10 KB = 7×10¹¹ bytes = 700 GB`.
3. Cache 10% of that: `70 GB` of memory, for example three cache machines with 32 GB each (with room to spare).
4. Say: *"I'd size it from measured hit rates in production; 10% of the hot set is a starting point."*

### 8.4 Invalidation: when cached data must stop being served 🟢

Pastes are **immutable**: a cached copy can never become *wrong*, only *no longer allowed*. That makes this the easy case of caching. Two events end a paste:

**Expiry.** Set the cache entry's TTL so it can't outlive the paste: `ttl = min(default_ttl, expires_at − now)`. The read path also checks `expires_at` on a miss.

**Delete.** Two steps: mark the database row deleted, and delete the cache entry. **Which order?** Trace both:

| Order | Interleaving with a concurrent reader | Result |
|---|---|---|
| Cache first, then database | 1. Delete removes the cache entry. 2. A reader misses, reads the database (row not yet marked deleted), and **re-fills the cache**. 3. Delete marks the row. | The deleted paste is served from the cache until its TTL runs out ❌ |
| **Database first, then cache** | 1. Delete marks the row. 2. A reader may still hit the old cache entry for a moment. 3. Delete removes the cache entry. Any later miss reads "deleted" | Served for at most a moment after the delete ✅ (within "a minute is acceptable") |

So: **change the source of truth first, then remove the cached copy.**

**Stampede** 🔵. A very popular paste's cache entry expires (or a cache machine restarts). In the next millisecond, thousands of requests miss at once and all go to the database and object store for the same key. Fixes: **request coalescing** (on each app server, only the first miss for a key fetches it; the others wait for that result) and **jittered TTLs** (add a random few percent to each TTL so popular entries don't expire together).

### 8.5 One more layer: a CDN 🔵

§4 found 300 MB/s leaving the service at peak, and §2 found that a new visitor pays several round trips before seeing anything. A **content delivery network** (CDN) is a network of cache servers in many cities. The user's request goes to the nearest one; if it has the paste, it answers without touching our servers.

- **Buys:** fewer and shorter round trips for users far away, and most of the 300 MB/s never reaches us.
- **Fits because:** pastes are immutable and public, the perfect CDN content.
- **Costs:** deletes now also need a **purge** call to the CDN (or a short CDN TTL, like 60 seconds, which matches "within a minute"), and the CDN is a bill.

### 8.6 The same idea one layer down

The database itself does cache-aside internally: its **buffer pool** keeps recently used pages in memory and only reads the disk on a miss, and below that the operating system's **page cache** does the same for files. When §5 said "the top levels of the B-tree are almost always in memory," that's those caches at work. The hit-rate formula in §8.3 applies to every one of these layers.

---

## 9. Forced move 6: read replicas, and the read-your-writes problem

### 9.1 What breaks

The requirement "survive the loss of any one machine" (§4). The metadata database is now **one machine**. If it dies, every cache miss fails, and creates fail too. The cache doesn't help for long: misses keep coming.

### 9.2 The move: one primary, two replicas 🟢

- All **writes** go to the **primary**.
- The primary sends every change to two **replicas**, which apply it in the same order. Usually this is **asynchronous**: the primary confirms the write to the app before the replicas have it.
- **Reads** (cache misses) go to the replicas, spreading the 7,800 misses per second.
- If the primary dies, a replica is **promoted** to primary (failover), automatically or by an operator.

**Costs:** three copies of the metadata, and **replication lag**: a replica is behind the primary by some milliseconds normally, and by seconds under load. Asynchronous replication can also **lose the last few writes** if the primary dies before sending them (synchronous replication avoids that at the cost of slower writes; lecture 006 goes deeper).

### 9.3 The read-your-writes problem (trace it)

1. `t = 0 ms`: a user creates a paste. App server A writes metadata to the **primary** and returns the link.
2. `t = 50 ms`: the user's browser opens the link. The load balancer picks app server B.
3. Server B checks the cache: **miss** (the paste is brand new).
4. Server B reads metadata from **replica 2**, which is 200 ms behind the primary.
5. Replica 2 doesn't have the row yet → **404**. The user sees "not found" for the paste they just made.

Fixes, with costs:

| Fix | How | Cost |
|---|---|---|
| **Write-through on create** | After creating a paste, the app also puts it into the cache. The next read is a hit | One extra cache write per create (116/s, nothing) |
| **Fall back to the primary on "not found"** | If a replica says "not found", ask the primary before answering 404 | Extra primary load for every unknown id; someone scanning random ids now hits the primary (cache the "not found" briefly, and rate limit) |
| Read from the primary for a few seconds after your own write | The app remembers (for example in a cookie) that this client just wrote | More moving parts; doesn't help the author's friend who opens the link at once |

**Choice for this design:** write-through on create, plus the primary fallback as a safety net. Saying *which* reads need the latest data, and routing only those to the primary, is the general principle.

---

## 10. The finished design, as the seven steps

```
                      browser
                         │  DNS: paste.example
                         ▼
                 CDN edge (near the user) ───── hit ─────► response
                         │ miss
                         ▼
              load balancer (redundant pair, health checks)
              │         │         │
           app 1     app 2  …  app 7          stateless; any server answers any request
              │  ╲
              │   ╲──► cache cluster          cache-aside; TTL ≤ expiry; write-through on create
              │
              ├──► metadata DB: primary ──async──► replica 1, replica 2
              │                (writes)              (cache-miss reads)
              │
              └──► object storage             paste bodies, key = paste id
```

| Step | This design |
|---|---|
| **1. Requirements** | §4: create, read, delete, expire; read p99 < 100 ms; survive one machine; deleted pastes gone within a minute. Numbers: 30,000 reads/s peak, 116 writes/s, 36.5 TB/year |
| **2. Interface** | `POST /pastes {text, expires_in?}` → `201 {id, url, delete_token}` · `GET /{id}` → `200 text` or `404` · `DELETE /{id}` with `delete_token` → `204`. Example: `GET /k3Xp9qLm` → `200`, the paste text |
| **3. State** | Metadata row (`id`, `created_at`, `expires_at`, `size`, `deleted`, `delete_token_hash`, `object_key`) in the database; written by create and delete, on the primary only. Body in object storage; written once by create. Cache entries; written by app servers on miss and on create |
| **4. One flow (read)** | Browser → CDN (miss) → load balancer → app server → cache (miss) → replica (metadata, check deleted/expired) → object storage (body) → fill cache with TTL → response → CDN stores it → browser |
| **4b. One flow (create)** | App server → `new_id()` → **put body in object storage first** → insert metadata on the primary → put into cache → return the link |
| **5. Components** | The diagram above. Each box traces to a forced move: index §5, separate DB and LB + stateless servers §6, object storage §7, cache and CDN §8, replicas §9 |
| **6. Deep dive** | The read path at 30,000/s: hit-rate math, cache sizing, invalidation order, stampede (§8) |
| **7. Failures and trade-offs** | App server dies → health checks remove it; its in-flight requests fail and are retried by clients. Cache machine dies → its keys miss: store reads rise toward 30,000/s for a while, so the replicas must be able to absorb a cache loss (or the cache is replicated). Primary dies → failover in seconds; creates fail meanwhile; async replication may lose the last writes. Object storage slow → timeouts on misses; hits are unaffected. **At 10×:** more app servers and cache, and the metadata table (7 TB/year) now needs partitioning (lecture 006) |

**Why the body goes in before the metadata (step 4b)**, traced the same way as §8.4:

- Metadata first, then the body upload fails: readers find a paste whose body doesn't exist → errors. ❌
- **Body first**, then the metadata insert fails: an orphan blob nobody points to → harmless; a cleanup job can delete orphans later. ✅

The rule: **write the thing being pointed to before the pointer.** (It's the same ordering rule as crash consistency in `../storage/001-crash_consistency.md`.)

**Expired pastes:** a nightly batch job deletes expired metadata and their blobs. It's **not** on the read path; reads already check `expires_at`.

---

## 11. What we didn't add, and why

An interviewer is checking whether every box has a reason, so say what you left out:

| Not added | Why not (with the number) | When it would become necessary |
|---|---|---|
| **Sharding** the metadata | `10⁷ rows/day × 365 × ~200 bytes ≈ 730 GB/year`: fits on one large database machine (plus replicas) for a couple of years | When the data or the write rate outgrows one primary (lecture 006) |
| **A message queue** | No work needs to happen after the response; 116 writes/s is easy | If creates needed slow processing (virus scanning, syntax highlighting): lecture 004 |
| **Several microservices** | One app service does three simple things | When teams or very different scaling needs split it |
| **Multiple regions** | Not required; one region with several zones meets "survive one machine" | If users need low latency worldwide for creates, or the business needs to survive a region outage |

---

## 12. Practice

In this order:

1. **Run the lab** (§3) with your predictions written first. Note where you were furthest off.
2. **Drill 3** in `practice/drills.md` (estimation reps, 10 min).
3. **Attempt `a01` (URL shortener)**, timed, out loud: `python3 practice.py start a01` in `practice/`. Almost everything in this lecture transfers. What's **new**, and is your deep dive: generating a unique short code across many servers at the same time, choosing 301 vs 302 redirects, and two users requesting the same custom alias at once. Those are left out of this lecture on purpose.
4. **Bridge `e02`** (LRU cache with expiry) within a few days: it's the cache box of §8, as code.

**Recall prompt for a walk:** *"Trace one read through the finished design, naming every component and what it does. Then derive the average-latency formula for cache-aside, and explain why the delete updates the database before the cache."*

---

## Misconceptions

| You might think | Reality | Why |
|---|---|---|
| "The database is the slow part" | Measure first: in the lab, 99.8% of each request was a TCP interaction | Requests mostly *wait*; the guess can be off by 500× |
| "More servers fix a slow query" | A missing index makes every server equally slow, and they all pile onto the same database | Fix inside the box first (§5) |
| "Stateless servers means there's no state" | The state still exists; it moved to the database or cache, where every server can reach it | §6.2 |
| "A cache always helps" | It helps in proportion to the hit rate, and only the average unless the misses are fast enough too | `avg = t_cache + (1 − h) × t_store` (§8.3) |
| "Read replicas make writes faster" | All writes still go to one primary; replicas add read capacity and failover | §9.2 |
| "Delete from the cache, then the database" | That order lets a concurrent reader re-fill the cache with deleted data | §8.4 |
| "A load balancer removes single points of failure" | One load balancer *is* a single point of failure unless it's a redundant pair or a managed service | §6.2 |

---

## Interview relevance

Sentences that carry this lecture into an interview:

- *"Reads outnumber writes 100 to 1, so the read path shapes this design. Let me size it: about 10⁴ reads a second on average, 3×10⁴ at peak."*
- *"The id is the primary key, so a lookup is a B-tree walk: a few page reads even at a billion rows."*
- *"App servers are stateless, so the load balancer can send any request anywhere and I can lose a server without losing anything."*
- *"Paste bodies go to object storage; the database only holds small metadata."*
- *"I'd put a cache-aside cache in front. With a 75% hit rate, the store sees a quarter of the reads, and the average drops to about `t_cache + 0.25 × t_store`."*
- *"Pastes are immutable, so caching is easy; the only invalidation is delete and expiry, and I update the database before removing the cache entry."*
- *"Replicas lag, so right after a create I'd write the paste into the cache, so the author doesn't get a 404 from a replica."*
- *"I haven't sharded, because the metadata is about 730 GB a year; I'd revisit that at 10×."*

---

## Self-check questions

1. Name, in order, the actors a first-time `GET` passes through before the app code runs.
<details><summary>Answer</summary>Browser → DNS (OS resolver, recursive resolver, authoritative server; often cached) → TCP handshake (both kernels) → TLS handshake → the request bytes over the network → the server's network card and kernel TCP stack (socket buffer) → a thread in the web server process, which parses HTTP and calls the handler.</details>

2. Why does a brand-new visitor far away wait about a quarter of a second even if the server is instant?
<details><summary>Answer</summary>About 3 round trips (TCP, TLS, request/response) at ~80 ms each, plus DNS on a cold cache. Only shortening the distance (a CDN) or reusing connections helps.</details>

3. Derive the depth of a B-tree with 500 keys per node holding 10⁹ rows.
<details><summary>Answer</summary>After d levels, 500^d rows are reachable. 500³ = 1.25×10⁸ < 10⁹ ≤ 500⁴ = 6.25×10¹⁰, so d = 4 page reads per lookup.</details>

4. In the lab, what made the default server take 44 ms per request, and what fixed it?
<details><summary>Answer</summary>The response went out as two small writes (headers, body). Nagle's algorithm held the body until the headers were ACKed; the client delayed its ACK (~40 ms) hoping to piggyback it. Setting TCP_NODELAY on the server's sockets sends the body immediately.</details>

5. You need 40,000 requests/s at peak; a server handles 8,000 and you plan for 50% utilization. How many servers?
<details><summary>Answer</summary>Usable per server = 8,000 × 0.5 = 4,000. 40,000 / 4,000 = 10, plus at least 1 spare = 11.</details>

6. Explain, with a two-request trace, why load-balanced servers must be stateless.
<details><summary>Answer</summary>Request 1 lands on server A, which stores something in its own memory. Request 2 from the same user lands on server B, which doesn't have it, so it fails. Move the state to a shared store so any server can answer.</details>

7. Why put paste bodies in object storage instead of the database?
<details><summary>Answer</summary>36.5 TB a year of large, never-edited blobs would make the database huge and slow to back up, replicate and recover. Object storage is built for durable blobs by key; the database keeps only small, searchable metadata.</details>

8. Derive the average latency with cache-aside.
<details><summary>Answer</summary>Hit costs t_cache; miss costs t_cache + t_store. avg = h·t_cache + (1−h)(t_cache + t_store) = t_cache + (1−h)·t_store.</details>

9. Hit rate 0.8, t_cache = 1 ms, t_store = 40 ms, 20,000 reads/s. Average latency and store reads per second?
<details><summary>Answer</summary>avg = 1 + 0.2 × 40 = 9 ms. Store reads = 0.2 × 20,000 = 4,000/s.</details>

10. Why does a delete update the database before deleting the cache entry?
<details><summary>Answer</summary>If the cache entry goes first, a concurrent reader can miss, read the not-yet-deleted row and re-fill the cache, which then serves the deleted paste until its TTL. Database first means the worst case is a brief moment of serving the old entry.</details>

11. What is a cache stampede, and two ways to prevent one?
<details><summary>Answer</summary>A hot key's entry disappears (expiry, restart) and thousands of simultaneous misses hit the store for that key. Prevent with request coalescing (one fetch per key; the rest wait for it) and jittered TTLs.</details>

12. A user creates a paste and immediately gets 404. Explain the cause and give two fixes.
<details><summary>Answer</summary>The read missed the cache and went to a replica that hadn't received the new row yet (replication lag). Fixes: write the new paste into the cache on create; on "not found" from a replica, check the primary before answering 404.</details>

13. Why is the body written before the metadata on create?
<details><summary>Answer</summary>If the metadata is written first and the body upload fails, readers find a paste with no body. Body first means a failure leaves only an unreferenced blob, which is harmless and can be cleaned up. Write what's pointed to before the pointer.</details>

14. Why no sharding in this design?
<details><summary>Answer</summary>The metadata is ~730 GB a year and writes are ~116/s: one primary handles that for years. Sharding adds a lot of complexity, so it waits until a number forces it.</details>

---

## Sources

- SQLite, "Query Planning" (how indexes turn full scans into B-tree lookups): https://www.sqlite.org/queryplanner.html (checked 2026-11-06)
- Nagle's algorithm and its interaction with delayed ACK: https://en.wikipedia.org/wiki/Nagle%27s_algorithm (checked 2026-11-06)
- Red Hat, "Reducing the TCP Delayed ACK Timeout" (Linux delayed ACK behavior): https://docs.redhat.com/en/documentation/red_hat_enterprise_linux_for_real_time/7/html/tuning_guide/Reducing_the_TCP_delayed_ack_timeout (checked 2026-11-06)
- Python `socketserver.StreamRequestHandler.disable_nagle_algorithm`: a class attribute in CPython's `socketserver.py` (it sets `TCP_NODELAY`); it isn't listed in the official docs, so the lab relies on the source.
- Lab: `code/read_path_lab.py`, run 2026-11-06 (Python 3.13.18, SQLite 3.53.1, 2-core Linux container). Hit rates are from a simulated Zipf workload, not real traffic.
- Latency and capacity planning numbers marked "assumption" are rounded planning values, not measurements.
