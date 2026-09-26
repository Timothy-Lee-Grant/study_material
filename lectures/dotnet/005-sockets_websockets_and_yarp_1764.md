2026_09_26_15_48-(Sockets-WebSockets-And-YARP-1764)

# Lecture 005 — From Sockets to WebSockets to YARP: Understanding (and Solving) dotnet/yarp#1764

> **For:** Timothy Lee Grant
> **Date:** 2026-09-26
> **Prerequisites:** Lecture 001 (the Generic Host, async, `Channel<T>`), Lecture 004 §7 (file descriptors, syscalls, `epoll`). Your `lectures/yarp/` folder (001–012) covers HTTP, TCP, and reverse proxies from another angle. This lecture is the *working* version, aimed at one real issue.
>
> **Goal:** by the end you should be able to (1) explain, from the wire up, why an idle WebSocket through YARP dies after 100 seconds; (2) configure YARP's timeouts and HTTP client correctly; (3) reproduce the behavior on your own machine; and (4) make the documentation contribution that closes the issue.

---

## Table of Contents

- [0. The issue, and the map of what you need](#0-the-issue-and-the-map-of-what-you-need)
- [1. The layer cake: envelopes inside envelopes](#1-the-layer-cake-envelopes-inside-envelopes)
- [2. Sockets: what they are and the calls that drive them](#2-sockets-what-they-are-and-the-calls-that-drive-them)
- [3. The TCP handshake and teardown, byte by byte](#3-the-tcp-handshake-and-teardown-byte-by-byte)
- [4. TCP is a byte stream: the framing problem](#4-tcp-is-a-byte-stream-the-framing-problem)
- [5. Sockets in C#: a server and a client](#5-sockets-in-c-a-server-and-a-client)
- [6. TLS in one page](#6-tls-in-one-page)
- [7. HTTP on top of TCP, and the many kinds of "keep-alive"](#7-http-on-top-of-tcp-and-the-many-kinds-of-keep-alive)
- [8. WebSockets: the upgrade handshake, frames, pings](#8-websockets-the-upgrade-handshake-frames-pings)
- [9. Where YARP comes in: two connections and a copy loop](#9-where-yarp-comes-in-two-connections-and-a-copy-loop)
- [10. Configuring YARP: HttpClient, HttpRequest, timeouts](#10-configuring-yarp-httpclient-httprequest-timeouts)
- [11. The lab: reproduce the 100-second disconnect](#11-the-lab-reproduce-the-100-second-disconnect)
- [12. Solving #1764: the contribution plan](#12-solving-1764-the-contribution-plan)
- [13. Misconceptions to avoid](#13-misconceptions-to-avoid)
- [14. Interview relevance](#14-interview-relevance)
- [15. Self-check questions](#15-self-check-questions)
- [16. Sources](#16-sources)

---

## 0. The issue, and the map of what you need

### 0.1 What dotnet/yarp#1764 says

- **Title:** "Doc WebSocket keep-alive requirement"
- **Opened:** June 17, 2022, by Tratcher (a YARP maintainer)
- **Labels:** `Type: Documentation`, **`help wanted`** ("we will welcome a contribution"). **Milestone:** Backlog. **Status:** open.
- **Body (verbatim):**

> "100s is the default activity timeout to close idle requests. Without this timeout the proxy would be subject to resource leaks as it can be very difficult to detect disconnects without ongoing traffic. WebSocket or application level keep-alives are required to keep an idle WebSocket from being closed by the proxy. These can be enabled on either the client or server (not the proxy)."

So this is a **documentation** issue. The maintainer already knows the behavior. What's missing is for users to find it *before* their WebSockets mysteriously die at 100 seconds. That's why people keep filing questions like "YARP keeps terminating the WebSocket after around 2 minutes" and "how do I set the timeout in YARP?"

### 0.2 Why this is a great first contribution

- It's labeled **help wanted** by the maintainers themselves.
- The change is **small and low-risk** (docs), but getting it *right* requires understanding a real systems concept end to end. That's the best kind of learning.
- You'll interact with two Microsoft repos: `dotnet/yarp` (the issue) and `dotnet/AspNetCore.Docs` (where YARP's docs live now, §12).

### 0.3 The map of what you need to understand

Each layer of this diagram is a section of this lecture. Read top to bottom, *then* go down into the sections.

```
 BROWSER / .NET CLIENT                 YARP (reverse proxy)                 DESTINATION SERVER
 ─────────────────────                 ────────────────────                 ──────────────────
 WebSocket messages, pings  ◄─ §8 ─►   copies bytes both ways,   ◄─ §8 ─►   WebSocket messages, pings
                                       ActivityTimeout (100 s)   §9
 HTTP/1.1 Upgrade or HTTP/2 ◄─ §7 ─►   Kestrel (in)   HttpMessageInvoker/  ◄─ §7 ─► Kestrel
                                                      SocketsHttpHandler (out)
 TLS (optional)             ◄─ §6 ─►   TLS                       TLS       ◄─ §6 ─►   TLS
 TCP connection #1          ◄─ §3 ─►   socket A                  socket B  ◄─ §3 ─►   TCP connection #2
 socket (fd) §2, §5                    (two SEPARATE TCP connections!)                  socket (fd)
```

The one sentence to remember: **YARP sits between two separate TCP connections and copies bytes between them. If no bytes move for 100 seconds, it hangs up both.**

---

## 1. The layer cake: envelopes inside envelopes

Tag: 🟢 **OWN IT**.

Networking is built as **layers**, each wrapping the one above it in its own envelope:

```
 ┌───────────────────────────────────────────────────────┐
 │ Ethernet/Wi-Fi frame  (MAC addresses: next hop only)  │
 │ ┌───────────────────────────────────────────────────┐ │
 │ │ IP packet  (IP addresses: which machine)          │ │
 │ │ ┌───────────────────────────────────────────────┐ │ │
 │ │ │ TCP segment  (ports, sequence numbers, ACKs)  │ │ │
 │ │ │ ┌───────────────────────────────────────────┐ │ │ │
 │ │ │ │ TLS record  (encrypted; optional)         │ │ │ │
 │ │ │ │ ┌───────────────────────────────────────┐ │ │ │ │
 │ │ │ │ │ HTTP request/response or WebSocket    │ │ │ │ │
 │ │ │ │ │ frame (what your code reads & writes) │ │ │ │ │
 │ │ │ │ └───────────────────────────────────────┘ │ │ │ │
 │ │ │ └───────────────────────────────────────────┘ │ │ │
 │ │ └───────────────────────────────────────────────┘ │ │
 │ └───────────────────────────────────────────────────┘ │
 └───────────────────────────────────────────────────────┘
```

| Layer | Job | Identifies things by | Who implements it |
|---|---|---|---|
| Link (Ethernet, Wi-Fi) | Move a frame to the *next* device | MAC address | Network card + driver |
| **IP** | Route a packet across networks to a machine, best-effort (packets can be lost, duplicated, reordered) | IP address | OS kernel |
| **TCP** | Turn unreliable packets into a **reliable, ordered byte stream** between two programs | **Port** numbers | OS kernel |
| **TLS** | Encrypt and authenticate the byte stream | Certificates | A library (OpenSSL on Linux; used by .NET) |
| **Application** (HTTP, WebSocket) | Give the bytes meaning | URLs, headers, frames | Your code / frameworks (Kestrel, `HttpClient`, YARP) |

**The firmware twin:** I2C has layers too. The electrical layer (SDA/SCL, pull-ups), the bit/byte layer (START, address, ACK), and your *application* protocol on top (your 3-byte frame with a preamble). Networking is the same idea with more floors.

### 1.1 What "a connection" actually is

A TCP connection is uniquely identified by a **4-tuple**:

```
 (client IP, client port, server IP, server port)
 e.g. (192.168.1.10, 51432, 192.168.1.20, 443)
```

- The **server port** is well known (443 for HTTPS, 80 for HTTP, 5000 in our lab).
- The **client port** is an *ephemeral* port the OS picks automatically.
- The same server port serves thousands of clients at once, because each connection has a different 4-tuple.
- A "connection" is **state in two kernels**: sequence numbers, buffers, timers. There's no physical wire reserved for it. That fact explains a lot about timeouts (§9.4).

---

## 2. Sockets: what they are and the calls that drive them

Tag: 🟢 **OWN IT**.

### 2.1 A socket is a file descriptor

From Lecture 004 §7.1: Linux names every open resource with a **file descriptor** (a small integer). A **socket** is simply a file descriptor that represents one end of a network conversation. You `read` and `write` it like a file; the kernel turns that into packets.

There are two kinds of TCP socket, and confusing them is the #1 beginner mistake:

| Kind | What it is | Created by |
|---|---|---|
| **Listening socket** | A "front desk" bound to a port. It never carries data. It only produces new connections. | `socket()` + `bind()` + `listen()` |
| **Connected socket** | One per conversation. Carries the actual bytes. | `accept()` on the server; `connect()` on the client |

### 2.2 The call sequence (the C API every language wraps)

```
        SERVER                                              CLIENT
        ──────                                              ──────
 fd_l = socket(AF_INET, SOCK_STREAM)                 fd = socket(AF_INET, SOCK_STREAM)
 bind(fd_l, 0.0.0.0:5000)                                   │
 listen(fd_l, backlog)                                      │
        │                                                   │
 fd_c = accept(fd_l)  ◄── blocks until a ───┐        connect(fd, server:5000)
        │                 connection is     └─────── (the kernel performs the
        │                 fully established          3-way handshake, §3)
        │                                                   │
 recv(fd_c) / send(fd_c)  ◄════ bytes in both directions ═══► send(fd) / recv(fd)
        │                                                   │
 close(fd_c)                                         close(fd)
```

### 2.3 What the kernel does behind those calls

```
                          SERVER KERNEL
 SYN arrives ──► [ SYN queue ]  half-open connections (handshake in progress)
                       │ handshake completes
                       ▼
                 [ ACCEPT queue ]  completed connections waiting for your accept()
                       │   ← size limited by the listen() backlog
                       ▼
 accept() returns a NEW fd, with its own:
     send buffer  ── your send()/write() copies bytes HERE; the kernel sends them later
     receive buffer ── arriving bytes wait HERE until your recv()/read()
```

Two consequences you'll meet in practice:

1. **`send` returning doesn't mean the peer received anything.** It only means the bytes were copied into your kernel's send buffer.
2. **Your program doesn't do the handshake.** `connect()` and `accept()` are just the moments your program *observes* that the kernel finished it.

### 2.4 Blocking vs async (why one thread can serve thousands of sockets)

- **Blocking style:** `recv()` puts the thread to sleep until bytes arrive. One thread per connection.
- **Event style:** ask the kernel, "wake me when *any* of these 10,000 sockets has data" (`epoll` on Linux, `kqueue` on macOS, I/O completion ports on Windows).
- **.NET uses the event style underneath `await`.** On Linux, `Socket` operations are driven by an `epoll` loop inside the runtime's socket implementation (`SocketAsyncEngine`). When you `await stream.ReadAsync(...)`, no thread waits. The `epoll` loop fires when the fd becomes readable, and your continuation is queued to the thread pool. That's Lecture 001 §10's "a `Task` is not a thread," at the bottom of the stack.

---

## 3. The TCP handshake and teardown, byte by byte

Tag: 🟢 **OWN IT**.

### 3.1 The three-way handshake: opening a connection

Each side picks a random starting **sequence number** (ISN), a counter for the bytes it will send. The handshake exchanges and acknowledges both:

```
 CLIENT                                                       SERVER (listening)
   │   ① SYN, seq = x                                           │
   │ ─────────────────────────────────────────────────────────► │  "I want to talk; my bytes start at x"
   │                                                            │
   │   ② SYN-ACK, seq = y, ack = x+1                            │
   │ ◄───────────────────────────────────────────────────────── │  "OK; mine start at y; I expect your x+1"
   │                                                            │
   │   ③ ACK, ack = y+1                                         │
   │ ─────────────────────────────────────────────────────────► │  "Got it; I expect your y+1"
   │                                                            │
 connect() returns                                   connection moves to the accept queue;
                                                     accept() returns a new fd
```

Why three steps? Each side must prove it can both **send** and **receive**, and must learn the other's starting sequence number. Two messages can't confirm both directions.

### 3.2 Sending data

Every byte has a sequence number. The receiver acknowledges ("ACK = next byte I expect"). Lost segments are retransmitted after a timeout. The **window** in each ACK says how much more the receiver's buffer can take (**flow control**). And **congestion control** adapts the sending rate to the network. Your code sees none of this, just an ordered stream of bytes.

### 3.3 Closing: FIN, and the violent version, RST

```
 A (closes first)                                              B
   │  FIN  ───────────────────────────────────────────────────► │  B's read() returns 0 ("end of stream")
   │  ◄──────────────────────────────────────────────────  ACK  │
   │        (B can still send its remaining data: "half-close") │
   │  ◄──────────────────────────────────────────────────  FIN  │  B calls close()
   │  ACK ────────────────────────────────────────────────────► │
 TIME_WAIT (A remembers the connection for a while, so stray
            late packets aren't confused with a new connection)
```

- **FIN** = "I'm done sending." Graceful.
- **RST** (reset) = "This connection is dead, now." Sent when a process is killed, when data arrives for a connection the kernel doesn't know, or when an app aborts a socket.

### 3.4 What each event looks like from C#

| On the wire | What your .NET code sees |
|---|---|
| SYN answered by RST (nothing listening on that port) | `SocketException` "Connection refused" |
| SYN gets no answer (firewall drops it, host down) | Connect hangs, then times out |
| Peer sends FIN | `ReadAsync` returns **0** |
| Peer sends RST | `IOException`/`SocketException` "Connection reset by peer" |
| Nothing at all for hours | **Nothing.** Your read just keeps waiting. (That's the problem YARP's timeout exists to solve, §9.3.) |

The last row is the heart of issue #1764. **TCP by itself can't tell "the other side is quiet" apart from "the other side is gone"** (for example, a laptop that closed its lid, or a cable pulled out). No packet is ever sent to say "I vanished."

### 3.5 TCP keepalive (the kernel's heartbeat)

TCP has an optional **keepalive**: after a connection sits idle for a while, the kernel sends tiny probe segments. If the peer doesn't answer, the kernel declares the connection dead. On Linux, the default idle time before the first probe is **7200 seconds (2 hours)**. Crucially, these probes are **invisible to applications**. They never show up as bytes in your stream. Hold onto that fact for §9.

---

## 4. TCP is a byte stream: the framing problem

Tag: 🟢 **OWN IT**.

TCP guarantees the *bytes* arrive in order. It does **not** preserve message boundaries:

```
 sender:  Send("HELLO")  Send("WORLD")
 receiver may get:  "HELLOWORLD"       (one read)
               or:  "HEL" + "LOWORLD"  (two reads)
               or:  "H" "E" "L" …     (in theory, any split)
```

So every protocol on top of TCP must define **framing**: how to find where one message ends and the next begins. There are three classic approaches:

| Approach | Example |
|---|---|
| Delimiter | HTTP/1.1 headers end with `\r\n\r\n`; line-based protocols end with `\n` |
| Length prefix | HTTP/2 frames, WebSocket frames, gRPC messages |
| Fixed size | **Your I2C telemetry:** always 3 bytes, with a preamble that says what the payload means |

You already designed a framing scheme in firmware. HTTP and WebSockets are framing schemes too, just bigger. That's the bridge to §7 and §8.

---
## 5. Sockets in C#: a server and a client

Tag: 🟢 **OWN IT**. Three levels of API, from lowest to highest:

| Type | Level | Use it when |
|---|---|---|
| `System.Net.Sockets.Socket` | Thin wrapper over the OS socket (the fd lives in a `SafeSocketHandle`, the Lecture 004 §7.5 pattern) | You need full control (options, UDP, raw) |
| `TcpListener` / `TcpClient` | Convenience wrappers for TCP | Simple TCP servers and clients |
| `NetworkStream` | A `Stream` over a connected socket | Read/write bytes with the normal `Stream` API |

### 5.1 An echo server

```csharp
// EchoServer/Program.cs   (dotnet new console)
using System.Net;
using System.Net.Sockets;

var listener = new TcpListener(IPAddress.Loopback, 7000);
listener.Start();                                         // socket() + bind() + listen()
Console.WriteLine("Listening on 127.0.0.1:7000");

while (true)
{
    TcpClient client = await listener.AcceptTcpClientAsync();  // accept(): returns AFTER the 3-way handshake
    Console.WriteLine($"Accepted {client.Client.RemoteEndPoint}");
    _ = HandleAsync(client);                               // don't await: keep accepting other clients
}

static async Task HandleAsync(TcpClient client)
{
    using (client)
    {
        NetworkStream stream = client.GetStream();
        var buffer = new byte[1024];
        int n;
        while ((n = await stream.ReadAsync(buffer)) > 0)   // 0 means the peer sent FIN
        {
            await stream.WriteAsync(buffer.AsMemory(0, n)); // echo back exactly what arrived
        }
        Console.WriteLine("Peer closed the connection (FIN)");
    }                                                       // Dispose → close() → our FIN
}
```

### 5.2 A client

```csharp
// EchoClient/Program.cs
using System.Net.Sockets;
using System.Text;

using var client = new TcpClient();
await client.ConnectAsync("127.0.0.1", 7000);            // connect(): SYN, SYN-ACK, ACK
NetworkStream stream = client.GetStream();

await stream.WriteAsync(Encoding.UTF8.GetBytes("hello\n"));
var buffer = new byte[1024];
int n = await stream.ReadAsync(buffer);                   // may return fewer bytes than were sent! (§4)
Console.WriteLine($"Echoed: {Encoding.UTF8.GetString(buffer, 0, n)}");
```

### 5.3 Watch it happen (do all three; each takes minutes)

On Linux (your Ubuntu desktop):

```bash
# 1. See the sockets and their states (LISTEN, ESTAB, TIME-WAIT)
ss -tanp | grep 7000

# 2. See the packets: SYN, SYN-ACK, ACK, data, FIN
sudo tcpdump -i lo -n port 7000

# 3. See the syscalls .NET makes (socket, bind, listen, accept4, epoll_wait, recvfrom …)
strace -f -e trace=network,epoll_wait dotnet EchoServer.dll
```

Then do the same with **Wireshark** on the loopback interface. Click the SYN, then the SYN-ACK, then the ACK, and match every field to §3.1.

**Exercises:** (1) Kill the server with Ctrl+C while a client is connected, and watch what the client sees (FIN or RST?). (2) Change the client to connect and then sit idle without sending anything. Watch `ss`: the connection stays `ESTAB` indefinitely, with no traffic at all. Nothing on the wire says whether the other side is still there. That's §3.4's last row, reproduced with your own hands.

---

## 6. TLS in one page

Tag: 🔵 **CONTRACT**.

TLS turns the TCP byte stream into an **encrypted, authenticated** byte stream. After the TCP handshake, a **TLS handshake** runs (TLS 1.3 needs one round trip):

```
 ClientHello  (supported versions and ciphers, a key share, the server name via SNI)  ───►
                                   ◄───  ServerHello (chosen cipher, key share) + certificate + proof
 both sides derive the same session keys; everything after this is encrypted
```

- **Certificates** prove the server is who it claims to be (the client checks the chain against trusted roots and matches the host name).
- **ALPN** (inside ClientHello) negotiates the application protocol: `h2` (HTTP/2) or `http/1.1`. This is how a client and server agree on HTTP/2 over TLS.
- **For YARP:** the incoming TLS connection is terminated by Kestrel, and the outgoing one is a *new* TLS session made by `SocketsHttpHandler`. Two separate TLS sessions, just as there are two separate TCP connections. (YARP's `SslProtocols` and `DangerousAcceptAnyServerCertificate` settings, §10.2, control the outgoing one.)
- **For your lab:** use plain `http://` and `ws://`, so Wireshark can show you everything unencrypted.

---

## 7. HTTP on top of TCP, and the many kinds of "keep-alive"

Tag: 🟢 **OWN IT**.

### 7.1 HTTP/1.1 is just text over the socket

You can speak HTTP by hand over a raw socket. This makes it concrete:

```csharp
using System.Net.Sockets;
using System.Text;

using var client = new TcpClient();
await client.ConnectAsync("example.com", 80);
var stream = client.GetStream();

string request =
    "GET / HTTP/1.1\r\n" +
    "Host: example.com\r\n" +
    "Connection: close\r\n" +       // ask the server to close after responding
    "\r\n";                         // blank line = end of headers (the framing delimiter)

await stream.WriteAsync(Encoding.ASCII.GetBytes(request));
using var reader = new StreamReader(stream, Encoding.ASCII);
Console.WriteLine(await reader.ReadToEndAsync());   // status line, headers, blank line, body
```

A response starts with a **status line** (`HTTP/1.1 200 OK`), then headers, then a blank line, then a body whose length is given by `Content-Length` or by chunked encoding (framing again).

### 7.2 HTTP/1.1 vs HTTP/2

| | HTTP/1.1 | HTTP/2 |
|---|---|---|
| Format | Text | Binary **frames** (length-prefixed) |
| Requests per connection at a time | One (in practice) | **Many**, multiplexed as independent *streams* |
| Connection health check | None built in | **PING frames** at the connection level |
| WebSockets | Via `Upgrade` → `101` (§8.1) | Via **extended CONNECT** (RFC 8441), one stream per WebSocket |

### 7.3 Clients, pools, and connection reuse in .NET

- `HttpClient` sits on top of **`SocketsHttpHandler`**, which keeps a **pool of open connections** per destination and reuses them. Opening a new TCP (+TLS) connection per request would be slow.
- `HttpMessageInvoker` is the lower-level base class of `HttpClient` (without conveniences like `BaseAddress`, `Timeout`, or response buffering helpers). **YARP forwards with an `HttpMessageInvoker`,** because proxies must stream responses and must not apply `HttpClient`'s 100-second overall `Timeout`.
- **Kestrel** is ASP.NET Core's server: it accepts connections, parses HTTP, and hands each request to the middleware pipeline.

### 7.4 Five mechanisms people call "keep-alive"

Three different features are literally named "keep-alive," and two more do a similar job. Mixing them up causes endless confusion, including in YARP questions. Learn this table cold:

| Name | Layer | What it does | Visible to applications? | Resets YARP's ActivityTimeout? |
|---|---|---|---|---|
| **TCP keepalive** | TCP (kernel) | Probes an idle connection to detect dead peers (Linux default: first probe after 2 hours) | ❌ No | ❌ **No** |
| **HTTP keep-alive** (persistent connections) | HTTP/1.1 | Reuse one TCP connection for many requests, instead of closing after each. Kestrel closes idle ones after `KeepAliveTimeout` (2 minutes by default). | Connection reuse only | Not applicable (it's *between* requests) |
| **HTTP/2 PING** | HTTP/2 connection | Checks that the connection is alive (`SocketsHttpHandler.KeepAlivePingDelay`, off by default) | Handled inside the HTTP stack | ❌ **No** (it's connection-level, not on your request's stream) |
| **WebSocket ping/pong** | WebSocket | Control frames *inside* the WebSocket stream | ✅ Flows as bytes through the stream | ✅ **Yes** |
| **Application heartbeat** | Your protocol | e.g. SignalR's keep-alive message every 15 seconds by default, or a `{"type":"ping"}` message | ✅ Yes | ✅ **Yes** |

The rightmost column is the whole of issue #1764 in one table.

---

## 8. WebSockets: the upgrade handshake, frames, pings

Tag: 🟢 **OWN IT**.

### 8.1 Why WebSockets exist

HTTP is request → response: the server can't speak unless asked. Chat, live dashboards, games, and streaming telemetry need **both sides to send at any time over one long-lived connection**. A WebSocket starts life as an HTTP request, then "upgrades" the same TCP connection into a two-way message channel (RFC 6455).

### 8.2 The opening handshake (HTTP/1.1)

The client sends an ordinary HTTP GET with special headers:

```
GET /ws HTTP/1.1
Host: localhost:5000
Connection: Upgrade
Upgrade: websocket
Sec-WebSocket-Version: 13
Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==        ← 16 random bytes, base64-encoded
```

If the server agrees, it answers with status **101 Switching Protocols**:

```
HTTP/1.1 101 Switching Protocols
Connection: Upgrade
Upgrade: websocket
Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=
```

From this moment, the TCP connection **stops speaking HTTP** and carries WebSocket frames.

`Sec-WebSocket-Accept` proves the server really understood the WebSocket request (and isn't a confused plain HTTP server or cache). It's computed as `base64(SHA-1(key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"))`, where the GUID is a fixed constant from the RFC. Verify the example yourself:

```csharp
using System.Security.Cryptography;
using System.Text;

string key = "dGhlIHNhbXBsZSBub25jZQ==";
string accept = Convert.ToBase64String(
    SHA1.HashData(Encoding.ASCII.GetBytes(key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11")));
Console.WriteLine(accept);   // s3pPLMBiTxaQ9kYGzzhZRbK+xOo=   (the RFC 6455 example)
```

You can also trigger a handshake from the command line against a server you run (§11), and watch the `101`:

```bash
curl -i -N \
  -H "Connection: Upgrade" -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Version: 13" -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" \
  http://localhost:5001/ws
```

### 8.3 Frames: WebSocket's own framing

```
  0                   1                   2                   3
 ┌─┬─┬─┬─┬───────┬─┬─────────────┬───────────────────────────────┐
 │F│R│R│R│opcode │M│ payload len │ extended payload length       │
 │I│S│S│S│ (4)   │A│    (7)      │ (16 or 64 bits, if len = 126/127)
 │N│V│V│V│       │S│             │                               │
 └─┴─┴─┴─┴───────┴─┴─────────────┴───────────────────────────────┘
 │ masking key (32 bits, only if MASK = 1) │ payload data …        │
```

| Opcode | Frame type | Notes |
|---|---|---|
| `0x1` | Text | UTF-8 |
| `0x2` | Binary | |
| `0x0` | Continuation | For messages split across frames (`FIN = 0` until the last) |
| `0x8` | **Close** | Carries a status code (e.g. 1000 normal, 1001 going away); starts the closing handshake |
| `0x9` | **Ping** | "Are you there?" The receiver must answer with a Pong. |
| `0xA` | **Pong** | Answer to a ping, or sent *unsolicited* as a one-way heartbeat |

Two details worth knowing:
- **Client-to-server frames must be masked** (XORed with a random key). This prevents old proxies from misinterpreting WebSocket bytes as HTTP.
- **Control frames** (close, ping, pong) are small (at most 125 bytes of payload) and can be interleaved between fragments of a large message.

From the TCP (and YARP) point of view, a ping frame is **just a few bytes flowing through the stream**. That's why it counts as activity.

### 8.4 Keep-alive in .NET's WebSocket implementations

| Side | Setting | Default | Behavior |
|---|---|---|---|
| **.NET client** (`ClientWebSocket`) | `Options.KeepAliveInterval` | 30 seconds (`WebSocket.DefaultKeepAliveInterval`) | Sends a keep-alive every interval. By default, an **unsolicited Pong** (a one-way heartbeat). |
| .NET client, .NET 9+ | `Options.KeepAliveTimeout` | Off | If set, sends **Ping** and expects a Pong within the timeout. Otherwise the connection is aborted. |
| **ASP.NET Core server** (`WebSocketOptions`, `UseWebSockets`) | `KeepAliveInterval` | **2 minutes** | "How frequently to send ping frames to the client to ensure proxies keep the connection open" |
| ASP.NET Core server, .NET 9+ | `KeepAliveTimeout` (global or per accept via `WebSocketAcceptContext`) | Disabled | Wait for a Pong; abort if it doesn't come |
| **Browser JavaScript** `WebSocket` | — | — | **Can't send pings from JavaScript.** Browsers answer server pings automatically. Browser apps need server-side keep-alives or app-level heartbeats. |

**Look closely at the ASP.NET Core default: 2 minutes.** That's *longer* than YARP's 100-second `ActivityTimeout`. So the classic failure is:

> A browser client (can't ping) talks through YARP (100 s idle limit) to an ASP.NET Core server with default settings (keep-alive every 120 s). The first keep-alive would arrive at 120 s, but YARP already closed the connection at 100 s.

Reports like "YARP keeps terminating the WebSocket after around 2 minutes" fit this pattern. By contrast, a .NET client with default settings (keep-alive every 30 s) generally *won't* hit it, because its own keep-alives reset the timer. That's a nice nuance to include in the docs.

### 8.5 WebSockets over HTTP/2

Since .NET 7, WebSockets can also run over HTTP/2 using **extended CONNECT** (RFC 8441): instead of a GET + 101 that takes over a whole TCP connection, the WebSocket becomes **one stream** inside a multiplexed HTTP/2 connection. Kestrel supports it automatically, and browsers use it when the server advertises support. YARP can accept either version and forward with either version, adapting the headers. After the handshake, both behave the same, and the **ActivityTimeout applies either way.**

### 8.6 The C# code: server and client

Server (ASP.NET Core). Note `UseWebSockets`, where the server keep-alive is set:

```csharp
// WsServer/Program.cs   (dotnet new web)
using System.Net.WebSockets;

var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

int keepAliveSeconds = app.Configuration.GetValue("KeepAliveSeconds", 0);   // 0 = off, for experiments
app.UseWebSockets(new WebSocketOptions
{
    KeepAliveInterval = keepAliveSeconds > 0 ? TimeSpan.FromSeconds(keepAliveSeconds) : TimeSpan.Zero,
});

app.Map("/ws", async (HttpContext context) =>
{
    if (!context.WebSockets.IsWebSocketRequest)
    {
        context.Response.StatusCode = StatusCodes.Status400BadRequest;
        return;
    }

    using WebSocket ws = await context.WebSockets.AcceptWebSocketAsync();   // sends the 101
    var buffer = new byte[4096];

    while (true)
    {
        ValueWebSocketReceiveResult result = await ws.ReceiveAsync(buffer.AsMemory(), context.RequestAborted);
        if (result.MessageType == WebSocketMessageType.Close)
        {
            await ws.CloseAsync(WebSocketCloseStatus.NormalClosure, "bye", CancellationToken.None);
            break;
        }
        await ws.SendAsync(buffer.AsMemory(0, result.Count), result.MessageType, result.EndOfMessage, context.RequestAborted);
    }
});

app.Run("http://localhost:5001");
```

Client (`ClientWebSocket`):

```csharp
// WsClient/Program.cs   (dotnet new console)
using System.Diagnostics;
using System.Net.WebSockets;
using System.Text;

int keepAliveSeconds = args.Length > 0 ? int.Parse(args[0]) : 0;          // 0 = off
string url = args.Length > 1 ? args[1] : "ws://localhost:5000/ws";         // 5000 = through YARP

using var ws = new ClientWebSocket();
ws.Options.KeepAliveInterval = keepAliveSeconds > 0 ? TimeSpan.FromSeconds(keepAliveSeconds) : TimeSpan.Zero;

await ws.ConnectAsync(new Uri(url), CancellationToken.None);               // TCP + HTTP upgrade handshake
Console.WriteLine($"{DateTime.Now:T} connected to {url} (client keep-alive: {keepAliveSeconds}s)");

await ws.SendAsync(Encoding.UTF8.GetBytes("hello").AsMemory(), WebSocketMessageType.Text, true, CancellationToken.None);

var buffer = new byte[4096];
var sw = Stopwatch.StartNew();
try
{
    while (true)
    {
        ValueWebSocketReceiveResult result = await ws.ReceiveAsync(buffer.AsMemory(), CancellationToken.None);
        if (result.MessageType == WebSocketMessageType.Close)
        {
            Console.WriteLine($"Closed by peer after {sw.Elapsed.TotalSeconds:F0}s: {ws.CloseStatus} {ws.CloseStatusDescription}");
            break;
        }
        Console.WriteLine($"{DateTime.Now:T} received: {Encoding.UTF8.GetString(buffer, 0, result.Count)}");
    }
}
catch (WebSocketException ex)
{
    Console.WriteLine($"{DateTime.Now:T} connection lost after {sw.Elapsed.TotalSeconds:F0}s: {ex.Message}");
}
```

Notice that after the first echo, **nobody sends anything**. That idle period is what we'll aim YARP's timer at in §11.

---
## 9. Where YARP comes in: two connections and a copy loop

Tag: 🟢 **OWN IT**. (Your `lectures/yarp/` series explains YARP's architecture in depth. `012-yarp_architecture_putting_everything_together.md` pairs well with this section.)

### 9.1 What YARP is

YARP ("Yet Another Reverse Proxy") is a **library**, not a standalone server. You host it inside an ASP.NET Core app. A **reverse proxy** receives requests *on behalf of* backend servers and forwards them, which makes it useful for routing, load balancing, TLS termination, and hiding internal topology.

```
 client ──TCP #1──► [ Kestrel ─► middleware ─► YARP: match ROUTE ─► pick CLUSTER destination
                                              ─► transforms ─► HttpForwarder ─► HttpMessageInvoker ]
                                                                                        │
                                                                              TCP #2 ───┴──► destination
```

- **Routes** decide *which* requests to handle (path, host, headers).
- **Clusters** are groups of **destinations** (backend addresses), plus the per-cluster settings for the outgoing HTTP client and requests (§10).

### 9.2 A normal HTTP request through YARP

1. Kestrel accepts TCP #1 and parses the request.
2. YARP matches a route, picks a destination, and applies transforms (headers, path).
3. `HttpForwarder` sends the request with an `HttpMessageInvoker` over TCP #2 (pooled by `SocketsHttpHandler`).
4. It streams the response body back to the client as it arrives.

### 9.3 A WebSocket through YARP

```
 client                          YARP                                    destination
   │ GET /ws  Upgrade: websocket   │                                          │
   │ ────────────────────────────► │  forwards the upgrade request            │
   │                               │ ───────────────────────────────────────► │
   │                               │ ◄─────────────────── 101 Switching ───── │
   │ ◄──── 101 Switching ───────── │                                          │
   │                               │                                          │
   │   From now on YARP holds two opaque byte streams and runs two copy loops │
   │                               │                                          │
   │ ═══ bytes (frames) ═══════►  [copy loop 1: client → destination]  ══════►│
   │ ◄══════════════════════════  [copy loop 2: destination → client]  ◄══════│
   │                               │                                          │
   │   Every successful read/write restarts the ACTIVITY TIMER (100 s).       │
   │   If the timer fires, YARP aborts BOTH connections.                      │
```

Two important properties:

- **After the 101, YARP no longer understands the traffic.** It copies bytes. It doesn't parse WebSocket frames (the same path also carries other upgraded protocols, like SPDY). That's one reason the issue says keep-alives must come from the client or server, "not the proxy": the proxy can't safely inject frames into a stream it treats as opaque.
- **A WebSocket ping or pong is just a few bytes in that stream.** So it passes through a copy loop and restarts the timer.

### 9.4 The activity timer: the idea in code

This is **simplified pseudo-code** to show the mechanism, not YARP's actual source. (To read the real implementation, search the YARP repo for `ActivityTimeout` and follow it to the type that resets a cancellation timer on progress.)

```csharp
// PSEUDO-CODE: the concept behind ActivityTimeout, not YARP's real implementation
async Task CopyAsync(Stream from, Stream to, ActivityTimer activity, CancellationToken ct)
{
    // ct is cancelled when the activity timer expires (or the client disconnects)
    var buffer = new byte[64 * 1024];
    while (true)
    {
        int n = await from.ReadAsync(buffer, ct);
        if (n == 0) return;                         // this side sent FIN: stream finished
        activity.Restart();                         // progress! push the deadline 100 s into the future
        await to.WriteAsync(buffer.AsMemory(0, n), ct);
        activity.Restart();
    }
}
```

Read that loop and the whole issue becomes obvious:

| Thing that happens | Does it complete a `ReadAsync` in the loop? | Resets the timer? |
|---|---|---|
| Application message (chat line, telemetry) | Yes | ✅ |
| WebSocket ping / pong frame | Yes (it's stream bytes) | ✅ |
| TCP keepalive probe | No (the kernel handles it; zero bytes reach the stream) | ❌ |
| HTTP/2 PING frame | No (connection-level, handled inside `SocketsHttpHandler`/Kestrel, not on this stream) | ❌ |
| Nothing at all | No | ❌ → abort at 100 s |

### 9.5 Why the timeout exists at all

From §3.4: **a peer that disappears silently never sends FIN or RST.** Laptops sleep, phones switch networks, NAT devices and firewalls quietly forget connection mappings. Each proxied WebSocket costs YARP two sockets, buffers, and tasks. Without an idle limit, silent corpses would pile up until the proxy runs out of memory or file descriptors. That's exactly the issue text: *"Without this timeout the proxy would be subject to resource leaks as it can be very difficult to detect disconnects without ongoing traffic."*

This is a real design trade-off, and worth being able to explain:

| Longer timeout | Shorter timeout |
|---|---|
| Idle-but-alive connections survive | Dead connections are cleaned up sooner |
| Dead connections waste resources longer | Legitimately quiet connections get cut, unless endpoints send keep-alives |

The system-level answer is **both**: a bounded timeout at the proxy *and* keep-alives at the endpoints that are comfortably shorter than every idle limit on the path. And YARP isn't the only box with one: cloud load balancers have idle timeouts too (for example, an Azure Load Balancer's default idle timeout is 4 minutes, and an AWS Application Load Balancer's is 60 seconds). Keep-alive intervals of around 15–30 seconds survive almost any path.

### 9.6 The timeline of the failure, and the fix

```
 NO KEEP-ALIVES (browser client, ASP.NET Core server with default 2-minute keep-alive)
 t=0s     connect + handshake (101) ...................... timer set to t=100
 t=1s     "hello" → echo ................................. timer reset to t=101
 t=1–101s silence
 t=101s   YARP timer fires → aborts both TCP connections
 t=121s   (the server's first keep-alive would have been sent here: too late)
          client sees an exception / close; server sees its socket die

 SERVER KEEP-ALIVE EVERY 30s
 t=0s  connect ... t=30s ping → pong ... t=60s ping → pong ... t=90s ping → pong ...
          each frame resets YARP's timer; the connection lives indefinitely
```

---

## 10. Configuring YARP: HttpClient, HttpRequest, timeouts

Tag: 🟢 **OWN IT** for the configuration model, 🔵 for individual knobs. This is the "HTTP client configuration" documentation you found, placed in context.

### 10.1 The configuration model

```json
{
  "ReverseProxy": {
    "Routes": {
      "route1": {
        "ClusterId": "cluster1",
        "Match": { "Path": "{**catch-all}" }
      }
    },
    "Clusters": {
      "cluster1": {
        "HttpClient": {                              // HOW TO CONNECT to destinations: SocketsHttpHandler settings
          "MaxConnectionsPerServer": 100,
          "SslProtocols": [ "Tls12", "Tls13" ]
        },
        "HttpRequest": {                             // HOW EACH FORWARDED REQUEST behaves: ForwarderRequestConfig
          "ActivityTimeout": "00:02:00",
          "Version": "2",
          "VersionPolicy": "RequestVersionOrLower"
        },
        "Destinations": {
          "d1": { "Address": "https://backend1.internal/" }
        }
      }
    }
  }
}
```

The key distinction: **`HttpClient` is about the outbound *connections*** (pooling, TLS, proxies). **`HttpRequest` is about each forwarded *request*** (activity timeout, HTTP version). Both are **per cluster**.

### 10.2 `HttpClient` settings (outbound connections)

| Setting | Meaning | Default |
|---|---|---|
| `SslProtocols` | Allowed TLS versions to destinations | System default |
| `DangerousAcceptAnyServerCertificate` | Skip certificate validation. **Test only.** | `false` |
| `MaxConnectionsPerServer` | Cap on concurrent HTTP/1.1 connections to one server | Unlimited (`int.MaxValue`) |
| `EnableMultipleHttp2Connections` | Open extra HTTP/2 connections when one hits its stream limit | `true` |
| `RequestHeaderEncoding` / `ResponseHeaderEncoding` | Allow non-ASCII header encodings | ASCII only |
| `WebProxy` (`Address`, `BypassOnLocal`, `UseDefaultCredentials`) | Send outbound traffic through a forward proxy | None |

### 10.3 `HttpRequest` settings (`ForwarderRequestConfig`)

| Setting | Meaning | Default |
|---|---|---|
| **`ActivityTimeout`** | "How long a request is allowed to remain idle between any operation completing, after which it will be canceled." WebSocket pings reset it; TCP keep-alives and HTTP/2 pings don't. **Applies to normal requests too**, not only WebSockets. | **100 seconds** |
| `Version` | Outbound HTTP version (1.0, 1.1, 2, 3) | 2 |
| `VersionPolicy` | `RequestVersionOrLower`, `RequestVersionOrHigher`, `RequestVersionExact` | `RequestVersionOrLower` |
| `AllowResponseBuffering` | Allow response write buffering (can break server-sent events) | off |

About version: with the defaults (2 + "or lower"), an `https://` destination negotiates HTTP/2 through TLS ALPN (§6) if the server supports it. A plain `http://` destination falls back to HTTP/1.1, because HTTP/2 without TLS needs prior knowledge ("exact" policy).

On `ActivityTimeout` for normal requests, a YARP maintainer clarified in a discussion: it "applies to active requests too, not just idle connections. If a request does not make progress within the given time period it will be aborted." A slow backend that takes 3 minutes before sending *any* response bytes will be cut off at 100 seconds.

### 10.4 The same configuration in code

```csharp
using Yarp.ReverseProxy.Configuration;
using Yarp.ReverseProxy.Forwarder;

var routes = new[]
{
    new RouteConfig
    {
        RouteId = "route1",
        ClusterId = "cluster1",
        Match = new RouteMatch { Path = "{**catch-all}" },
    },
};

var clusters = new[]
{
    new ClusterConfig
    {
        ClusterId = "cluster1",
        HttpClient = new HttpClientConfig { MaxConnectionsPerServer = 100 },
        HttpRequest = new ForwarderRequestConfig { ActivityTimeout = TimeSpan.FromMinutes(2) },
        Destinations = new Dictionary<string, DestinationConfig>
        {
            ["d1"] = new DestinationConfig { Address = "https://backend1.internal/" },
        },
    },
};

builder.Services.AddReverseProxy().LoadFromMemory(routes, clusters);
```

### 10.5 Settings that aren't in the config schema: `ConfigureHttpClient`

For any other `SocketsHttpHandler` property, YARP gives you a callback that runs whenever a cluster's handler is created:

```csharp
builder.Services.AddReverseProxy()
    .LoadFromConfig(builder.Configuration.GetSection("ReverseProxy"))
    .ConfigureHttpClient((context, handler) =>
    {
        handler.ConnectTimeout = TimeSpan.FromSeconds(10);        // fail fast if a destination is down
        handler.KeepAlivePingDelay = TimeSpan.FromSeconds(30);    // HTTP/2 PINGs keep the *connection* healthy...
        handler.KeepAlivePingTimeout = TimeSpan.FromSeconds(10);  // ...but do NOT reset ActivityTimeout (§9.4)
    });
```

For total control there's `IForwarderHttpClientFactory` (return an `HttpMessageInvoker`, **not** an `HttpClient`, to avoid response buffering and `HttpClient`'s own timeout).

### 10.6 Route-level timeouts (.NET 8+ request timeouts)

Separate from `ActivityTimeout`, YARP 2.1+ on .NET 8+ integrates ASP.NET Core's **request timeouts** middleware. You can put a *total* time limit on a route:

```json
"Routes": {
  "route1": { "ClusterId": "cluster1", "TimeoutPolicy": "customPolicy", "Match": { "Hosts": [ "localhost" ] } },
  "route2": { "ClusterId": "cluster1", "Timeout": "00:01:00",           "Match": { "Hosts": [ "localhost2" ] } }
}
```

```csharp
builder.Services.AddRequestTimeouts(options =>
{
    options.AddPolicy("customPolicy", TimeSpan.FromSeconds(20));
});
// ...
app.UseRequestTimeouts();
app.MapReverseProxy();
```

Rules to remember:
- Route `Timeout` and `ActivityTimeout` **both apply; whichever expires first wins.**
- Route/request timeouts are **disabled after a WebSocket handshake**, but **`ActivityTimeout` still applies** to WebSockets. (That's the sentence in the Timeouts doc.)
- `"TimeoutPolicy": "disable"` turns request timeouts off for a route.
- Unlike route timeouts, `ActivityTimeout` applies even with a debugger attached.

### 10.7 Direct forwarding: the same knobs without the config system

If you use YARP's low-level `IHttpForwarder` yourself, you pass the `ForwarderRequestConfig` directly:

```csharp
using System.Net;
using Yarp.ReverseProxy.Forwarder;

builder.Services.AddHttpForwarder();
var app = builder.Build();

var invoker = new HttpMessageInvoker(new SocketsHttpHandler
{
    UseProxy = false,
    AllowAutoRedirect = false,
    AutomaticDecompression = DecompressionMethods.None,
    UseCookies = false,
    ConnectTimeout = TimeSpan.FromSeconds(15),
});
var requestConfig = new ForwarderRequestConfig { ActivityTimeout = TimeSpan.FromSeconds(100) };

app.Map("/{**catch-all}", async (HttpContext httpContext, IHttpForwarder forwarder) =>
{
    ForwarderError error = await forwarder.SendAsync(
        httpContext, "http://localhost:5001/", invoker, requestConfig, HttpTransformer.Default);

    if (error != ForwarderError.None)
    {
        var errorFeature = httpContext.GetForwarderErrorFeature();
        Console.WriteLine($"Forwarding failed: {error} {errorFeature?.Exception?.Message}");
    }
});
```

### 10.8 Recipes for WebSockets through YARP

| Recipe | How | When |
|---|---|---|
| **1. Keep-alives at the endpoints** (recommended) | Server: `WebSocketOptions.KeepAliveInterval = 30 s`. .NET clients already default to 30 s. SignalR already sends keep-alives every 15 s. | Almost always. It also protects against load balancer and NAT idle timeouts, not only YARP's. |
| **2. A dedicated cluster for WebSocket routes** | Point a second cluster at the same destinations, give it a longer `ActivityTimeout`, and route `/ws` there | When you can't change the endpoints (third-party server, browser clients with a legacy backend) |
| **3. Both** | Keep-alives + a moderately raised timeout | Belt and braces for critical long-lived connections |
| ❌ **Anti-pattern** | Raise `ActivityTimeout` to hours on the main cluster | Dead connections linger for hours, and *every normal request* gets a much weaker hang detector |

Recipe 2 in config:

```json
"Routes": {
  "api": { "ClusterId": "backend",    "Match": { "Path": "/api/{**rest}" } },
  "ws":  { "ClusterId": "backend-ws", "Match": { "Path": "/ws" } }
},
"Clusters": {
  "backend": {
    "Destinations": { "d1": { "Address": "http://backend:8080/" } }
  },
  "backend-ws": {
    "HttpRequest": { "ActivityTimeout": "00:10:00" },
    "Destinations": { "d1": { "Address": "http://backend:8080/" } }
  }
}
```

---
## 11. The lab: reproduce the 100-second disconnect

Tag: 🟢 **DO IT**. The lab turns everything above into evidence, and that evidence is what makes your contribution credible (§12). Run it on the Ubuntu desktop (or the Mac). It's small and needs no special hardware.

### 11.1 Set up three projects

```bash
mkdir yarp-ws-lab && cd yarp-ws-lab
dotnet new web     -n WsServer     # §8.6 server code
dotnet new console -n WsClient     # §8.6 client code
dotnet new web     -n Proxy
dotnet add Proxy package Yarp.ReverseProxy
```

`Proxy/Program.cs`:

```csharp
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddReverseProxy()
    .LoadFromConfig(builder.Configuration.GetSection("ReverseProxy"));

var app = builder.Build();
app.MapReverseProxy();
app.Run("http://localhost:5000");
```

`Proxy/appsettings.json`. Set `ActivityTimeout` to **10 seconds** so each experiment takes seconds, not minutes:

```json
{
  "Logging": { "LogLevel": { "Default": "Information", "Yarp": "Debug" } },
  "ReverseProxy": {
    "Routes": {
      "ws": { "ClusterId": "echo", "Match": { "Path": "{**catch-all}" } }
    },
    "Clusters": {
      "echo": {
        "HttpRequest": { "ActivityTimeout": "00:00:10" },
        "Destinations": { "d1": { "Address": "http://localhost:5001/" } }
      }
    }
  }
}
```

Three terminals:

```bash
dotnet run --project WsServer                            # add -- --KeepAliveSeconds=3 for server keep-alives
dotnet run --project Proxy
dotnet run --project WsClient -- 0                       # arg 1: client keep-alive seconds; arg 2: URL (optional)
```

### 11.2 The experiments

Predict each result *before* running it (that's the "predict the review" habit from carreer_path/003, applied to systems). Then record what actually happened.

| # | Path | Server keep-alive | Client keep-alive | Prediction (per this lecture) | Your result |
|---|---|---|---|---|---|
| E1 | **Direct** (`ws://localhost:5001/ws`) | off | off | Stays open indefinitely: no proxy, no timer | |
| E2 | Through YARP | off | off | **Cut at ~10 s** | |
| E3 | Through YARP | 3 s | off | Survives (server pings reset the timer) | |
| E4 | Through YARP | off | 3 s | Survives (client unsolicited pongs reset the timer) | |
| E5 | Through YARP | off | off, but the client sends a text message every 5 s | Survives (app-level heartbeat) | |
| E6 | Through YARP, `ActivityTimeout` = 30 s | off | off | Cut at ~30 s | |
| E7 | Through YARP | 15 s | off | **Cut at ~10 s** (keep-alive interval longer than the timeout: the §8.4 trap, scaled down) | |

E7 is the most instructive. It reproduces the real-world default mismatch (server keep-alive every 2 minutes vs a 100-second proxy timeout) in miniature.

### 11.3 Look underneath while it runs

```bash
ss -tanp | grep -E ':5000|:5001'          # TWO established connections: client↔proxy and proxy↔server
sudo tcpdump -i lo -n 'port 5000 or port 5001'
```

In **Wireshark** (capture on loopback, filter `tcp.port == 5000 || tcp.port == 5001`):

1. Find **two** TCP handshakes: client → proxy on 5000, and proxy → server on 5001.
2. Find the `GET /ws` with `Upgrade: websocket`, and the `101 Switching Protocols`, **on each connection**.
3. In E3/E4, find the WebSocket **Ping/Pong** frames (Wireshark decodes the `websocket` protocol). Notice they appear on *both* connections, because YARP copies them through.
4. In E2, find the moment of the timeout: the proxy closing both connections (FIN or RST).
5. With the proxy's `Yarp` log level at Debug, match the proxy's log lines to what you see on the wire.

Write the results into your table. They're your evidence for §12.

### 11.4 Extension experiments (optional)

- **Read the real implementation:** find where YARP applies `ActivityTimeout` to the upgraded streams (search the dotnet/yarp source for `ActivityTimeout`), and compare it with the §9.4 pseudo-code. Write a context card (carreer_path/003 §5.2) for this corner of YARP.
- **Step through it:** debug the Proxy with breakpoints in YARP's source (Source Link lets the debugger download it) and watch the copy loops run.
- **HTTP/2 WebSockets:** make the client use HTTP/2 (`ws.Options.HttpVersion = HttpVersion.Version20` with `HttpVersionPolicy.RequestVersionOrHigher`, and the `ConnectAsync` overload that takes an `HttpMessageInvoker`) against an `https` proxy endpoint, and confirm the timeout behaves the same way.

---

## 12. Solving #1764: the contribution plan

### 12.1 Where things stand (checked 2026-09-26)

Before writing anything, establish the current state. That's the first thing a maintainer will want to know.

| Place | What it says about idle WebSockets |
|---|---|
| **YARP docs location** | YARP's docs moved into Microsoft Learn. The source is now `dotnet/AspNetCore.Docs`, under `aspnetcore/fundamentals/servers/yarp/` (the migration was tracked in AspNetCore.Docs issue #34650). |
| **Timeouts page** (`yarp/timeouts.md`) | ✅ Has a WebSockets paragraph: request timeouts are disabled after the handshake, "However, `ActivityTimeout` does apply to WebSocket requests. WebSocket keep-alives can be enabled by either the client or server talking to the proxy to keep the connection from becoming idle and triggering the `ActivityTimeout`." |
| **HTTP client config page** | ✅ The `ActivityTimeout` description says WebSocket pings reset it, and TCP keep-alives and HTTP/2 pings don't. |
| **WebSockets page** (`yarp/websockets.md`) | ❌ **No mention** of `ActivityTimeout`, idle disconnects, or keep-alives. Its "Timeout" section only covers request timeouts. |
| **dotnet/yarp#1764** | Still open, `help wanted`, Backlog |

**The gap:** the page a developer actually reads when proxying WebSockets doesn't warn them. It also lacks *how-to* guidance: which setting to change on an ASP.NET Core server or a .NET client, the 2-minute default mismatch, and browsers not being able to send pings. That's a small, clear, valuable contribution.

(You mentioned a linked question about configuring timeout values. Questions like that are *evidence* of the gap. Mention one or two of them in your comment to show that users hit this.)

### 12.2 Step 1: comment on the issue first

Commenting before writing the PR avoids surprises (Lecture 004 §11.3). Something like:

> *Hi! I'd like to take this. It looks like the Timeouts page and the HTTP client config page now mention `ActivityTimeout` for WebSockets, but the WebSockets page (`aspnetcore/fundamentals/servers/yarp/websockets.md` in AspNetCore.Docs) doesn't. That's the page people read when proxying WebSockets. I'd propose adding a short "Keep-alives and the activity timeout" section there, with ASP.NET Core server and .NET client settings, a note that the server's default keep-alive (2 minutes) is longer than the default `ActivityTimeout` (100 s), and a note that browsers can't send pings. I reproduced the behavior locally (results attached). Does that sound right, and should the PR go to AspNetCore.Docs?*

Attach your §11.2 results table. Evidence gets attention.

### 12.3 Step 2: the PR to `dotnet/AspNetCore.Docs`

1. Fork `dotnet/AspNetCore.Docs` and create a branch.
2. Edit `aspnetcore/fundamentals/servers/yarp/websockets.md`. Update `ms.date` in the front matter, following the repo's conventions.
3. Read the repo's contributing guidance and Microsoft Learn's contributor guide (style, `xref` links, code blocks). Docs repos care about **style consistency** as much as correctness.
4. Open the PR. Reference `dotnet/yarp#1764` in the description, and say what you verified and how.
5. The docs build produces a **preview** of the rendered page. Check it yourself before asking for review.
6. Respond to review comments promptly and graciously. Then go back to #1764 and link the PR.

### 12.4 A draft of the section (rewrite it in your own words)

This draft is here so you can see the target's *shape*: what to include and what claims can be backed up. **Rewrite it yourself.** You'll own it in review, and in interviews.

~~~~markdown
## Keep-alives and the activity timeout

YARP cancels proxied requests that make no progress for the cluster's `ActivityTimeout`, which is 100 seconds by default (see [Timeouts](xref:fundamentals/servers/yarp/timeouts)). This also applies to WebSocket and SPDY connections after the upgrade: if no data flows in either direction for longer than `ActivityTimeout`, YARP closes the connections to both the client and the destination. This protects the proxy from accumulating connections whose peers have disappeared without closing them.

To keep idle WebSocket connections open, enable WebSocket keep-alives or send application-level heartbeat messages from the client or the destination server. Keep-alives can't be enabled on the proxy. WebSocket ping and pong frames count as activity. TCP keep-alives and HTTP/2 PING frames don't, because they don't flow through the proxied stream.

* **ASP.NET Core destination servers:** set `WebSocketOptions.KeepAliveInterval` to a value lower than `ActivityTimeout`. The default interval, 2 minutes, is longer than the default `ActivityTimeout`.

  ```csharp
  app.UseWebSockets(new WebSocketOptions
  {
      KeepAliveInterval = TimeSpan.FromSeconds(30)
  });
  ```

* **.NET clients:** `ClientWebSocketOptions.KeepAliveInterval` sends keep-alives every 30 seconds by default.
* **Browser clients:** the JavaScript WebSocket API can't send ping frames. Enable keep-alives on the server, or send periodic application messages. SignalR sends keep-alive messages every 15 seconds by default.

Alternatively, increase `ActivityTimeout` for the cluster that serves WebSocket routes. A longer timeout delays the cleanup of connections whose peers have disappeared.
~~~~

Before submitting, **verify every factual claim** in the text against the current docs and your lab (defaults change between versions). Keep code samples minimal and tested.

### 12.5 What reviewers will check

| They'll ask | Be ready with |
|---|---|
| Is it accurate? | Your lab results; links to the API docs for each setting and default |
| Is it in the right place and not duplicated? | "Timeouts has the rule; the WebSockets page links to it and adds the how-to." |
| Does it follow the style guide? | Short sentences, second person, present tense, `xref` links, no unnecessary jargon |
| Is it scoped? | One section, one page. Save other ideas for separate PRs. |

**After it merges:** add it to your brag document (carreer_path/003 §1). "Diagnosed and documented a WebSocket idle-timeout behavior in YARP; contributed to Microsoft's ASP.NET Core docs" is a true, specific, Microsoft-relevant line, *and* an interview story you understand down to the TCP handshake.

---

## 13. Misconceptions to avoid

| Misconception | Reality |
|---|---|
| "TCP keepalive will keep my WebSocket alive through YARP." | Kernel probes never reach the proxied stream; they don't reset `ActivityTimeout`. |
| "HTTP/2 pings will do it." | Connection-level; they don't reset a stream's activity timer. |
| "YARP should just send pings itself." | After the upgrade YARP copies opaque bytes; injecting frames would require it to parse and participate in the protocol. The maintainers' position: enable keep-alives on the client or server. |
| "Just set `ActivityTimeout` to 24 hours." | Dead connections then linger for hours, and it weakens hang detection for *all* requests on that cluster. Use a dedicated cluster if you must. |
| "`ActivityTimeout` only affects idle WebSockets." | It applies to every proxied request that makes no progress, including a slow backend that hasn't sent a response yet. |
| "`HttpClient.Timeout` controls YARP's timeouts." | YARP forwards with `HttpMessageInvoker`. Its knobs are `ActivityTimeout` and route timeouts. |
| "`send()` returned, so the peer got it." | It only reached your kernel's send buffer. |
| "One `ReadAsync` = one message." | TCP is a byte stream; framing is the protocol's job. WebSocket APIs do the framing for you. |
| "A WebSocket is a separate connection from the HTTP request." | Over HTTP/1.1 it's the *same* TCP connection, upgraded. Over HTTP/2 it's a stream within one. |

---

## 14. Interview relevance

This lecture covers several classic interview topics, now with a story attached:

| Question | Your answer's backbone |
|---|---|
| "What happens when you type a URL and press Enter?" | DNS → TCP handshake (§3) → TLS (§6) → HTTP (§7) → rendering. You can now go deep on the middle three. |
| "Explain the TCP three-way handshake." | §3.1, including *why* three messages |
| "How would you detect a dead connection?" | TCP can't tell silence from death (§3.4). Heartbeats plus timeouts, at the right layer (§7.4). |
| "Design a WebSocket gateway for a million connections." | fds and `epoll` (§2.4), per-connection memory, idle timeouts vs keep-alives (§9.5), load balancer idle limits, graceful draining |
| "Tell me about an open-source contribution." | #1764: you reproduced the behavior, found the real gap by auditing the current docs, and wrote the fix. |

---

## 15. Self-check questions

1. What four values identify a TCP connection, and why can one server port serve thousands of clients? (§1.1)
   <details><summary>Answer</summary>Client IP, client port, server IP, server port. Each connection's 4-tuple differs (different client IP/port), so the kernel keeps them apart.</details>

2. What's the difference between a listening socket and a connected socket? (§2.1)
   <details><summary>Answer</summary>A listening socket is bound to a port and only produces new connections via <code>accept</code>. It never carries data. A connected socket is one per conversation and carries the bytes.</details>

3. Walk through the three-way handshake. Why isn't two messages enough? (§3.1)
   <details><summary>Answer</summary>SYN (seq x) → SYN-ACK (seq y, ack x+1) → ACK (ack y+1). Each side must prove it can send and receive and must learn the other's initial sequence number. Two messages can't confirm both directions.</details>

4. In C#, what does `ReadAsync` returning 0 mean, and what does "connection reset" mean? (§3.4)
   <details><summary>Answer</summary>0 means the peer sent FIN (graceful end of stream). A reset means an RST arrived: the connection was aborted.</details>

5. Why can't TCP alone detect that a peer disappeared? (§3.4)
   <details><summary>Answer</summary>A peer that vanishes (sleep, network loss, NAT expiry) sends nothing, so no FIN or RST arrives. From the other side, silence and death look identical until something is sent.</details>

6. Why does every protocol on TCP need framing? Give three framing styles. (§4)
   <details><summary>Answer</summary>TCP doesn't preserve message boundaries. Styles: delimiters (HTTP headers' blank line), length prefixes (WebSocket, HTTP/2 frames), fixed sizes (a 3-byte telemetry frame).</details>

7. How does `await socket.ReceiveAsync(...)` avoid blocking a thread on Linux? (§2.4)
   <details><summary>Answer</summary>The runtime registers the socket with an <code>epoll</code> loop. No thread waits. When the fd becomes readable, the continuation is queued to the thread pool.</details>

8. What's `Sec-WebSocket-Accept`, and how is it computed? (§8.2)
   <details><summary>Answer</summary>The server's proof that it understood the WebSocket handshake: base64(SHA-1(Sec-WebSocket-Key + the fixed GUID from RFC 6455)).</details>

9. Name the "keep-alive"-like mechanisms from §7.4 and say which reset YARP's ActivityTimeout. (§7.4)
   <details><summary>Answer</summary>TCP keepalive (no), HTTP persistent connections (not applicable), HTTP/2 PING (no), WebSocket ping/pong and application heartbeats (yes).</details>

10. After a WebSocket upgrade, what exactly is YARP doing with the traffic? (§9.3)
    <details><summary>Answer</summary>Running two copy loops over two opaque byte streams (client→destination and destination→client), restarting an activity timer on every successful read or write.</details>

11. Why do browser clients plus a default ASP.NET Core server hit the 100-second cut-off? (§8.4)
    <details><summary>Answer</summary>Browsers can't send pings, and the server's default keep-alive interval (2 minutes) is longer than YARP's default ActivityTimeout (100 s). No bytes flow for 100 s, so YARP closes the connection.</details>

12. What's the difference between the `HttpClient` and `HttpRequest` sections of a YARP cluster? (§10.1)
    <details><summary>Answer</summary><code>HttpClient</code> configures outbound connections (<code>SocketsHttpHandler</code>: TLS, pooling, proxies). <code>HttpRequest</code> configures each forwarded request (<code>ForwarderRequestConfig</code>: ActivityTimeout, version, version policy).</details>

13. A route has `Timeout: 00:05:00` and its cluster keeps the default ActivityTimeout. An idle WebSocket on that route: when is it closed? (§10.6)
    <details><summary>Answer</summary>At about 100 seconds. Route/request timeouts are disabled after the WebSocket handshake, but ActivityTimeout still applies.</details>

14. Why is "raise ActivityTimeout to 24 hours on the main cluster" a bad fix? (§10.8, §13)
    <details><summary>Answer</summary>Dead connections accumulate for hours, and it weakens the hang detection for every normal request on that cluster. Prefer endpoint keep-alives, or a dedicated WebSocket cluster.</details>

15. Where does the documentation fix for #1764 go, and what's the specific gap? (§12.1)
    <details><summary>Answer</summary><code>dotnet/AspNetCore.Docs</code>, <code>aspnetcore/fundamentals/servers/yarp/websockets.md</code>. The WebSockets page doesn't mention ActivityTimeout or keep-alives, and gives no how-to for servers, .NET clients, or browsers.</details>

---

## 16. Sources

Checked 2026-09-26.

**The issue and YARP docs**
- [dotnet/yarp#1764: Doc WebSocket keep-alive requirement](https://github.com/dotnet/yarp/issues/1764)
- [YARP: Proxying WebSockets and SPDY (Learn)](https://learn.microsoft.com/en-us/aspnet/core/fundamentals/servers/yarp/websockets?view=aspnetcore-10.0) · [source: websockets.md](https://github.com/dotnet/AspNetCore.Docs/blob/main/aspnetcore/fundamentals/servers/yarp/websockets.md)
- [YARP request timeouts (Learn)](https://learn.microsoft.com/en-us/aspnet/core/fundamentals/servers/yarp/timeouts?view=aspnetcore-10.0) · [source: timeouts.md](https://github.com/dotnet/AspNetCore.Docs/blob/main/aspnetcore/fundamentals/servers/yarp/timeouts.md)
- [YARP HTTP client configuration](https://dotnet.github.io/yarp/articles/http-client-config.html)
- [Migrate YARP docs to AspNetCore.Docs (#34650)](https://github.com/dotnet/AspNetCore.Docs/issues/34650)
- [Discussion: "reverse-proxy timeout how to set?" (#2183)](https://github.com/microsoft/reverse-proxy/discussions/2183) · [Issue: "YARP keep terminating the WebSocket after around 2 minutes" (#2615)](https://github.com/microsoft/reverse-proxy/issues/2615) · [Strange Behaviour with Activity Timeout (#2298)](https://github.com/dotnet/yarp/issues/2298) · [Set timeout for HttpForwarder (#2207)](https://github.com/dotnet/yarp/issues/2207)
- [dotnet/yarp repository](https://github.com/dotnet/yarp)

**WebSockets in .NET**
- [WebSockets support in ASP.NET Core (KeepAliveInterval default 2 minutes, KeepAliveTimeout)](https://learn.microsoft.com/en-us/aspnet/core/fundamentals/websockets?view=aspnetcore-10.0)
- [WebSockets support in .NET (ClientWebSocket keep-alive strategies, HTTP/2 WebSockets)](https://learn.microsoft.com/en-us/dotnet/fundamentals/networking/websockets)
- [ClientWebSocketOptions.KeepAliveTimeout](https://learn.microsoft.com/en-us/dotnet/api/system.net.websockets.clientwebsocketoptions.keepalivetimeout?view=net-10.0) · [WebSocketOptions.KeepAliveInterval](https://learn.microsoft.com/en-us/dotnet/api/microsoft.aspnetcore.builder.websocketoptions.keepaliveinterval?view=aspnetcore-10.0)
- [SignalR HubOptions.KeepAliveInterval](https://learn.microsoft.com/en-us/dotnet/api/microsoft.aspnetcore.signalr.huboptions.keepaliveinterval?view=aspnetcore-10.0)

**Protocols**
- [RFC 6455: The WebSocket Protocol](https://www.rfc-editor.org/rfc/rfc6455.html) · [RFC 8441: Bootstrapping WebSockets with HTTP/2](https://datatracker.ietf.org/doc/html/rfc8441) · [RFC 7230 §6.7: HTTP/1.1 Upgrade](https://datatracker.ietf.org/doc/html/rfc7230#section-6.7)

---

*End of Lecture 005. Next: do the §11 lab this week, then §12's Step 1 comment. The "Generic Host & DI, in depth" lecture moves to 006.*
