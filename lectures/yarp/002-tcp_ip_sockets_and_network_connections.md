# Lecture 2: TCP, IP, Sockets, and Network Connections

Series: YARP Learning Series
Builds on: [Lecture 1 — HTTP: From the Wire to the Application](001-http_from_the_wire_to_the_application.md), particularly §2 (prerequisite transport concepts), §5 (the request lifecycle), and §10.2–10.4 (connection reuse, timeouts, cancellation).
Prepares you for: reading YARP's socket/connection-handling code (`SocketsHttpHandler` configuration, connection pooling, Kestrel's transport layer) and reasoning about why connection-level bugs in a proxy look completely different from application-level bugs.

---

## 1. Learning Objectives

By the end of this lecture you should be able to:

1. Name the layer (IP, TCP, HTTP, application) responsible for any given piece of behavior — "who's job is this?" should have a confident, specific answer.
2. Explain the difference between a TCP **connection** and an HTTP **request**, and give a concrete example where one connection carries many requests.
3. Explain what a socket is as an OS-level object, and how an application's calls (`connect`, `send`, `recv`, `close`) map onto TCP's actual behavior on the wire.
4. Explain, mechanically, what happens during connection establishment, data transfer (with loss/retransmission), and connection teardown.
5. Explain flow control and congestion control as two *different* problems TCP solves, and why both matter.
6. Diagnose, at a conceptual level, what's actually happening when: a server is unreachable, a connection resets, a connection hangs, or a client disappears mid-request.
7. Explain concretely why a reverse proxy has *two independent* connection lifecycles to manage for every logical request, and why that doubles (not just duplicates) its operational concerns.

---

## 2. Prerequisite Concepts

You've already got HTTP conceptually, and Lecture 1 §2 gave you a fast preview of IP/ports/sockets/TCP/UDP/TLS just deep enough to understand HTTP versions. This lecture is that preview, expanded into the real thing — so you'll see some of the same vocabulary again, but this time we go one layer deeper and actually stay there. If a term feels totally new, it's genuinely new; if it feels familiar, that's Lecture 1 doing its job as groundwork.

One habit worth adopting for this whole lecture: whenever I describe a behavior, ask yourself "is this something the *application* decided, or something that just happens automatically once you open a connection?" That question is the throughline of this entire lecture, and it's the exact question you'll need to answer when reading unfamiliar networking code in YARP or anywhere else.

---

## 3. Core Mental Model

Here's the layered stack you gave me, and it's the right one to memorize exactly as-is:

```
   Application            <- your code: "get me /v1/users/42"
        │
        ▼
       HTTP                <- message FORMAT: methods, headers, status, body
        │
        ▼
   TCP  /  QUIC             <- reliable delivery of bytes (or streams of bytes)
        │
        ▼
        IP                  <- addressing + routing: get this packet to that machine
        │
        ▼
  Network interface          <- actually putting electrical/radio/optical signals
   (Ethernet, Wi-Fi)            on the wire/air
```

The single most important idea in this lecture: **each layer solves exactly one problem and hands a clean abstraction to the layer above it, deliberately knowing nothing about the layers above.** IP doesn't know what a "port" is. TCP doesn't know what a "header" is. HTTP doesn't know what a "packet" is. This isn't an accident or a limitation — it's the entire design philosophy (called "separation of concerns" if you want the formal name), and it's *why* you can swap HTTP's transport from TCP to QUIC (Lecture 1 §8) without HTTP itself changing at all: the layer above never had to know the details of the layer below in the first place.

Read the stack **downward** to understand how a request gets sent, and **upward** to understand how a response gets received and interpreted. You'll do both directions constantly once you're reading real networking code.

---

## 4. IP — Addressing and Routing

### 4.1 What IP is actually responsible for

IP's (Internet Protocol) entire job: **given a destination address, get this packet of bytes closer to that destination, one hop at a time, with no guarantees.** That's it. IP does not guarantee delivery, does not guarantee order, does not retransmit lost packets, and does not know or care whether the data it's carrying makes any sense. It's often called a "best-effort" protocol for exactly this reason. Every guarantee you're used to relying on (arrives, arrives in order, arrives exactly once) is something TCP builds *on top of* IP — IP itself provides none of it.

### 4.2 IP addresses

An IP address identifies a machine (technically, a network interface on a machine) on a network.

**IPv4**: 32-bit addresses, written as four decimal octets: `142.250.80.14`. There are only ~4.3 billion possible IPv4 addresses — and the internet ran out of easily-allocatable ones years ago, which is a major reason IPv6 and techniques like NAT (below) exist.

**IPv6**: 128-bit addresses, written as eight groups of hex digits: `2001:0db8:85a3:0000:0000:8a2e:0370:7334` (commonly abbreviated, e.g. `2001:db8:85a3::8a2e:370:7334`, where `::` means "the rest is zeros"). The address space is astronomically larger — the actual motivation is running out of IPv4 addresses, not "faster" or "better" routing. For this series, you mainly need to *recognize* an IPv6 address when you see one in logs or config; you don't need to master its full addressing rules.

### 4.3 localhost, private, and public addresses

- **`127.0.0.1` (localhost / loopback)**: a special address that always means "this same machine," and packets sent to it never actually touch a physical network interface — the OS loops them straight back internally. Useful for local development (e.g., YARP running locally, forwarding to a backend also running locally on `127.0.0.1:5001`).
- **Private addresses**: ranges reserved for use *inside* private networks (e.g., `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`) — not globally routable on the public internet. Your home Wi-Fi router almost certainly hands your laptop something like `192.168.1.42`. Inside a cloud VPC, your servers typically have private addresses like `10.0.4.15` and talk to each other directly using them — this is exactly the kind of address YARP would use to reach a backend sitting in the same private network.
- **Public addresses**: globally unique, globally routable addresses — what the rest of the internet actually uses to reach your service. A **NAT (Network Address Translation)** device (your home router, or a cloud load balancer) is what maps a public address to a private one behind it, so many private-address machines can share one public-facing identity.

Concretely, in the running example from Lecture 1: `api.contoso.com` resolves via DNS to some public IP — but that public IP might belong to a load balancer or YARP instance sitting at the network edge, which then forwards to backend servers reachable only by their private IPs, invisible from outside. This is an extremely common real-world topology, and it's worth internalizing now because it explains why "the backend's IP address" and "the address a client used to reach your service" are very often two completely different addresses.

### 4.4 Routing, conceptually

You don't need to understand routing protocols (BGP, OSPF, etc.) for this series — but you should have the right mental model: IP routing is **not** "compute the whole path up front." Each router along the way only knows "for this destination address, send it out *this* direction, to the next router" — a purely local, hop-by-hop decision, repeated independently by every router the packet passes through until it arrives. No single router (and no sender) knows or controls the entire path. This is precisely why packets can arrive out of order, or take different paths on different attempts, or get dropped by any single overloaded hop along the way — and it's exactly why TCP (next section) has to actively compensate for exactly that unpredictability.

```
   Sender                                                    Destination
     │                                                             ▲
     │  "get this closer to 203.0.113.10"                          │
     ▼                                                             │
  [Router A] ──"my best next hop for that dest is Router B"──> [Router B] ──> ... ──> [Router N]
     
   Each router only knows ITS next hop. No end-to-end path is pre-computed or guaranteed.
```

---

## 5. Ports

### 5.1 What a port is, and why servers listen on one

IP gets a packet to the right *machine*. But a machine typically runs many programs that all want to send/receive network traffic simultaneously — a web server, an SSH daemon, a database, your IDE's debugger. A **port** (a 16-bit number, 0–65535) is how the OS distinguishes "which program on this machine does this packet belong to."

A server **listens** on a specific, known port — e.g., a web server listens on 443 (HTTPS) or 80 (HTTP) — meaning it has told the OS "any incoming connection attempt aimed at this port is mine; hand it to me." This is a *deliberate, fixed* choice so clients know where to find it. `api.contoso.com:443` fully identifies "this machine, this program" — the address gets you to the machine, the port gets you to the specific listening program.

### 5.2 Client-side ephemeral ports

Here's the part people often miss: **the client also uses a port**, even though nobody configured it and you never think about it. When your app connects out to `api.contoso.com:443`, the OS automatically assigns your side of that connection a temporary, essentially-random port from a range called **ephemeral ports** (commonly in the 32768–65535 range, OS-dependent) — say, `54217`. You never chose `54217`; the OS picked it purely so this connection has a unique local identity.

**Why this matters**: a TCP connection is actually identified by a **4-tuple**: `(source IP, source port, destination IP, destination port)`. This is what lets a single client machine have *many simultaneous connections to the same server* without them getting confused with each other — each one gets a different ephemeral source port, so each 4-tuple is unique even though the destination IP and port are identical every time.

```
Client machine (192.168.1.42)                    Server (203.0.113.10:443)

  connection 1: (192.168.1.42:54217 -> 203.0.113.10:443)   ─┐
  connection 2: (192.168.1.42:54218 -> 203.0.113.10:443)   ─┼─  all distinct connections,
  connection 3: (192.168.1.42:54219 -> 203.0.113.10:443)   ─┘   distinguished ONLY by
                                                                 the client's ephemeral port
```

### 5.3 Port conflicts and exhaustion

Two related, very real operational problems:

**Bind conflict**: only one program on a machine can *listen* on a given port at a time. If you try to start a second server on a port that's already bound, you get an immediate error (`Address already in use` / `EADDRINUSE`). This is why restarting a server sometimes fails right after stopping it — the OS may hold the port briefly in a `TIME_WAIT` state (below) even after the listening process exits.

**Ephemeral port exhaustion**: since there are only ~28,000–64,000 usable ephemeral ports (and each closed connection lingers briefly in `TIME_WAIT`, tying its port up for a short period even after it's "done"), a machine that opens an enormous number of short-lived outbound connections *to the same destination* can actually run out of available (source port, destination) combinations. This is a real, well-documented production failure mode — and it's a direct, concrete reason connection *reuse* (Lecture 1 §10.2) isn't just a performance nicety, it's sometimes the difference between a proxy functioning and a proxy failing outright under load. Hold onto this fact; it comes back explicitly in §12.

---

## 6. TCP

### 6.1 What TCP adds on top of IP

Recall §4.1: IP is best-effort — no ordering, no reliability, no retransmission guarantees. TCP's entire purpose is to build a **reliable, ordered, byte-stream** abstraction on top of that unreliable foundation, between two specific ports on two specific machines. From the application's point of view, once a TCP connection is established, it looks like a simple, dependable pipe: bytes go in one end, in order, and (barring an actual failure) exactly those bytes come out the other end, in the same order, exactly once.

### 6.2 Connection establishment — the three-way handshake, in full

You saw the outline in Lecture 1 §2.2. Here's the mechanism with enough detail to actually reason about it:

```
Client                                                    Server
  │                                                          │
  │──── SYN, seq=1000 ─────────────────────────────────────>│   "I want to talk. My starting
  │                                                          │    sequence number is 1000."
  │<─── SYN-ACK, seq=5000, ack=1001 ─────────────────────────│   "OK. My starting sequence
  │                                                          │    number is 5000. I've received
  │                                                          │    your byte 1000, expecting 1001 next."
  │──── ACK, ack=5001 ──────────────────────────────────────>│   "Confirmed. Expecting your
  │                                                          │    byte 5001 next."
  │                                                          │
  │      Connection is now ESTABLISHED. Data can flow.       │
```

Each side picks its own starting **sequence number** (not zero, for security/robustness reasons you don't need to dig into) and every subsequent byte sent increments it. The `ack` field is the receiver continuously telling the sender "here's the next byte number I expect" — which is simultaneously an acknowledgment of everything received so far. This three-way exchange costs exactly **one full round trip** before the *client's* first real data can even be sent (the client's data can technically ride along with that third ACK packet, but conceptually: one RTT of pure overhead before useful work starts). This is precisely the cost Lecture 1 §2.2 and §8.4 referenced.

### 6.3 Reliable delivery and ordering

Every byte sent gets a sequence number. The receiver acknowledges what it has received. If the sender doesn't get an ACK within an expected time window, it assumes the data was lost and **retransmits** it. If data arrives out of order (because IP routing, §4.4, made no ordering promise), the receiving TCP stack buffers it and only hands bytes up to the application **in the correct order** — it will hold onto byte 5002 until byte 5001 shows up, even if 5002 physically arrived first. This is the exact mechanism behind "TCP head-of-line blocking" from Lecture 1 §8.1 — now you can see precisely *why* it happens: the receiving stack is enforcing strict ordering by design, and it cannot hand anything to the application out of order, even if doing so would otherwise be fine.

```
Packets arrive at the receiver in this order:  [seq 5002][seq 5001][seq 5003]
                                                    ▲
                                    TCP HOLDS this — won't deliver it to
                                    the application — until 5001 arrives,
                                    even though it's already sitting in
                                    the receive buffer.

Once 5001 arrives:  the stack delivers 5001, 5002, 5003 to the application,
                     in that order, as if nothing unusual happened.
```

### 6.4 Flow control — protecting the *receiver*

Flow control answers: **"how much data can the sender send before the receiver has had a chance to process what's already been sent?"** Every TCP receiver advertises a **receive window** — "I have room for N more bytes right now" — and the sender is not allowed to send more than that without waiting. This exists so a fast sender can't overwhelm a slow receiver's buffer (imagine a powerful server streaming data to a receiver on a phone with a small buffer and a slow CPU — without flow control, the server could blast data faster than the phone could ever consume it, and the extra data would simply be dropped). This window is dynamically renegotiated continuously as the connection progresses — it's not a one-time setting.

### 6.5 Congestion control — protecting the *network*

This is a different problem from flow control, and it's worth keeping the two mentally separate:

- **Flow control**: is the *receiver* able to keep up?
- **Congestion control**: is the *network path in between* able to keep up?

TCP doesn't know the network's actual capacity ahead of time, so it **probes for it**, conceptually like this (the real algorithms — slow start, congestion avoidance, etc. — are more nuanced, but this is the right depth for this series):

1. Start sending cautiously (a small number of packets).
2. If they all arrive successfully (acknowledged), increase the sending rate.
3. Keep increasing... until packet loss is detected.
4. Packet loss is treated as a *signal* — "the network is congested, back off" — so the sender sharply reduces its rate, then cautiously starts probing upward again.

```
sending rate
    │                              ╱╲
    │                          ╱╲ ╱  ╲
    │                      ╱╲ ╱  X    ╲___
    │                  ╱╲ ╱  X                <- loss detected, back off sharply,
    │              ╱╲ ╱  X                       then cautiously ramp up again
    │          ╱╲ ╱
    │      ╱╲ ╱
    │  ╱╲ ╱
    └──────────────────────────────────────────► time
```

**Why this matters practically**: this is exactly why a *brand new* TCP connection is slower to reach full speed than a long-lived, already-"warmed-up" one — it has to re-run this probing process from scratch. A long-lived, reused connection (Lecture 1 §10.2) isn't just saving you a handshake — it's also already operating at its learned, efficient sending rate, while a fresh connection has to earn that rate all over again. This is a second, distinct, often-overlooked reason connection reuse matters for a proxy's throughput, on top of the handshake-cost argument you already know.

### 6.6 Connection termination

TCP connections close via a **four-way handshake** (each side closes its own direction independently, since TCP connections are technically full-duplex — two independent byte streams, one each direction):

```
Client                                                    Server
  │──── FIN ────────────────────────────────────────────────>│   "I'm done sending."
  │<─── ACK ─────────────────────────────────────────────────│   "Acknowledged."
  │                                                            │
  │<─── FIN ────────────────────────────────────────────────  │   "I'm done sending too."
  │──── ACK ────────────────────────────────────────────────>│   "Acknowledged."
  │                                                            │
  │   Client now waits in TIME_WAIT for a short period          │
  │   (to handle any last stray/delayed packets) before          │
  │   fully releasing the port for reuse.                        │
```

That lingering `TIME_WAIT` state is exactly what's behind the ephemeral-port-exhaustion problem from §5.3 — a connection that has "closed" from the application's point of view isn't instantly gone from the OS's point of view.

Connections can also end **abruptly**, via a `RST` (reset) packet instead of a graceful FIN exchange — this happens when one side encounters an error state it can't cleanly recover from (e.g., data arrives for a connection the OS no longer has any record of, or an application crashes without closing sockets properly). A `RST` is a hard stop, not a negotiated goodbye — no more data should be expected after it, and any data already "sent but not yet acknowledged" from the resetting side is simply lost. I'll come back to this concretely in §10.

---

## 7. Sockets

### 7.1 What a socket represents

A **socket** is the operating system's handle representing one endpoint of a network connection (or, before connecting, a "not yet connected" endpoint ready to connect or listen). It's the thing your application code actually holds and calls methods on — you don't manipulate TCP sequence numbers or IP headers directly; you call `connect()`, `send()`, `recv()`, `close()` on a socket, and the OS's networking stack does everything described in §4–§6 underneath that call, invisibly.

Think of it as analogous to a file handle: opening a file gives you a handle you read/write through without personally managing disk blocks — a socket gives you a handle you read/write through without personally managing packets, sequence numbers, or acknowledgments.

### 7.2 The relationship, explicitly

```
   Application         <- your code: httpClient.GetAsync(...), or raw socket calls
        │
        ▼
     Socket              <- OS-level handle/API: connect(), send(), recv(), close()
        │
        ▼
      TCP                <- kernel's TCP state machine for THIS socket: sequence
        │                    numbers, retransmission, flow/congestion control
        ▼
       IP                <- kernel's routing/addressing for outgoing/incoming packets
        │
        ▼
Network interface          <- actual hardware transmission
```

When you write `socket.Send(bytes)` in application code, you're not "sending bytes over the network" directly — you're handing bytes to the kernel's TCP implementation, which buffers them, breaks them into segments, assigns sequence numbers, and manages retransmission/flow/congestion entirely on its own, asynchronously from your application's perspective. Your `Send()` call typically returns as soon as the kernel has *accepted* the bytes into its own send buffer — not when they've actually arrived at the destination. This gap (application thinks "sent," but the data might still be in flight, retrying, or even lost and about to be retransmitted) is a genuinely important thing to hold in your head, because it explains a lot of confusing failure behavior later (§10).

### 7.3 What "listening" actually means, mechanically

A server calls something like `bind()` (claim a port) then `listen()` (say "I'm ready to accept incoming connection attempts on this port") then `accept()` in a loop. Each time a client completes a three-way handshake (§6.2) against that listening socket, the OS hands the server application a **brand new socket**, specific to that one client connection — the original listening socket keeps listening for the *next* new connection. This is why a busy server can be simultaneously handling thousands of individual client connections: each one is its own distinct socket with its own TCP state, even though they all originated from the same `listen()`ing port.

```
                    ┌── listening socket on :443 ── waits for new connections forever
                    │
   client A connects ──► NEW socket #1  (this one talks ONLY to client A)
   client B connects ──► NEW socket #2  (this one talks ONLY to client B)
   client C connects ──► NEW socket #3  (this one talks ONLY to client C)
```

---

## 8. Connections vs. Requests — Why One TCP Connection ≠ One HTTP Request

This is the section you flagged as extremely important, and it deserves to be stated as bluntly as possible:

> **A TCP connection is a pipe. HTTP requests are things that travel through that pipe. The pipe does not know or care how many things travel through it, and — as of HTTP/1.1's persistent connections and especially HTTP/2's multiplexing — the answer is very often "many."**

### 8.1 Concretely, in HTTP/1.1

```
ONE TCP connection, THREE HTTP/1.1 requests, sequentially, reusing the same connection:

  Client                                          Server
    │══════ TCP handshake (once) ═══════════════════│
    │                                                │
    │──── GET /v1/users/42 ────────────────────────>│
    │<─────────── 200 OK, user JSON ──────────────────│
    │                                                │
    │──── GET /v1/users/42/orders ─────────────────>│
    │<─────────── 200 OK, orders JSON ─────────────────│
    │                                                │
    │──── POST /v1/users/42/orders ────────────────>│
    │<─────────── 201 Created ─────────────────────────│
    │                                                │
    │══════ (connection eventually closes, or is reused
    │        for a 4th request, or sits idle waiting) ══│
```

One handshake. Three completely independent, sequential HTTP requests. From TCP's point of view, this is just one continuous stream of bytes — it has no concept of "request boundaries" at all; that concept exists entirely at the HTTP layer, which parses the byte stream into discrete messages (Lecture 1 §4.3's raw-message format is literally how the HTTP layer knows where one request ends and the next begins within that single continuous TCP stream).

### 8.2 Concretely, in HTTP/2

Recall Lecture 1 §7.2 — HTTP/2 multiplexes many *concurrent* streams over one connection, not just sequential ones:

```
ONE TCP connection, interleaved concurrently — still just ONE connection:

  Client                                                    Server
    │══════ TCP handshake (once) ═══════════════════════════│
    │                                                        │
    │── stream 1: GET /v1/users/42 ─────────────────────────>│
    │── stream 3: GET /v1/products ─────────────────────────>│
    │── stream 5: GET /v1/notifications ────────────────────>│
    │<───────── stream 3 response (fast) ───────────────────── │
    │<───────── stream 5 response ──────────────────────────── │
    │<───────── stream 1 response (was slower) ────────────────│
```

Three concurrent HTTP requests, one TCP connection, interleaved arbitrarily. If you were only thinking at the TCP layer, you'd see "one connection, some bytes went back and forth" — you would have **no way to know**, without also understanding HTTP/2 framing, that three independent logical requests were involved at all.

### 8.3 Why this distinction is the single most important thing in this lecture for reading YARP

YARP code (and any proxy or load balancer) constantly has to reason about **connections** and **requests** as two separate, independently-scoped things — with independent lifecycles:

- A single backend **connection** might be actively carrying (or have carried) many different clients' **requests** over its lifetime (via pooling/reuse), especially under HTTP/1.1 keep-alive or HTTP/2 multiplexing.
- A connection can be healthy while a specific request on it fails (e.g., an HTTP/2 stream gets reset via `RST_STREAM`, per Lecture 1 §7.3, without the underlying connection closing).
- Conversely, a connection can die (network failure, timeout, reset) while a request was mid-flight on it — and that failure needs to be attributed to *the request that was using it*, not treated as "the whole proxy is down."
- Connection-level configuration (pool size, idle timeout, max lifetime) and request-level configuration (per-request timeout, retry policy) are **different knobs governing different things**, and conflating them is a common source of confusing proxy misconfiguration.

If you only ever think "a request = a connection," code that manages connection pools, multiplexed streams, and per-request cancellation independently will look arbitrary and confusing. Once you see them as genuinely separate concepts with separate lifecycles — which is exactly what this section demonstrated concretely — that code becomes legible.

---

## 9. TCP Performance

Quick, connected-together recap of terms you'll constantly see in this context — each tied to a mechanism you now actually understand, not just a word:

- **Latency**: dominated, at the TCP level, by the number of round trips required — handshake (§6.2, 1 RTT), plus however many round trips your actual data exchange needs, plus TLS on top if applicable (Lecture 1 §2.4).
- **Round trips**: the fundamental "unit of slowness" in networked systems — physics (the speed of light through fiber, plus real-world routing hops) puts a hard floor under how fast one round trip can be between two distant points, no amount of software optimization changes that floor; the entire game is *minimizing how many round trips you need*, not making an individual one instantaneous.
- **Bandwidth**: the maximum raw bit-rate of the link, as defined in Lecture 1 §10.1 — TCP's congestion control (§6.5) is precisely the mechanism trying to use as much of that bandwidth as possible *without* overwhelming the path.
- **Congestion**: what happens when demand on a network path exceeds its capacity — manifests as increased latency (queuing at routers) and eventually packet loss (queues overflow and get dropped) — this is the condition congestion control (§6.5) is actively trying to detect and back off from.
- **Packet loss**: individual packets never arriving — triggers TCP's retransmission (§6.3) and is *interpreted* by congestion control (§6.5) as a signal to slow down, meaning loss has a compounding cost: not just "resend this one packet" but "also now send everything more cautiously for a while."
- **Connection setup cost**: the handshake RTT (§6.2), plus TLS RTTs if applicable, paid *before* any application data can flow — a fixed tax on every new connection, completely independent of how much data you actually intend to send over it.
- **Connection reuse**: avoids paying that setup cost repeatedly, *and* (per §6.5) avoids re-running congestion control's slow-start ramp-up from scratch — a reused connection is both cheaper to start using and faster once you're using it, which is why it's such a heavily emphasized theme across this whole series.

---

## 10. Failure — What Actually Happens

This is where understanding the mechanism (not just the vocabulary) pays off directly — each of these produces a *specific, different* observable behavior, and being able to tell them apart is a real diagnostic skill.

### 10.1 The server disappears (machine is off / unreachable)

There's no server to even respond with a `RST` — packets just go unanswered. The client's TCP stack retransmits the initial SYN a few times (§6.2/§6.3), with increasing delays between attempts, and eventually gives up and reports a **connection timeout** to the application. This is typically the *slowest* failure to detect, because the client has no signal that anything is wrong — it can only infer failure from *silence*, and silence takes time to be confident about.

### 10.2 The network disappears (cable unplugged / Wi-Fi drops) mid-connection

Similar to §10.1 but mid-conversation instead of at setup: in-flight packets simply vanish, retransmissions go unanswered, and eventually the sending side times out. Neither side gets an explicit "goodbye" — both sides just eventually conclude, independently and only after a timeout, that the connection is dead.

### 10.3 Packets are lost (but the path itself is fine)

Handled transparently by TCP's retransmission (§6.3) — the application usually never even finds out this happened, beyond a small latency hit (and, per §6.5, a temporary congestion-control slowdown). This is the *expected, routine* case TCP was built to absorb invisibly — it's not really a "failure" from the application's perspective at all, which is worth appreciating: TCP is doing a huge amount of invisible cleanup work on your behalf, constantly.

### 10.4 The server stops responding (process hung, but the connection itself is fine)

This is a subtle and important one to distinguish from the above: the TCP connection can be completely healthy (both sides' TCP stacks are fine, ACKs flow normally if there's any TCP-level traffic like keepalives) while the *application* on the server side is simply stuck — deadlocked, in an infinite loop, waiting on some other hung resource. From the client's point of view, this looks like: the request was sent successfully, and then... nothing. No error, no response, just silence — indistinguishable, from the client's perspective, from "still legitimately working on it." **This is exactly why request-level timeouts (Lecture 1 §10.3) must exist independently of TCP itself** — TCP has no idea the application is stuck; TCP's job stopped at "delivered your bytes to the other side," and it did that successfully. Only a timeout set by the *application* (or the proxy) can catch this case.

### 10.5 The connection is reset

An explicit `RST` (§6.6) arrives — this is actually the *fastest and clearest* failure signal, because it's an unambiguous message rather than silence. Common causes: the listening application isn't actually running on that port anymore (nothing to accept the connection), the receiving OS has no record of this connection anymore (e.g., the server process crashed and a new one started, or the connection was idle so long an intermediate device like a load balancer or NAT dropped its tracking state for it), or the application explicitly aborted the connection. The application sees this immediately as a clear "connection reset" error — no ambiguous waiting required.

### 10.6 The client disconnects (mid-request, from the server's point of view)

The server may or may not notice quickly, depending on whether it's actively trying to write to the socket at that moment (a write to a socket whose peer is gone will eventually fail/reset) or just idly waiting to read more (which might not fail immediately — this is part of why "detect that the client left" is a real, nontrivial engineering problem, not an automatic given). This connects directly to Lecture 1 §10.4 (cancellation) and §13's "partial write" failure scenario — if the server doesn't actively check for this, it can keep doing wasted work for a client that's no longer there to receive the result.

### 10.7 Summary table — how to tell these apart

| Scenario | Client-observed signal | Typical detection speed |
|---|---|---|
| Server machine unreachable | timeout (no response at all to SYN) | slow (multiple retry intervals) |
| Network path down mid-connection | timeout (no response to in-flight data) | slow |
| Ordinary packet loss | invisible — handled transparently | none needed, self-healing |
| Server process hung, connection fine | timeout (connection open, but no application response) | as slow as your configured timeout allows |
| Connection reset | immediate, explicit error | fast |
| Client disconnected | server-side error on next write attempt, or nothing at all if server never tries to write/read | variable, sometimes never without active checks |

---

## 11. Common Misconceptions

- **"If `send()` returned successfully, the data arrived at the other end."** No — it means the kernel accepted the bytes into its own send buffer (§7.2). The data could still be lost and awaiting retransmission, or the connection could fail moments later before delivery completes.
- **"A slow response means the network is slow."** Not necessarily — §10.4 shows a perfectly healthy, fast network can be carrying a request to a server whose *application* is simply stuck. Network health and application health are independent things that both happen to sit on the same connection.
- **"One connection = one request, so if I see one connection open, exactly one thing is happening on it."** Directly contradicted by §8 — with keep-alive or HTTP/2, one connection can carry (sequentially or concurrently) many independent requests.
- **"Closing a TCP connection is instant."** No — the four-way close (§6.6) plus `TIME_WAIT` means a "closed" connection can linger, holding resources (notably, a port) for a real, measurable period afterward.
- **"Congestion control and flow control are the same thing."** They solve different problems (network capacity vs. receiver capacity, §6.4 vs §6.5) and can each independently limit throughput — you can have a fast, willing receiver throttled by network congestion, or a slow receiver throttling a wide-open network path.
- **"IP addresses and ports are basically the same kind of thing, at different granularity."** Not quite — an IP address identifies a *machine* (routing concern, §4); a port identifies a *program on that machine* (multiplexing concern, §5) — genuinely different layers solving genuinely different problems, which is exactly why they're specified independently as `(IP, port)` pairs everywhere you'll see them in networking code.

---

## 12. Production Perspective: 10 → 10,000 → 1,000,000 → 100,000,000 Connections

**~10 concurrent connections**: everything in this lecture is invisible in practice. Ephemeral port exhaustion (§5.3) is not a concept you'd ever encounter. A handful of TCP connections opening and closing costs nothing measurable.

**~10,000 concurrent connections**: the OS's per-process file descriptor limits (each open socket consumes one) start to matter and often need explicit tuning (`ulimit` and equivalents). `TIME_WAIT` accumulation (§6.6) from short-lived connections can start showing up in monitoring, even if it's not yet causing outright failures. This is roughly the scale where "just let the OS defaults handle it" stops being safely true.

**~1,000,000 concurrent connections**: ephemeral port exhaustion (§5.3) becomes a genuine, documented production risk, especially for any component (like a proxy) making a large number of *outbound* connections to a *small* number of backend destinations — because remember, a 4-tuple needs to be unique, and with a fixed destination IP/port, the client's ephemeral port range is the only thing providing that uniqueness, and it's a finite, shared resource. This is exactly the scale where connection pooling (§6.5, §8.3) stops being "best practice" and becomes "the only way the system stays up." Congestion control's slow-start penalty on fresh connections (§6.5) becomes a measurable aggregate latency cost when it's happening constantly instead of rarely.

**~100,000,000 concurrent connections**: this is the scale of large CDNs and edge proxy fleets. Connection state itself (all those open sockets, their TCP buffers, their congestion-control state) becomes a first-class capacity-planning concern, not just an implementation detail — engineering teams actively track and budget for it. QUIC's per-stream independence (§13) becomes operationally significant specifically because, at this scale, "many users on lossy mobile networks" isn't an edge case, it's a large fraction of total traffic, all the time — so a transport-level improvement that only matters "sometimes" at smaller scale matters *constantly* here.

---

## 13. QUIC — Just Enough to Understand HTTP/3's Behavior

You already got the "why" in Lecture 1 §8 — here's the minimum mechanical grounding to make that "why" solid, without going further than this series needs.

QUIC is a transport protocol, like TCP, but:

- It runs over **UDP** (§ — recall UDP itself provides no ordering/reliability guarantees at all; it's a nearly blank slate, per Lecture 1 §2.3) rather than being a kernel-level protocol like TCP.
- It **reimplements**, itself, the things TCP normally gives you: reliable delivery, ordering, retransmission, flow control, congestion control — all the mechanisms from §6 of this lecture — but does so **per-stream**, not connection-wide.
- Because ordering/retransmission is tracked per-stream instead of as one single byte sequence for the whole connection, **loss of a packet belonging to stream A does not block delivery of already-arrived data belonging to stream B** — this is the exact fix for the TCP-level head-of-line blocking problem from Lecture 1 §8.1, now visible mechanically: TCP enforces one global ordered byte stream (§6.3) with no concept of independent sub-streams; QUIC was designed, from the ground up, specifically to *have* that concept.
- It bundles the transport handshake and the TLS handshake into one combined negotiation (rather than TCP's handshake, then a separate TLS handshake stacked on top), which is why QUIC connections typically establish faster than the equivalent TCP+TLS combination (Lecture 1 §8.4).

That's the right depth for this series — you do not need QUIC's actual wire format, its specific loss-detection algorithm, or its congestion-control variant (per Lecture 1 §16, this stays explicitly deferred).

---

## 14. Performance Implications

- **Reuse connections whenever the destination is fixed and repeated** (§6.5, §8.3, §12) — this is the highest-leverage networking-level optimization available to anything that talks to the same backend repeatedly, which describes a reverse proxy almost by definition.
- **Budget for ephemeral port and file descriptor limits explicitly** once you're operating at meaningful connection concurrency (§5.3, §12) — these are not abstract concerns, they are concrete OS-level ceilings that real systems hit.
- **Distinguish connection-level health from request-level health** in any monitoring/alerting you design or read (§8.3, §10.7) — "the connection is fine" and "the request succeeded" are different facts, and conflating them produces confusing incident investigations.
- **Set explicit application-level timeouts; never rely on TCP alone to detect a hung peer** (§10.4) — TCP's job ends at "delivered your bytes"; it has no opinion about whether the application on the other end is actually doing anything with them.
- Deep congestion-control tuning, custom retransmission strategies, and kernel-level socket buffer tuning are **not** where your effort belongs at this stage (per §15) — these are handled by the OS/runtime, and are specialist territory even for experienced infrastructure engineers.

---

## 15. YARP Connection

### 15.1 Why a proxy must actively care about connections, not just requests

Recall Lecture 1 §15.1: a reverse proxy is simultaneously an HTTP server (to the client) and an HTTP client (to the backend), for the same logical request. Now, with this lecture's vocabulary, state that more precisely: **a reverse proxy manages two entirely independent TCP (or QUIC) connection lifecycles for every logical request it handles — an inbound one it did not choose to open, and an outbound one it must choose to open (or reuse) itself.** Everything from §6 through §10 of this lecture applies *separately* to each side.

### 15.2 Concrete things YARP has to actively manage, per topic from this lecture

**Incoming connections**: YARP (via Kestrel, its underlying server) accepts inbound TCP/QUIC connections from potentially many thousands of clients simultaneously — each one its own socket (§7.3), each one independently going through handshake, data transfer, and eventually termination (§6.2, §6.6), completely outside YARP's control in terms of *when* a client decides to connect or disconnect.

**Outgoing connections**: for each incoming request, YARP must have (or establish) an outbound connection to the chosen backend. This is where §6.5's congestion-control-ramp-up point and §5.3's ephemeral-port-exhaustion point become directly operational: opening a fresh backend connection per request, at any real scale, is exactly the failure mode described in §12's "1,000,000 connections" tier — a proxy is one of the most common real-world things that actually hits ephemeral port exhaustion, precisely because it's structurally a many-inbound-connections-funneling-into-comparatively-few-backend-destinations system.

**Connection reuse**: YARP maintains **pools** of already-established outbound connections per backend destination, specifically to avoid re-paying handshake cost (§6.2) and congestion-control ramp-up (§6.5) on every single request, and to avoid ephemeral port exhaustion (§5.3) under sustained load. This is not an optional performance knob — per §12, it's close to a structural requirement at production scale.

**Timeouts**: because §10.4 showed that TCP alone cannot detect a hung backend application — only an explicit, application-level timeout can — YARP must apply its *own* timeouts to backend requests, independent of whatever timeout (if any) the original client is using. This is the mechanical justification behind Lecture 1 §10.3's claim that timeouts "compose" across hops: each hop needs its own, and they need to be set with awareness of each other.

**Cancellation**: per §10.6 and Lecture 1 §10.4 — if the client-side connection drops or is cancelled, YARP ideally propagates that cancellation to the outbound backend connection promptly, rather than continuing to wait on (or drive) a backend request nobody is waiting to receive anymore. Given §10.6's point that a server doesn't always notice a departed client automatically, YARP has to actively wire this up — it is not free.

**Network failures**: every failure mode in §10 can happen on *either* leg (client↔YARP or YARP↔backend), independently, and YARP has to translate a failure on the backend leg into a sensible HTTP-level response on the client leg — this is precisely where Lecture 1 §4.8's `502`/`503`/`504` status codes come from: they are YARP's way of expressing, in HTTP terms, a failure that actually happened at the TCP/connection layer described in this entire lecture. A `502 Bad Gateway`, for instance, is very often literally "I got a connection reset (§10.5) or connection refused talking to the backend."

### 15.3 The two-sided diagram

```
   Client                 network                  YARP                  network                 Backend
     │                        │                      │                       │                       │
     │──── TCP/QUIC conn ────>│───────conn───────────>│                       │                       │
     │        (leg 1: client ↔ YARP,                  │                       │                       │
     │         YARP did not choose when this           │                       │                       │
     │         opens or closes — the client did)        │                       │                       │
     │                                                  │                       │                       │
     │                                                  │────TCP/QUIC conn────>│──────conn────────────>│
     │                                                  │        (leg 2: YARP ↔ backend,                │
     │                                                  │         YARP DOES choose — opens,               │
     │                                                  │         reuses from a pool, or times out)        │
     │                                                  │                       │                       │
     │<═══════════════════ one HTTP request/response, logically ═══════════════════════════════════════>│
     │             flows across TWO independently-managed connection lifecycles                          │
```

YARP effectively participates in **two full copies of this entire lecture at once, simultaneously, for every request in flight**: two connection lifecycles, two sets of handshake/data-transfer/termination mechanics, two independent sets of failure modes (§10), and — crucially — the responsibility of translating whatever happens on the (invisible-to-the-client) backend leg into a coherent HTTP response on the (invisible-to-the-backend) client leg. That translation *is*, in large part, what a reverse proxy fundamentally is, once you strip away the HTTP-layer vocabulary from Lecture 1 and look purely at the connection mechanics underneath it.

---

## 16. What I Don't Need to Know Yet

- Specific congestion-control algorithm variants (Reno, CUBIC, BBR, etc.) — "TCP probes for capacity and backs off on loss" (§6.5) is sufficient depth here.
- IPv6 addressing/subnetting rules in detail — recognize the format (§4.2), nothing more, for now.
- Routing protocols (BGP, OSPF) — §4.4's hop-by-hop mental model is the right depth.
- NAT traversal techniques, STUN/TURN, or other peer-to-peer connectivity mechanisms — not relevant to a reverse proxy's server-side role.
- Raw socket programming details (setting individual socket options, buffer sizing tuning) beyond recognizing that they exist and that frameworks like Kestrel/`SocketsHttpHandler` manage most of this for you by default.
- QUIC's specific wire format or loss-recovery algorithm (per Lecture 1 §16 and §13 above — still deferred).
- Load balancing algorithms themselves — still explicitly deferred to a dedicated later lecture, per Lecture 1 §16.

---

## 17. Knowledge Check

1. A client has three tabs open, each making requests to `api.contoso.com`. Using the 4-tuple concept from §5.2, explain how the server's OS is able to tell these three tabs' traffic apart, given that all three share the same client machine and the same destination.
2. Explain why a freshly-opened TCP connection to a backend can be measurably slower for its first several requests than a connection that's been open and active for a while, using two *separate* mechanisms from this lecture (not just "handshake cost").
3. A monitoring dashboard shows a backend's TCP connection as "healthy" (no errors, no resets) but requests through it are timing out. Using §10.4, explain how both of those facts can be true simultaneously, and explain specifically why only an application-level (not TCP-level) mechanism can catch this.
4. A proxy is configured to open a brand-new outbound connection for every single incoming request, under heavy sustained load. Using §5.3 and §12, explain the specific failure mode this risks, and why "just add more backend servers" would not fix it.
5. Explain, using §8's distinction, why an HTTP/2 client can have "one request fail" while its underlying TCP connection remains completely fine — and why this would be much harder to express cleanly in HTTP/1.1.
6. Using §15.2, explain why a `504 Gateway Timeout` from YARP does not necessarily mean the *client's* connection to YARP had any problem at all.

---

## 18. Practical Exercise

Everything here runs locally on your Mac, no extra infrastructure required.

### Part A — See a real TCP connection's lifecycle with your own eyes

```bash
# Start a trivial local server (Python's built-in one is fine for this)
python3 -m http.server 8123
```

In another terminal, watch its connections while you hit it with curl:
```bash
# See the listening socket
lsof -iTCP:8123 -sTCP:LISTEN

# In a third terminal, make a request, then immediately check state
curl -s http://localhost:8123/ -o /dev/null
lsof -iTCP:8123
```
Try making several requests back-to-back and watch for `ESTABLISHED`, `TIME_WAIT`, and `CLOSE_WAIT` states appear in the `lsof`/`netstat -an` output — those are the exact states from §6.6's teardown sequence, made visible.

### Part B — Watch a connection get reused vs. re-established

```bash
# Force a NEW connection for every request (add explicit Connection: close)
curl -v -H "Connection: close" http://localhost:8123/ 2>&1 | grep -i "connect\|connection"
curl -v -H "Connection: close" http://localhost:8123/ 2>&1 | grep -i "connect\|connection"

# vs letting curl reuse a connection across multiple requests in one invocation
curl -v http://localhost:8123/ http://localhost:8123/ 2>&1 | grep -i "connect\|re-using"
```
Look for curl's own `* Re-using existing connection` message in the second case — that's connection reuse (§8.1) happening in front of you.

### Part C — Feel connection setup cost directly

```bash
# Time a request to something requiring a fresh TCP+TLS handshake each time
curl -w "\nDNS: %{time_namelookup}s | Connect: %{time_connect}s | TLS: %{time_appconnect}s | Total: %{time_total}s\n" \
  -o /dev/null -s https://example.com/
```
Run it a few times and compare `time_connect`/`time_appconnect` (handshake costs) against `time_total` — for a small response, handshake cost can be the *majority* of total time, which is exactly why §14's "reuse connections" recommendation has such outsized real-world impact.

### Part D — C#: see the socket-exhaustion footgun directly, then fix it

This is a famous, real-world .NET gotcha that is a direct, practical consequence of §5.3 (ephemeral port exhaustion) and §6.5 (connection reuse) — and it's exactly the class of bug a proxy author must never write.

```csharp
// THE BUG: a new HttpClient (and therefore a fresh underlying connection,
// not pooled/reused) is created and disposed on every call.
// Under load, this can exhaust ephemeral ports (§5.3) and/or pay full
// handshake + slow-start cost (§6.2, §6.5) on every single request.
async Task BadAsync()
{
    using var client = new HttpClient();
    await client.GetAsync("http://localhost:8123/");
}

// THE FIX: one long-lived HttpClient (or, better, IHttpClientFactory in
// ASP.NET Core) whose underlying SocketsHttpHandler pools and reuses
// connections across calls — exactly the connection-reuse behavior
// this whole lecture has been building toward.
static readonly HttpClient SharedClient = new HttpClient();

async Task GoodAsync()
{
    await SharedClient.GetAsync("http://localhost:8123/");
}
```

Run a tight loop (a few thousand iterations) of `BadAsync()` against your local Python server and watch `lsof -iTCP:8123 | wc -l` climb and connections pile up in `TIME_WAIT`; then do the same with `GoodAsync()` and watch it stay flat, reusing one connection. This is, quite literally, the mistake connection pooling exists to prevent — and it's the exact mechanism YARP's own backend `HttpClient` configuration is built around avoiding, at a much larger scale.

---

## 19. "Ready to Move On" Criteria

Before starting Lecture 3, you should be able to explain — out loud, in your own words:

- [ ] What job each layer (application, HTTP, TCP/QUIC, IP, network interface) does, and specifically what it does *not* know about the layers above or below it.
- [ ] What a 4-tuple is, and why it's what actually distinguishes simultaneous connections between the same two machines.
- [ ] The three-way handshake, well enough to say why it costs exactly one round trip before real data can flow.
- [ ] Why TCP enforces strict byte ordering, and how that specific behavior is the direct cause of TCP-level head-of-line blocking.
- [ ] The difference between flow control and congestion control — which problem each one solves.
- [ ] A concrete example of one TCP connection carrying multiple HTTP requests, and why that means "connection health" and "request success" are different facts.
- [ ] Why a request can time out even though the underlying TCP connection is completely healthy.
- [ ] Why ephemeral port exhaustion is a real risk specifically for proxies, and how connection pooling prevents it.
- [ ] Why YARP has to manage two independent connection lifecycles per request, and can name at least three specific consequences of that (from §15.2).

If any of these feel uncertain, revisit that section before moving forward — Lecture 3 will assume you can reason fluently about connections and requests as separate things, since that distinction underlies almost everything a reverse proxy does.
