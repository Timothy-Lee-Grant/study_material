# Lecture 1: HTTP — From the Wire to the Application

Series: YARP Learning Series
Prepares you for: reading YARP's `ProxyHttpClient`, `HttpRequestConfig`, transforms, and the forwarder pipeline with actual comprehension instead of pattern-matching on class names.

---

## 1. Learning Objectives

By the end of this lecture you should be able to:

1. Explain what HTTP actually is (a message format + a set of semantics, not "the internet").
2. Trace a request from a browser typing a URL all the way to bytes hitting a server process, and correctly say *which parts are HTTP and which parts are not*.
3. Read a raw HTTP/1.1 message and explain every line in it.
4. Explain why HTTP/1.1 struggles under high concurrency, and what specific mechanism (head-of-line blocking) causes that.
5. Explain what problem HTTP/2 solves and how (multiplexing over one TCP connection) — and why that *still* wasn't enough, which is what HTTP/3 fixes.
6. Explain why a reverse proxy has to actively understand HTTP — it cannot just "copy bytes" — and give concrete examples of decisions YARP has to make about headers, bodies, status codes, and connections.
7. Reason about latency, throughput, timeouts, and cancellation as engineering trade-offs, not vocabulary.

---

## 2. Prerequisite Concepts

You said you're comfortable with APIs and backend development, so I'll skip "what is a request." But a few things sit *underneath* HTTP that you need before HTTP/1.1 vs 2 vs 3 will make sense. I'll teach these briefly — just enough mechanism, not a networking course.

### 2.1 IP, ports, and sockets

Every machine on a network has an **IP address** (e.g., `142.250.80.14`). That gets you to the *machine*. A single machine runs many programs that might want network traffic (a web server, an SSH daemon, a database). To distinguish them, each program listens on a **port** — a number from 0–65535. `example.com:443` means "the machine at this address, port 443" (443 is the conventional HTTPS port).

A **socket** is the OS-level handle representing one endpoint of a network connection — think of it like a file descriptor, but for a network conversation instead of a file. When your application "opens a connection," what's actually happening is the OS creates a socket, and the two ends (client socket, server socket) agree to exchange bytes.

**Why this matters for YARP:** YARP maintains pools of sockets/connections to backend servers. Understanding that a "connection" is a real, stateful OS resource (not a free abstraction) is why connection reuse is a big deal later in this lecture.

### 2.2 TCP: a reliable, ordered byte stream

Most HTTP (versions 1.1 and 2) runs on top of **TCP** (Transmission Control Protocol). TCP's job is: given two endpoints, deliver a stream of bytes reliably, in order, exactly once, even though the underlying network (IP) only promises "best effort, packets may be lost, duplicated, or reordered."

TCP achieves this with:
- **Sequence numbers** on every byte, so the receiver can detect loss and reordering.
- **Acknowledgments (ACKs)** — the receiver tells the sender what it has received.
- **Retransmission** — if an ACK doesn't arrive in time, the sender resends.
- **The three-way handshake** to establish a connection before any data flows:

```
Client                          Server
  |------------ SYN ------------->|      "I want to talk"
  |<--------- SYN-ACK -------------|      "OK, I hear you, go ahead"
  |------------ ACK -------------->|      "Confirmed"
  |                                |
  |   (connection now established, both sides can send bytes)
```

That round trip costs real time — typically one full network round-trip (RTT) before a single byte of your actual request is sent. If the connection also needs TLS (HTTPS), that's *additional* round trips on top (conceptually: 1 more RTT for TLS 1.3, 2 more for TLS 1.2).

**Why this matters:** this handshake cost is the entire reason "connection reuse" is a headline performance concept in HTTP, and it's the entire reason HTTP/3 redesigns the handshake. If connections were free to open, nobody would care about keep-alive.

### 2.3 UDP (just enough to understand HTTP/3 later)

**UDP** (User Datagram Protocol) is the other main transport. It sends individual packets ("datagrams") with *no* guarantee of delivery, ordering, or duplicate-prevention, and *no* handshake — you just send. It's faster to start and has no built-in head-of-line blocking behavior, because it doesn't try to keep anything in order for you. HTTP/3 uses UDP as its foundation — I'll explain why later, once you've seen why TCP becomes a liability at the HTTP/2 layer.

### 2.4 TLS, briefly

TLS (what makes HTTP "HTTPS") encrypts the byte stream and verifies server identity via certificates. I am not going to teach TLS internals here — for this series, you only need to know:
- TLS sits between TCP and HTTP (or between UDP and HTTP in HTTP/3's case).
- Establishing TLS costs extra round trips before any HTTP bytes flow.
- A proxy like YARP often has to *terminate* TLS (decrypt client traffic) and then decide whether to *re-encrypt* a new TLS connection to the backend or talk plaintext internally. That's a real architectural decision you'll see in YARP configuration.

That's all the transport-layer background you need. Now, HTTP itself.

---

## 3. Core Mental Model

Here's the one sentence to hold onto for this entire lecture:

> **HTTP is a text-shaped (or, in HTTP/2+, binary-framed) agreement about how to format a request for something and a response to it, layered on top of a connection that some other protocol (TCP or QUIC) already established.**

HTTP does not create connections. HTTP does not route packets. HTTP does not know about IP addresses in any deep way. HTTP's entire job is: **given that two programs can already exchange bytes reliably, here is the shape those bytes must take so both sides agree on what's being asked for and what's being answered.**

Everything in this lecture is really about two things:
1. **The message format** — how a request/response is structured (headers, body, status, etc.) — this is what stays *conceptually* stable across HTTP/1.1, 2, and 3.
2. **The delivery mechanics** — how those messages actually get multiplexed over connections — this is what changes dramatically across versions, and it's what YARP has to be deeply aware of.

---

## 4. HTTP Fundamentals — The Message

I'll use one running example throughout this lecture so the abstractions stay grounded: a frontend app calling `GET https://api.contoso.com/v1/users/42` with an auth token, to fetch a user profile, through a reverse proxy (eventually YARP) in front of an ASP.NET Core backend.

### 4.1 What HTTP actually is

HTTP (HyperText Transfer Protocol) is an **application-layer, request/response, stateless, text-originated protocol**. Let's unpack each word because each one is load-bearing:

- **Application-layer**: it's the top of the stack — the thing your code actually constructs and reads. Below it: TCP/QUIC (transport), IP (network), Ethernet/Wi-Fi (link).
- **Request/response**: a client sends a request; a server sends back exactly one response to that request. (HTTP/2 technically allowed "server push," extra unsolicited responses, but it's been deprecated/removed from browsers — don't spend time on it.)
- **Stateless**: the protocol itself has no memory of previous requests. The server doesn't inherently know that request #2 came from the same client as request #1. (Cookies and tokens are how *applications* fake state on top of a stateless protocol — more on this below.)
- **Text-originated**: HTTP/1.1 messages are literally human-readable ASCII text. HTTP/2 and HTTP/3 moved to binary framing for efficiency, but the *conceptual* fields (method, headers, status, body) are identical — they're just encoded differently on the wire.

### 4.2 Client/server architecture

One side initiates (the **client**) — it opens the connection and sends the first message. The other side (the **server**) listens on a port, accepts connections, and responds. This is asymmetric: a server cannot spontaneously send your browser a request. This asymmetry is exactly why WebSockets and Server-Sent Events exist as *separate* mechanisms — HTTP alone can't do server-initiated pushes to a browser.

In your running example: your frontend app is the client. `api.contoso.com` is the server *as far as the frontend is concerned*. But once YARP enters the picture, YARP is simultaneously:
- **a server**, from the frontend's point of view (it accepts the incoming connection and looks like `api.contoso.com`)
- **a client**, from the backend's point of view (it opens its own connection to the real backend and sends its own request)

This dual role — being a server on one side and a client on the other, for the *same logical request* — is the single most important architectural fact about what a reverse proxy is. Hold onto it; it explains almost everything about how YARP is built.

### 4.3 A raw HTTP/1.1 request, line by line

Forget SDKs for a second. This is literally what goes over the wire (I'm using `\r\n` explicitly because that's the actual required line terminator in the spec — not just `\n`):

```
GET /v1/users/42 HTTP/1.1\r\n
Host: api.contoso.com\r\n
Authorization: Bearer eyJhbGciOi...\r\n
Accept: application/json\r\n
User-Agent: MyApp/1.0\r\n
Connection: keep-alive\r\n
\r\n
```

Breaking this down:

- **Request line**: `GET /v1/users/42 HTTP/1.1` — method, path, HTTP version. This is the only line that isn't a header.
- **Headers**: `Name: Value` pairs, one per line. Order mostly doesn't matter semantically (with rare exceptions), but duplicates of certain headers are meaningful (e.g., multiple `Set-Cookie` headers in a response).
- **Blank line (`\r\n\r\n`)**: this is the delimiter that says "headers are done." Nothing subtle here — it's just how the parser knows where headers end and body begins.
- **Body**: for a `GET`, there usually isn't one. If there were, it would start immediately after that blank line.

A response looks structurally similar:

```
HTTP/1.1 200 OK\r\n
Content-Type: application/json\r\n
Content-Length: 87\r\n
Connection: keep-alive\r\n
\r\n
{"id":42,"name":"Ada Lovelace","email":"ada@contoso.com","role":"engineer"}
```

- **Status line**: `HTTP/1.1 200 OK` — version, status code, human-readable reason phrase (the reason phrase is cosmetic; software should key off the numeric code).
- **Headers**, same shape as request headers.
- **Blank line**, then **body**.

Notice: this is *just text*. Any program that can read/write bytes over a TCP connection and knows this format can speak HTTP. That's the whole trick — it's a simple, universally-implementable contract.

### 4.4 HTTP methods (verbs)

The method tells the server **what kind of operation** this is. The two properties that actually matter for engineering (not just trivia) are:

- **Safe**: does this method have side effects? (`GET`, `HEAD`, `OPTIONS` are safe — they should never change server state.)
- **Idempotent**: does calling it N times have the same effect as calling it once? (`GET`, `PUT`, `DELETE` are idempotent. `POST` is *not*.)

| Method | Safe | Idempotent | Typical use |
|---|---|---|---|
| GET | yes | yes | fetch a resource |
| HEAD | yes | yes | like GET but headers only, no body — used to check existence/size without downloading |
| POST | no | no | create a resource, or any non-idempotent action |
| PUT | no | yes | replace a resource entirely |
| PATCH | no | no (by spec, though often implemented idempotently) | partially update a resource |
| DELETE | no | yes | remove a resource |
| OPTIONS | yes | yes | ask what methods/headers are allowed (used heavily by CORS preflight) |

**Why idempotency matters for a proxy:** if a request to the backend times out, is it *safe to automatically retry*? For a `GET`, yes — retrying can't cause harm. For a `POST` (e.g., "charge this credit card"), automatically retrying could double-charge the user. YARP's retry/failover logic has to respect this distinction; it is not free to retry blindly just because a connection failed.

### 4.5 URLs and URIs

`https://api.contoso.com:443/v1/users/42?include=roles#section`

- **Scheme**: `https` — also implicitly tells you the default port (443) and that TLS is used.
- **Host**: `api.contoso.com` — used for DNS resolution *and* sent again in the `Host` header (yes, both — DNS resolution happens before any HTTP bytes are sent, but the server still needs to know which hostname you meant, because one server/IP can host many domains).
- **Port**: `443` (optional if it's the scheme default).
- **Path**: `/v1/users/42` — identifies the resource, as far as the *application* is concerned. HTTP itself doesn't know what a path "means"; that's entirely up to the server's routing logic.
- **Query string**: `?include=roles` — key/value pairs, conventionally used for filtering/options, not identity.
- **Fragment**: `#section` — this is purely client-side (browser scrolls to an anchor). **Critically: the fragment is never sent to the server at all.** It's stripped before the request is even constructed. This trips people up constantly.

**URI vs URL**: URI (Uniform Resource *Identifier*) is the general concept — "a string that identifies a resource." URL (Uniform Resource *Locator*) is a URI that also tells you *how to get it* (scheme + host). In casual conversation and in YARP's own code/docs, these are used almost interchangeably; don't lose sleep over the distinction.

### 4.6 Headers

Headers are metadata about the request or response — everything that *isn't* the actual payload but describes it, controls it, or authenticates it. Some categories worth knowing by function rather than memorizing a list:

- **Routing/identity**: `Host` — which virtual server you mean.
- **Content description**: `Content-Type` (what format the body is in), `Content-Length` (how many bytes the body is).
- **Negotiation**: `Accept` (what formats the client can handle in the response), `Accept-Encoding` (what compression the client supports, e.g. `gzip`).
- **Auth**: `Authorization`.
- **Caching**: `Cache-Control`, `ETag`, `If-None-Match`.
- **Connection behavior**: `Connection: keep-alive`, `Connection: close`.
- **Proxy-specific**: `X-Forwarded-For`, `X-Forwarded-Proto`, `X-Forwarded-Host`, `Via` — these exist *specifically* because proxies exist. I'll come back to these in the YARP section because they are one of the most concrete things YARP touches.

Headers are how HTTP stays extensible without changing the protocol itself — need to convey new metadata? Add a header. This is also exactly why a reverse proxy's job is nontrivial: it has to decide, header by header, "do I forward this as-is, rewrite it, add to it, or strip it?"

### 4.7 Request bodies and response bodies

The body is the actual payload — JSON, form data, a file upload, an HTML page, binary data, whatever. Two things determine how a receiver knows where the body ends:

1. **`Content-Length: N`** — "the body is exactly N bytes, stop reading after that many."
2. **`Transfer-Encoding: chunked`** — "I don't know the total length up front, so I'll send it in labeled chunks and a terminating marker tells you when it's done." (Full mechanics in §6.4.)

A request/response body is optional — `GET` requests conventionally have none, `POST`/`PUT`/`PATCH` typically do, `DELETE` sometimes does. There's no protocol-level restriction preventing a `GET` from having a body, but it's discouraged and many implementations (including some HTTP libraries and caches) don't support it well — treat it as "don't."

### 4.8 Status codes

Grouped by first digit — this grouping is meaningful and worth internalizing, because *code that branches on status* usually branches on the class, not the exact number:

- **1xx — Informational**: rare to touch directly (`100 Continue` is the notable one — a client can ask "should I bother sending this large body?" before sending it).
- **2xx — Success**: `200 OK`, `201 Created`, `204 No Content` (success, but no body — common for DELETE).
- **3xx — Redirection**: "the resource is somewhere else, go there" (§4.11).
- **4xx — Client error**: the *client* did something wrong — `400 Bad Request`, `401 Unauthorized` (not authenticated), `403 Forbidden` (authenticated but not allowed), `404 Not Found`, `429 Too Many Requests`.
- **5xx — Server error**: the *server* did something wrong — `500 Internal Server Error`, `502 Bad Gateway` (a proxy got an invalid response from upstream), `503 Service Unavailable`, `504 Gateway Timeout`.

**502, 503, and 504 deserve special attention right now**, because these are the codes a reverse proxy *itself* generates, not the backend. If YARP can't reach the backend at all, or the backend sends garbage, YARP returns `502`. If YARP has no healthy backend to send to, `503`. If the backend takes too long, `504`. Recognizing these as "the proxy talking about itself" (as opposed to the application talking about the request) will directly help you read YARP source later.

### 4.9 Content types (and negotiation)

`Content-Type: application/json` tells the receiver how to *parse* the body — is it JSON, HTML, a JPEG, form-encoded data, raw binary? Format: `type/subtype`, e.g. `application/json`, `text/html`, `image/png`, `application/octet-stream` (generic binary).

**Content negotiation** is the client saying, via the `Accept` header, "here's what I can understand, in preference order" — e.g. `Accept: application/json, text/html;q=0.8` (the `q` value is a preference weight). The server picks the best match it can produce. This matters for a proxy mainly in the sense that YARP generally does *not* rewrite bodies or negotiate content on the application's behalf — it's usually a "dumb pipe" for the body while being a "smart router" for everything about *where the request goes*. That distinction is worth sitting with.

### 4.10 Cookies

Since HTTP is stateless, cookies are the mechanism applications use to *fake* statefulness. Mechanism:

1. Server sends `Set-Cookie: session=abc123; HttpOnly; Secure; SameSite=Strict` in a response.
2. The client (browser) stores it and automatically attaches `Cookie: session=abc123` on every *subsequent* request to that same domain (subject to path/domain/expiry rules).
3. The server looks up `abc123` in its own session store to know "which user is this."

The cookie itself is just an opaque token from HTTP's point of view — the *meaning* ("this identifies a logged-in session") is entirely an application-layer convention, not something HTTP understands.

### 4.11 Authentication headers

Two you'll see constantly:

- `Authorization: Basic base64(username:password)` — credentials sent (base64-encoded, **not encrypted** — this is only safe over TLS) on every request.
- `Authorization: Bearer <token>` — the modern default (JWTs, OAuth access tokens). "Bearer" literally means "whoever holds this token is authorized" — there's no additional proof required, which is exactly why these tokens must be protected in transit (TLS) and have short lifetimes.

A proxy generally forwards the `Authorization` header through unchanged (it's not the proxy's job to authenticate on the application's behalf, usually) — but YARP *can* be configured to strip, inspect, or require auth at the proxy layer itself, which is a real architectural choice (auth at the edge vs auth at the service).

### 4.12 Redirects

A `3xx` response tells the client "go elsewhere," using the `Location` header to say where:

```
HTTP/1.1 301 Moved Permanently
Location: https://api.contoso.com/v2/users/42
```

- `301 Moved Permanently` — update your bookmarks/links, this is forever.
- `302 Found` / `307 Temporary Redirect` — just for now.
- `308 Permanent Redirect` — like 301 but strictly preserves the method (301 historically allowed clients to switch POST→GET on redirect, which surprised people; 307/308 exist to remove that ambiguity).

The client (browser or HTTP library) is responsible for *following* redirects by issuing a brand new request to the new URL — the original server is done once it sends the 3xx. This is worth noticing: **a redirect is not a proxy**. The original server's job ends the moment it says "go over there." A reverse proxy is fundamentally different: YARP doesn't tell the client to go elsewhere — it forwards the request itself and returns the backend's response as if it had produced it. That distinction (tell the client to redo the work, vs. do the work on the client's behalf and hand back the result) is one of the clearest ways to understand what a proxy structurally *is*.

---

## 5. The HTTP Request Lifecycle

Now let's walk through the *entire* trip, and be explicit about the boundary between "HTTP" and "everything HTTP depends on."

```
 ┌────────┐                                                        ┌────────┐
 │ Client │                                                        │ Server │
 └───┬────┘                                                        └───┬────┘
     │                                                                 │
     │ 1. DNS lookup: "api.contoso.com" -> 203.0.113.10   [NOT HTTP]   │
     │─────────────────────────────────────────────────────>          │
     │                                                                 │
     │ 2. TCP three-way handshake to 203.0.113.10:443     [NOT HTTP]   │
     │<===============================================================>│
     │                                                                 │
     │ 3. TLS handshake (cert exchange, key agreement)    [NOT HTTP]   │
     │<===============================================================>│
     │                                                                 │
     │ 4. Client writes HTTP request bytes onto the           [HTTP]   │
     │    now-open, now-encrypted TCP connection                       │
     │────────────────────────────────────────────────────────────────>│
     │                                                                 │
     │                                          5. Server's HTTP layer │
     │                                             parses the request  │
     │                                             (method/path/headers)
     │                                                                 │
     │                                          6. Server hands parsed │
     │                                             request to the      │
     │                                             APPLICATION         │
     │                                             (your route handler,│
     │                                             controller, etc.)   │
     │                                                       [NOT HTTP]│
     │                                                                 │
     │                                          7. Application returns │
     │                                             data; HTTP layer    │
     │                                             serializes it into  │
     │                                             a response  [HTTP]  │
     │                                                                 │
     │ 8. Server writes HTTP response bytes back on the       [HTTP]   │
     │    same TCP connection                                          │
     │<────────────────────────────────────────────────────────────────│
     │                                                                 │
     │ 9. Client's HTTP layer parses response,             [HTTP]      │
     │    hands parsed data to application code                        │
     │                                                    [NOT HTTP]   │
```

The precise takeaway: **HTTP is only steps 4, 5, 7, 8, 9.** DNS (step 1) is a completely separate protocol/system (translates names to IP addresses — nothing to do with HTTP's message format). TCP + TLS (steps 2–3) establish and secure the pipe HTTP will use — HTTP doesn't know or care how the bytes get from A to B reliably, it just assumes they do. And what your application code *does* with a parsed request (step 6) is business logic, not HTTP.

This separation is exactly why HTTP/3 can swap TCP for QUIC (over UDP) without changing what a "request" or "response" *means* — because the message semantics (steps 4/5/7/8/9) are a separate layer from the transport (steps 2/3). This decoupling is the single most useful thing to understand before HTTP/2 and HTTP/3 make sense.

---

## 6. HTTP/1.1

HTTP/1.1 (1997) is still the version most people mentally default to — text-based, one logical request/response cycle at a time on a connection. Its main innovations over HTTP/1.0 were about *not* paying the TCP handshake cost on every single request.

### 6.1 Persistent connections & Keep-Alive

In HTTP/1.0, the default was: open a TCP connection, send one request, get one response, **close the connection**. If your page needed 20 assets (HTML, CSS, images), that's 20 TCP handshakes (and 20 TLS handshakes, if HTTPS). Given each handshake costs a round trip, this is brutally slow.

HTTP/1.1 makes persistent connections the **default**: after a response, the connection stays open, and the client can send another request over the *same* connection. The header `Connection: keep-alive` is the (now largely redundant, since it's default in 1.1) signal for this. `Connection: close` tells the other side "actually, close it after this."

```
One connection, HTTP/1.1, persistent:

  Client                                Server
    │──── GET /style.css ─────────────────>│
    │<─────────── 200 OK, css body ─────────│
    │                                       │   (connection stays open)
    │──── GET /logo.png ───────────────────>│
    │<─────────── 200 OK, png body ─────────│
    │                                       │   (connection stays open)
    │──── GET /app.js ─────────────────────>│
    │<─────────── 200 OK, js body ──────────│
```

**Why this matters for a proxy:** connection reuse isn't just a client-facing browser optimization. YARP maintains and reuses its *own* pool of connections to each backend, for exactly the same reason — opening a new TCP+TLS connection to the backend for every incoming request would be catastrophically slow and would exhaust backend resources at any real scale.

### 6.2 Request/response semantics — strictly serial per connection

Here's the critical limitation: on a single HTTP/1.1 connection, requests and responses must go **one at a time, in order**. The client can't say "here's request A, then request B" and get responses back in any order or interleaved — the server *must* respond to A completely before B's response can be sent (technically the client *can* send A and B back-to-back without waiting — that's called "pipelining" — but the responses must still come back strictly in order, and pipelining is so poorly supported and fragile in practice that virtually nobody uses it; treat it as a historical footnote, not something you need to reason about further).

**This is where "head-of-line blocking" comes from — memorize this mechanism, not just the term.**

```
Single HTTP/1.1 connection, no pipelining (the realistic case):

  Client                                          Server
    │──── GET /slow-report ────────────────────────>│
    │                                                │  (this request takes 3 seconds
    │                 ... waiting ...                │   to process on the server)
    │                                                │
    │<─────────────── 200 OK (after 3s) ──────────────│
    │──── GET /fast-ping ──────────────────────────>│   <- couldn't even be SENT
    │<─────────────── 200 OK (instant) ───────────────│      until the slow one finished
```

Even though `/fast-ping` would be instant, it's stuck behind `/slow-report` because they share one connection and HTTP/1.1 can't interleave them. This is **head-of-line (HOL) blocking at the connection level**.

### 6.3 The workaround: connection parallelism

Browsers historically worked around this by opening **multiple parallel connections per host** (historically 6 was a common browser limit) — so up to 6 requests could genuinely be in flight simultaneously. This "fixes" the symptom but at real cost: each connection is its own TCP handshake, its own TLS handshake, its own congestion-control state, and — critically for you — its own resource footprint on the *server* (and on YARP, sitting between them). This tension (need parallelism, but connections are expensive) is precisely the problem HTTP/2 was designed to solve properly instead of working around.

### 6.4 Content-Length vs. chunked transfer encoding

The server needs to tell the client where the body ends. Two mechanisms:

**Content-Length** — simplest case, you know the size up front:
```
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 87

{"id":42,"name":"Ada Lovelace", ...}
```
The receiver reads exactly 87 bytes after the blank line, then knows the message is complete.

**Chunked transfer encoding** — used when the server *doesn't* know the total size ahead of time (e.g., it's generating a large report row-by-row, or streaming data from a database, or proxying a response it hasn't fully received yet):

```
HTTP/1.1 200 OK
Content-Type: text/plain
Transfer-Encoding: chunked

7\r\n
Mozilla\r\n
9\r\n
Developer\r\n
0\r\n
\r\n
```

Each chunk is prefixed by its length in hex, followed by that many bytes, repeated, and terminated by a zero-length chunk (`0\r\n\r\n`). This is exactly what enables **streaming**: the server can start sending bytes to the client before it has finished producing the whole response — no need to buffer the entire payload in memory first.

**Why this matters enormously for a proxy:** YARP frequently does not — and often *cannot* — know the size of a backend's response ahead of time, especially with chunked upstream responses. It needs to correctly relay chunked encoding (or re-chunk, or convert between HTTP/1.1 chunking and HTTP/2's native streaming, depending on which protocol it's speaking to the client vs. the backend). Get this wrong and you either buffer huge responses fully in memory (bad) or corrupt the stream (worse).

### 6.5 Limitations of HTTP/1.1, summarized

- Head-of-line blocking per connection (fundamental protocol limitation, not an implementation bug).
- Workaround (multiple parallel connections) is expensive on both ends and doesn't scale cleanly.
- Headers are sent as plain, repeated text on every request — no compression — which is wasteful, especially with today's large header sets (cookies, auth tokens, tracing headers).
- No way to prioritize one in-flight request over another.

---

## 7. HTTP/2

HTTP/2 (2015) keeps the *same semantics* — methods, headers, status codes, bodies all mean the same thing — but completely redesigns how messages are packaged and delivered over the connection. This is the most important thing to internalize: **HTTP/2 is not a new protocol conceptually, it's a new transport encoding for the same request/response model.**

### 7.1 Binary framing

Instead of human-readable text, HTTP/2 breaks every message into small binary **frames**. A frame has a type (`HEADERS`, `DATA`, `SETTINGS`, `WINDOW_UPDATE`, etc.), a length, flags, and a **stream ID**. Frames are the atomic unit sent over the connection — a full request or response is reassembled from a sequence of frames.

### 7.2 Streams and multiplexing — the actual fix for HOL blocking

A **stream** is a logical, independent, bidirectional sequence of frames representing one request/response exchange, identified by a **stream ID**. Multiple streams share a single TCP connection, and their frames can be **interleaved**:

```
One HTTP/2 connection, multiplexed:

  Client                                                Server
    │── HEADERS(stream 1, GET /slow-report) ─────────────>│
    │── HEADERS(stream 3, GET /fast-ping) ────────────────>│
    │                                                       │
    │<───────── DATA(stream 3, fast-ping result) ───────────│   <- arrives immediately,
    │                                                       │      NOT blocked by stream 1
    │<── DATA(stream 1, partial slow-report bytes) ─────────│
    │<── DATA(stream 1, more slow-report bytes) ────────────│
    │<── DATA(stream 1, final slow-report bytes) ───────────│
```

This is the actual, structural fix for the HOL blocking problem from §6.2 — not a workaround, a redesign. One TCP connection, many concurrent logical exchanges, and a slow one no longer blocks a fast one *at the HTTP layer*. (Hold that last qualifier — "at the HTTP layer" — it's going to matter a lot in §8.)

### 7.3 Connection-level vs. stream-level behavior

Some things in HTTP/2 apply to the whole connection; others apply per-stream. This distinction matters when you eventually read flow-control or configuration code:

- **Connection-level**: the underlying TCP socket, overall connection flow-control window, `SETTINGS` frames (negotiated capabilities like max concurrent streams).
- **Stream-level**: each individual request/response has its own state machine (idle → open → half-closed → closed), its own flow-control window, and can be independently cancelled (`RST_STREAM`) without tearing down the whole connection.

That last point is a real, practical feature: a client can cancel a single in-flight request without killing every other in-flight request sharing that connection — something impossible to do cleanly in HTTP/1.1 without closing the whole connection.

### 7.4 Header compression (HPACK) — conceptually

Headers are repetitive across requests on the same connection — same `Host`, same `User-Agent`, same cookies, over and over. HPACK maintains a **shared compression table** on both sides of the connection, so repeated header names/values get replaced with small references instead of being retransmitted as full text every time. You don't need the compression algorithm's internals — just know: **this is why HTTP/2 headers are efficient even though they still carry the same semantic information as HTTP/1.1 headers.**

### 7.5 Why HTTP/2 exists — summary

Solve HOL blocking and header redundancy *without* requiring dozens of parallel TCP connections, by multiplexing many logical streams over one physical connection, and compressing the repetitive metadata.

### 7.6 Mental model shift, explicitly

| | HTTP/1.1 | HTTP/2 |
|---|---|---|
| Unit sent on the wire | full text messages, in order | small binary frames, interleaved |
| Concurrency | multiple TCP connections | multiple streams, one TCP connection |
| Headers | retransmitted in full every time | compressed via shared table |
| Cancel one request | must close the whole connection | `RST_STREAM`, connection stays alive |

---

## 8. HTTP/3

HTTP/3 (standardized 2022) keeps going in the same direction — but it makes a transport-layer change that surprises people the first time they see it: **it drops TCP entirely** and runs over **QUIC**, which sits on **UDP**.

### 8.1 The problem HTTP/2 didn't actually solve

Go back to §7.2's diagram. HTTP/2 fixed HOL blocking *at the HTTP layer* — multiple streams, no HTTP-level blocking. But all those streams still ride on a **single TCP connection**. And TCP itself guarantees strictly ordered, reliable delivery of *the entire byte stream* — it has no concept of "streams" at all; from TCP's point of view, it's all just one sequence of bytes.

So: if a single TCP packet is lost, TCP will not deliver *any* bytes after that point — even bytes belonging to a completely unrelated HTTP/2 stream that arrived just fine — until the lost packet is retransmitted and confirmed. **This is TCP-level head-of-line blocking**, and it undermines the whole benefit of HTTP/2 multiplexing whenever there's any packet loss (which is common and expected on real networks, especially mobile/Wi-Fi):

```
TCP connection carrying HTTP/2 streams 1, 3, 5:

  [pkt: stream1 data][pkt: stream3 data][pkt: LOST][pkt: stream5 data][pkt: stream1 data]
                                            ^
                             TCP withholds EVERYTHING after this point —
                             including the already-arrived stream5 and stream1 packets —
                             until the lost packet is retransmitted.
```

You built a beautiful multiplexed protocol at the HTTP layer, and TCP (below it, oblivious to "streams" as a concept) reintroduces blocking anyway.

### 8.2 QUIC's answer: multiplexing at the transport layer itself

QUIC is a transport protocol (like TCP) but built from scratch on top of UDP, and — critically — QUIC **natively understands the concept of independent streams**. Loss of a packet belonging to one QUIC stream only blocks *that stream*; other streams' packets, even if received later in real time, can be delivered to the application immediately. The multiplexing that HTTP/2 tried to bolt onto TCP is instead built into the transport itself.

### 8.3 Why build on UDP instead of just "fixing" TCP?

TCP's ordering/reliability guarantees are implemented deep in operating system kernels and decades of network middleboxes (firewalls, NATs, load balancers) that assume "TCP behaves like TCP." You cannot practically change TCP's fundamental in-order-delivery guarantee without breaking a huge amount of existing infrastructure and requiring OS-level rollout across the entire internet. UDP, by contrast, is deliberately minimal — no ordering, no reliability, no handshake — a nearly blank slate. QUIC implements its *own* reliability, ordering (per-stream, not connection-wide), congestion control, and encryption entirely in user-space (as a library), on top of that blank slate. This means QUIC can evolve much faster than TCP ever could, without needing OS/kernel updates.

### 8.4 Faster connection establishment

Recall from §2.2: TCP handshake (1 RTT) + TLS handshake (1–2 more RTTs) before any HTTP bytes flow. QUIC integrates the transport handshake *and* the TLS 1.3 handshake into a single combined handshake, and for servers you've connected to recently, it supports **0-RTT** — resuming a previous connection's security parameters well enough to send actual request data in the very first packet. Fewer round trips before useful work starts.

### 8.5 What you don't need to master here

You do **not** need to understand QUIC's internal congestion control, its packet-loss recovery algorithms, or its wire format. For this series, the load-bearing facts are:
- HTTP/3 = HTTP semantics (same methods/headers/status/bodies) + QUIC transport (over UDP).
- QUIC exists specifically to fix TCP-level HOL blocking that undermined HTTP/2's multiplexing.
- It changes *transport*, not *meaning* — a request is still a request.

---

## 9. Streaming

You've already seen the mechanism (chunked encoding, §6.4) — this section is about *why it matters operationally*.

**The core idea**: instead of a server (or proxy) fully reading a request body into memory, then fully processing it, then fully writing a response body into memory before sending anything — streaming means data flows through in bounded-size pieces as it becomes available, in both directions.

```
NON-STREAMING (buffered) — dangerous at scale:

  Backend produces 2GB report
       │
       ▼
  [ Entire 2GB held in server RAM ]
       │
       ▼
  Only then does it start being sent to the client

STREAMING:

  Backend produces report in small pieces
       │
       ▼
  [ small buffer, e.g. 64KB ]───► sent to client ───► [ small buffer ] ───► ...
       │
       ▼
  Memory usage stays roughly constant regardless of total size
```

**Why this matters for high-volume systems**: imagine 1,000 concurrent clients each downloading a 500MB file, non-streamed. That's potentially 500GB of server RAM just holding response bodies in flight — the server falls over long before that, from memory pressure alone, even though the CPU work is trivial. With streaming, memory use per request stays roughly constant (bounded by buffer size), so the limiting factor becomes something much more reasonable, like network bandwidth or connection count.

**Backpressure** is the companion concept: if the client is reading slowly (slow network, slow disk), the server needs a way to *pause* producing more data rather than buffering unboundedly waiting for the client to catch up. HTTP/2 and HTTP/3's flow-control windows (mentioned in §7.3) are exactly this mechanism, formalized at the protocol level — a receiver advertises how much it's willing to buffer, and the sender must respect that.

**Why this matters specifically for a proxy:** YARP sits directly in the data path of every streamed request/response. If YARP buffers everything before forwarding, it defeats streaming entirely for every request that passes through it — turning a low-memory, low-latency streaming design into a high-memory, high-latency one, and doing so multiplied across every concurrent request the proxy is handling. This is why YARP is built around forwarding request/response bodies via `Stream`/pipe abstractions rather than reading them fully into byte arrays — this is not a minor implementation detail, it's central to what makes a proxy viable at scale.

---

## 10. Important Engineering Concepts

These aren't HTTP-specific vocabulary — they're the lens you'll use to reason about *any* networked system, including YARP.

### 10.1 Latency vs. throughput vs. bandwidth

These get conflated constantly — keep them structurally separate:

- **Latency**: time for *one* unit of work (e.g., one request) to complete, end to end. Measured in time (ms).
- **Bandwidth**: the maximum rate at which raw bits can be pushed through a link. Measured in bits/sec.
- **Throughput**: the *actual* rate at which useful work (e.g., requests, or bytes of payload) gets completed, given real-world constraints (not just link speed — also concurrency limits, processing time, contention). Measured in units/sec (e.g., requests/sec).

A concrete distinction: a single request might have 200ms latency, but if your server can handle 500 requests concurrently (each still taking 200ms), your *throughput* can be 2,500 req/sec even though no individual request got faster. Latency is about one trip; throughput is about aggregate flow. A proxy can improve throughput (by handling many connections efficiently, load balancing across backends) while making *individual* latency slightly worse (because it's an extra hop) — that trade-off is completely normal and expected, and you'll see YARP's design constantly balancing it.

### 10.2 Connection reuse (revisited as an engineering concern)

Already covered mechanically (§6.1) — here's the engineering framing: every connection your proxy opens to a backend consumes a file descriptor, socket buffer memory, and (for TLS) CPU for the handshake, on *both* the proxy and the backend. A proxy handling thousands of requests/sec absolutely must reuse backend connections rather than opening a new one per request — otherwise connection *setup* overhead dwarfs actual request processing, and you can exhaust available file descriptors/ports outright. This is why YARP maintains connection pools per backend destination, and why understanding pooling isn't optional background knowledge — it's core to how the forwarder actually functions.

### 10.3 Timeouts

A timeout is a *decision*, not a default. "How long do I wait before giving up?" has to be answered at multiple layers:
- Connection establishment timeout — how long to wait for the TCP/TLS handshake.
- Request timeout — how long to wait for a full response after the request is sent.
- Idle timeout — how long an open-but-unused connection is allowed to sit before being closed.

For a proxy, timeouts exist at *both* legs — client↔proxy and proxy↔backend — and they compose. If your proxy's timeout to the backend is longer than the client's timeout to the proxy, the client gives up and moves on while the proxy is still uselessly waiting on a backend response nobody wants anymore — wasted resources with no benefit to anyone. Getting the relationship between these timeouts right is a real, recurring design decision in proxy configuration.

### 10.4 Cancellation

Related to timeouts but distinct: cancellation is explicit and can happen for reasons *other* than time (a user navigates away, closes a tab, or an upstream client disconnects). The important property: cancellation should **propagate**. If a client disconnects mid-request, the proxy ideally stops waiting on the backend too (an HTTP/2 `RST_STREAM`, from §7.3, is exactly this signal), and ideally the backend stops doing unnecessary work as well. In C#, this is `CancellationToken` — and in a proxy's forwarding pipeline, propagating that token from the incoming request all the way to the outgoing backend call is what makes cancellation actually save resources instead of just papering over a symptom on one side.

### 10.5 Request size / response size

Large bodies interact with everything above: they take longer to transmit (latency), they consume more memory if buffered instead of streamed (§9), and they can exhaust the connection's flow-control window (§7.3) if the receiver isn't consuming fast enough. A proxy commonly enforces **maximum request/response size limits** as a defensive measure — not because HTTP requires it, but because an unbounded body is an easy way for either a misbehaving client or a compromised/malicious one to exhaust proxy memory.

---

## 11. Common Misconceptions

- **"HTTPS and HTTP are basically the same, just with a lock icon."** No — HTTPS changes the transport (TLS in between), which changes handshake cost, and matters enormously for where a proxy terminates encryption.
- **"HTTP/2 means requests are sent instantly, no waiting."** No — multiplexing removes *HTTP-layer* queuing, but you still wait for actual network RTT and server processing time. It removes an artificial bottleneck, not physics.
- **"More connections = always faster."** No — beyond a point, more parallel connections just adds handshake/memory overhead without adding real throughput (and can trigger connection limits on the server or intermediate proxies).
- **"A redirect is a kind of proxying."** No — see §4.12. A redirect tells the *client* to make a new request elsewhere; a proxy does the forwarding itself and hands back the result. Structurally opposite responsibilities.
- **"Chunked encoding and Content-Length can both be present."** No — they're mutually exclusive ways of framing the same body; a message uses one or the other, never both (some implementations will actively reject a message that tries to send both, since it's ambiguous/a known request-smuggling attack vector).
- **"HTTP/3 just means 'HTTP/2 but faster.'"** It's specifically about fixing transport-level HOL blocking via QUIC — not a generic "make it faster" bucket of improvements.
- **"A stateless protocol means the server can't remember anything about you."** HTTP itself has no memory — but applications routinely build statefulness on top (cookies, tokens, sessions) precisely because the protocol doesn't provide it for free.

---

## 12. Production Perspective: 10 → 10,000 → 1,000,000 → 100,000,000 users

Scaling isn't just "add more servers" — here's how the *HTTP-level* concerns from this lecture actually change shape as load grows.

**~10 users**: A single server, HTTP/1.1 is completely fine. Connection reuse barely matters — you might not even notice if it's missing. Timeouts can be generous. You could run this from a laptop.

**~10,000 users**: Connection *count* starts to matter — you can't let every client keep an idle connection open forever (file descriptor limits become real). Keep-alive idle timeouts need actual tuning. You likely introduce a load balancer/reverse proxy in front of your app servers for the first time — this is roughly the scale where "just run one server" stops being viable, and understanding HTTP becomes load-bearing rather than academic.

**~1,000,000 users**: HTTP/1.1's head-of-line blocking becomes a real, measurable problem — you likely need HTTP/2 (or your CDN/edge already terminates it for you). Connection pooling to backends is no longer optional — a proxy opening a fresh TCP+TLS connection per request would collapse under this load. You start caring deeply about tail latency (p99, not just average) because at this volume, "rare" edge cases happen constantly in absolute terms. Retries need to be idempotency-aware (§4.4) or you risk cascading failures/duplicate side effects across the fleet.

**~100,000,000 users**: You're operating at a scale where QUIC/HTTP/3's tolerance for packet loss (§8) has measurable, real revenue/UX impact, especially for mobile users on lossy networks. Connection *establishment* cost (handshakes) is optimized aggressively (0-RTT, session resumption) because even milliseconds saved per connection compound across billions of daily connections. Timeouts, retries, and cancellation propagation (§10.3–10.4) must be nearly perfect, because small inefficiencies multiply into enormous aggregate resource waste and cost. This is squarely the scale YARP itself is designed for (it's what routes traffic inside Microsoft's own large-scale services) — every mechanism in this lecture exists *because* systems eventually reach this scale.

---

## 13. Failure Scenarios

- **Connection reset mid-response**: the server (or a proxy in between) abruptly closes the TCP connection before finishing the response. The client sees a partial/truncated body — this is why response parsers must be able to detect "connection closed before `Content-Length` bytes received" as an explicit error, not silently treat a short read as success.
- **Slowloris-style slow requests**: a client opens a connection and sends the request extremely slowly (or never finishes headers), tying up a server connection/thread indefinitely. Servers and proxies need explicit header/request timeouts to defend against this — "wait forever for more bytes" is not a safe default.
- **Backend hangs, never responds**: without a request timeout, the proxy (and every resource tied to that in-flight request — a connection, a thread/task, memory) is held indefinitely. This is why a proxy always needs its *own* independent timeout to a backend, regardless of what the client's timeout is.
- **Malformed chunked encoding**: a buggy or malicious sender sends chunk-size headers that don't match reality. This is a genuine security surface (HTTP request smuggling relies on exactly this kind of ambiguity between how a proxy and a backend each interpret framing) — which is part of why proxies must parse HTTP strictly rather than loosely "passing bytes through."
- **Partial write on the client→proxy leg while proxy→backend leg has already started**: if a client disconnects mid-upload, what should happen to the in-flight request to the backend? Ideally it's cancelled (§10.4) — but if cancellation isn't wired through correctly, the backend keeps processing a request nobody's waiting on anymore, wasting backend capacity.

---

## 14. Performance Implications

- **Avoid buffering full bodies** when you can stream instead — this is the single biggest lever for memory-bound scalability in anything sitting in a request path (§9).
- **Reuse connections aggressively**, but bound the pool — unbounded pooling can itself exhaust backend resources (§10.2).
- **Prefer HTTP/2+ for high-concurrency backend communication** where supported — fewer physical connections needed for the same logical concurrency (§7).
- **Set timeouts deliberately at every hop**, and make sure they compose sensibly rather than fighting each other (§10.3).
- **Propagate cancellation** so aborted work stops being work as early as possible in the pipeline (§10.4).
- Micro-optimizing header parsing speed, TCP congestion-control tuning, or QUIC's internal algorithms is **not** where your effort should go at this stage — those are deep specialist areas (and largely handled for you by Kestrel/the OS/the QUIC library). Your leverage is in the architectural decisions above.

---

## 15. YARP Connection

### 15.1 Why HTTP understanding is foundational to a reverse proxy, specifically

Go back to §4.2: a reverse proxy is simultaneously an HTTP *server* (to the client) and an HTTP *client* (to the backend), for the same logical request. Everything in this lecture is knowledge YARP needs *twice over* — once for how it behaves as a server accepting inbound requests, and once for how it behaves as a client issuing outbound requests. A proxy that didn't deeply understand HTTP couldn't just "copy bytes through" — because the message isn't a flat blob, it's a structured thing with rules (framing, connection semantics, header meaning) that differ depending on which HTTP version is in play on each side, and those two sides can even be *different versions* (e.g., HTTP/2 from the client, HTTP/1.1 to the backend) — which means YARP sometimes has to translate between wire formats while preserving identical semantics.

### 15.2 Concrete things YARP has to decide, per topic from this lecture

**Headers**: 
- Must add/rewrite `X-Forwarded-For`, `X-Forwarded-Proto`, `X-Forwarded-Host` — because once YARP is in the middle, the backend's own `Host`/remote-IP info reflects *YARP*, not the original client, unless YARP explicitly preserves that context in these headers.
- Must strip or rewrite **hop-by-hop headers** (like `Connection`, `Keep-Alive`, `Transfer-Encoding` in certain cases) — these describe the *specific connection* the header arrived on, and blindly forwarding them to a different connection (to the backend) is actively wrong, not just unnecessary.
- Must decide what to do with the `Host` header when the backend expects a different hostname than the client sent.

**Request bodies**: must decide whether to buffer (rarely, and only when necessary, e.g., needing to read the whole body to make a routing decision) or stream (the default and strongly preferred approach, per §9) — and must correctly relay `Content-Length` vs. chunked framing, converting between them if the two legs use different HTTP versions.

**Response bodies**: same streaming concern in reverse — must start forwarding backend response bytes to the client as they arrive, not after buffering the whole thing, to preserve the latency and memory benefits of streaming end-to-end.

**Status codes**: mostly pass through backend status codes unchanged — but YARP itself must *generate* status codes for proxy-specific failures it detects that the backend never even produced: `502 Bad Gateway` (backend unreachable or sent malformed response), `503 Service Unavailable` (no healthy backend available), `504 Gateway Timeout` (backend too slow). Recognizing which status codes are "the backend talking" vs. "YARP talking about the backend" is exactly the distinction from §4.8.

**HTTP versions**: YARP may need to accept HTTP/2 or HTTP/3 from clients while speaking HTTP/1.1 or HTTP/2 to backends (backends often don't support the newest version) — meaning YARP has to translate framing/semantics between versions while keeping the logical request/response identical. This directly requires understanding that HTTP/1.1, 2, and 3 share *semantics* but differ in *delivery mechanics* (§7.6) — that's precisely the seam YARP operates on.

**Connections**: YARP must pool and reuse backend connections (§10.2) rather than opening one per request — this is core to its performance, not an optional optimization. It also has to manage per-backend connection limits, idle timeouts, and health — deciding when a pooled connection is stale and should be discarded rather than reused.

**Streaming**: as covered in §9 and §15.2 above — this is arguably the single most architecturally central HTTP concept for YARP, since buffering-by-default would defeat the purpose of a high-throughput proxy.

### 15.3 The mental model to carry forward

```
   Client                    YARP                      Backend
     │                        │                            │
     │──── HTTP request ─────>│                            │
     │   (as a SERVER here)   │                            │
     │                        │──── HTTP request ─────────>│
     │                        │  (as a CLIENT here — may    │
     │                        │   be different HTTP version,│
     │                        │   different/pooled TCP conn,│
     │                        │   rewritten headers)        │
     │                        │                            │
     │                        │<──── HTTP response ─────────│
     │<──── HTTP response ────│                            │
     │  (streamed back, not   │                            │
     │   buffered whole)      │                            │
```

For YARP to sit correctly in that middle position, it must understand, at a mechanical level (not just vocabulary):
- what parts of a message are meaningful application data (forward faithfully) vs. connection-specific metadata (must not blindly forward) — §15.2 headers;
- how to preserve streaming semantics across two independently-negotiated connections that might even be different HTTP versions — §9, §15.2;
- when to generate its *own* HTTP responses (errors about the proxy's own state) vs. relay the backend's — §4.8, §15.2;
- how connection lifecycle (open, reuse, pool, timeout, cancel) works on both legs simultaneously, independently — §6.1, §10.2, §10.3, §10.4.

This is why "HTTP" is Lecture 1 of this series and not a footnote — essentially every architectural decision inside YARP's forwarder is really a decision about *one specific mechanism from this lecture*, applied at the seam between two independent HTTP connections.

---

## 16. What I Don't Need to Know Yet

Explicitly deferred — recognize the term if you see it, nothing more, until a later lecture (or never, if it turns out not to be relevant):

- QUIC's internal congestion control algorithms, packet number spaces, or wire-level frame encoding.
- HPACK/QPACK compression algorithm internals (the actual encoding scheme, Huffman tables, etc.) — "there's a shared compression table" is sufficient depth for now.
- HTTP/2 Server Push mechanics — deprecated/removed from browsers, not worth deep study.
- TLS internals beyond "it encrypts and authenticates, and costs round trips to establish."
- HTTP caching semantics in depth (`ETag`, `Cache-Control` directives, validation strategies) — relevant eventually, but it's a distinct topic from the transport/message mechanics covered here, and will likely get its own lecture if it becomes relevant to a specific YARP feature (e.g., response caching middleware).
- WebSockets / Server-Sent Events protocol details — related to HTTP (they upgrade *from* an HTTP request) but are a separate mechanism from request/response proxying.
- Load balancing algorithms themselves (round-robin, least-connections, etc.) — that's a YARP-specific topic for a later lecture; this lecture only established *why connections and requests are the things being balanced*.

---

## 17. Knowledge Check

Reason through these — they require applying the mechanism, not recalling a definition:

1. A client on a lossy Wi-Fi network is using HTTP/2 to a server. One packet gets dropped. Explain, in terms of TCP and HTTP/2 streams, why *every* in-flight stream on that connection stalls — even ones whose data already fully arrived at the network layer.
2. Your proxy receives a `POST /charge-card` request, forwards it to the backend, and the backend connection drops before any response arrives. Should your proxy automatically retry the request against another backend instance? Justify your answer using the concepts of safety/idempotency from §4.4.
3. Explain why a proxy cannot simply forward the `Connection: keep-alive` header it received from the client onto the connection it opens to the backend. What would go wrong?
4. A response has both `Content-Length: 500` and, three lines later, its body actually contains 800 bytes before the connection closes. What should a strict HTTP parser do, and why is this scenario specifically dangerous in a system with a proxy in front of a backend?
5. Explain, using the DNS → TCP → TLS → HTTP breakdown from §5, why HTTP/3 can change the transport (swap TCP+TLS for QUIC) without changing what a "GET request" or a "200 response" *means* to your application code.
6. Your proxy buffers the entire response body from a backend before forwarding it to the client, "to make the logic simpler." Describe a concrete failure mode this introduces at high concurrency, connecting it explicitly to §9 and §10.5.

---

## 18. Practical Exercise

You have a Mac — here's something you can do in ~20 minutes with zero extra infrastructure, that will make several of the abstractions in this lecture tangible rather than theoretical.

### Part A — Read a raw HTTP/1.1 message with your own eyes

```bash
# -v shows you the actual request/response headers as sent on the wire
curl -v https://example.com/ 2>&1 | head -50
```
Look at the `>` lines (what curl sent — the actual request line and headers) and the `<` lines (what came back). Confirm you can identify: the request line, `Host` header, status line, `Content-Length` or `Transfer-Encoding`, and any `Set-Cookie`.

### Part B — See HTTP/1.1 head-of-line blocking directly

```bash
# Force HTTP/1.1 and time a request
curl --http1.1 -w "\nTotal time: %{time_total}s\n" -o /dev/null -s https://example.com/
```

Then compare against forcing HTTP/2 (if the server supports it):
```bash
curl --http2 -w "\nTotal time: %{time_total}s\n" -o /dev/null -s https://example.com/
```

### Part C — Watch chunked transfer encoding happen

Many APIs that stream responses will show `Transfer-Encoding: chunked` instead of `Content-Length`. Try:
```bash
curl -v https://httpbin.org/stream/5 2>&1 | grep -i "transfer-encoding\|content-length"
```
(`httpbin.org/stream/N` deliberately streams N JSON lines one at a time — a good example of a server that can't know its total length up front, so it must use chunked encoding, exactly as described in §6.4.)

### Part D — Build a tiny streaming endpoint yourself (C#, since that's your strength)

This is the most valuable part — it'll make §9 (streaming) concrete by having you *cause* both the buffered and streamed behavior yourself and watch them differ.

```csharp
// dotnet new web -o HttpLectureDemo && cd HttpLectureDemo
// Replace Program.cs with this, then: dotnet run

var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

// BUFFERED: builds the whole string in memory before sending anything.
app.MapGet("/buffered", async (HttpContext ctx) =>
{
    var sb = new System.Text.StringBuilder();
    for (int i = 0; i < 10; i++)
    {
        sb.AppendLine($"line {i}");
        await Task.Delay(300); // simulate slow data production
    }
    await ctx.Response.WriteAsync(sb.ToString());
    // Notice: the client receives NOTHING until all 10 lines are ready.
});

// STREAMED: writes and flushes each piece as it becomes available.
app.MapGet("/streamed", async (HttpContext ctx) =>
{
    ctx.Response.Headers.ContentType = "text/plain";
    for (int i = 0; i < 10; i++)
    {
        await ctx.Response.WriteAsync($"line {i}\n");
        await ctx.Response.Body.FlushAsync(); // push bytes to the client NOW
        await Task.Delay(300); // simulate slow data production
    }
});

app.Run();
```

Run it, then in two terminals:
```bash
curl -N http://localhost:5000/buffered    # -N disables curl's own output buffering
curl -N http://localhost:5000/streamed
```

Watch `/buffered` sit silent for ~3 seconds and then dump everything at once. Watch `/streamed` print `line 0`, `line 1`, ... one every 300ms, in real time. That visible difference *is* §9 — and it's exactly the difference between a proxy that buffers bodies and one that doesn't.

---

## 19. "Ready to Move On" Criteria

Before starting Lecture 2, you should be able to explain — out loud, in your own words, without looking back at this document:

- [ ] What HTTP is, and specifically which parts of a request's journey are HTTP vs. not HTTP (DNS, TCP, TLS).
- [ ] Why a persistent connection matters, and what specifically it saves you from re-paying.
- [ ] What head-of-line blocking is, mechanically, at the HTTP/1.1 connection level.
- [ ] How HTTP/2 fixes that specific problem (streams + multiplexing over one connection).
- [ ] Why HTTP/2's fix is incomplete — what TCP-level HOL blocking is, and why it still happens even with HTTP/2 streams.
- [ ] Why HTTP/3 uses QUIC/UDP instead of TCP, at the level of "TCP enforces one ordered byte stream; QUIC natively separates streams" — not the algorithmic internals.
- [ ] Why streaming matters for memory usage at scale, using a concrete number-of-concurrent-requests argument.
- [ ] Why a reverse proxy is architecturally "a server and a client at once for the same request," and at least three concrete things that fact forces YARP to actively decide about (not just relay) — pick from headers, bodies, status codes, connections.
- [ ] The difference between idempotent and non-idempotent methods, and why that distinction governs whether a proxy can safely auto-retry a failed request.

If any of those feel shaky, it's worth re-reading that section rather than pushing forward — this lecture is the foundation the rest of the series builds directly on top of.
