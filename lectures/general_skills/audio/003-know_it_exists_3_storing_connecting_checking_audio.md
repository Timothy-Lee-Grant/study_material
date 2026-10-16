# Know It Exists, Part 3: Storing, Connecting, and Checking (audio lecture)

This is the last part of a three-part series about concepts worth knowing just because they exist. Part one covered how programs find out that something happened. Part two covered who starts your code and what keeps it running. This part covers three more families: where data lives, how your program connects to other systems and to people, and how to check that what the AI built is actually correct.

## Why this matters

The third family matters most in the AI era, so it's worth explaining why. When implementation is cheap, the scarce skill is verification. AI can write a thousand lines in a minute. Knowing whether those thousand lines are right is the bottleneck, and the bottleneck is now you. Most people check AI code by reading it, which is slow and misses things. Several of the concepts in this episode are *mechanical* ways to check, ways that don't rely on you spotting the bug by eye. Knowing they exist changes what you can safely delegate.

The card format is the same: the smell, what it is, where it lives and who calls whom, the catch, and the words to say to the AI.

## The core ideas

One. SQLite, said "S-Q-L-ite" or "sequel-ite", is a full SQL database that lives in one ordinary file inside your program, with no server. It handles many readers but only one writer at a time.

Two. Object storage holds large files, called blobs, cheaply and at any scale. A presigned URL, which Azure calls a shared access signature, lets a client upload or download directly, with time-limited permission, without passing the bytes through your server.

Three. Search comes in kinds. Full-text search matches and ranks words, vector search matches meaning, and hybrid search combines them. Many products already have one built in.

Four. Redis is an in-memory store of data structures, each with an optional expiry time. It's a common tool for caching, rate limiting, counters, and leaderboards.

Five. Spec-first development means an OpenAPI document describes an HTTP API, and tools generate the client code from it, so the contract is the source of truth instead of the code.

Six. OAuth lets a user grant your program limited access to their account without giving you their password. The device code flow handles gadgets without a keyboard, and Azure managed identity lets cloud code authenticate with no secret at all.

Seven. A headless browser, driven by a library like Playwright, lets code operate a website the way a person does, when there's no API.

Eight. Property-based testing checks rules that should hold for all inputs, against hundreds of generated inputs. Git bisect runs a binary search over commit history to find the change that broke something.

Nine. eBPF lets you safely attach small programs to events inside the Linux kernel, to watch or filter what the system is doing without changing the kernel. It's niche, but it's remarkable to know about.

## Section one: SQLite, a database that is just a file

The smell: "I need to store structured data for this tool, device, or app, and setting up a database server feels like too much." What people do instead is write JSON files by hand and slowly reinvent queries, indexes, and safe writes, badly.

**SQLite** is a complete SQL database engine packaged as a library inside your program. The whole database (tables, indexes, everything) is one ordinary file on disk. There's no server process, no port, no password, and no installation. Your program opens the file and runs SQL against it. It's one of the most widely deployed pieces of software in existence: it's inside every phone, every major browser, and countless desktop apps. It's very reliable about not losing data during a crash. Timothy's crash-consistency lecture is the background for why that's hard and why using SQLite beats writing files yourself.

Where it lives: in your process, as a library. In dot net, you reach it through a package called Microsoft Data SQLite, or through Entity Framework.

The catch: **one writer at a time.** Many readers can read at once, and turning on a setting called W-A-L mode, for write-ahead log (the same idea as in part one), lets readers keep reading while a write happens. But two programs that both write heavily at the same moment will queue up behind each other. And because it's a local file, it isn't the right choice for a database shared by many servers over a network. The rule of thumb: one machine, modest write traffic, SQLite is often the best answer. Many machines writing, use a database server like Postgres.

## Section two: object storage and presigned URLs

The smell: "users upload photos, videos, logs, or documents", or "I need to keep large files cheaply, forever." The mistake is putting large files in the database or on the web server's own disk.

**Object storage** is a cloud service built for this. You store objects (a blob of bytes plus a name and some metadata) in containers, called buckets on Amazon. There are no folders in the true sense, just names that may contain slashes. It's cheap, effectively unlimited, and very durable. The names: Amazon S3, said "S-three", which also became the standard interface that many other providers copy, and on Azure, **Blob Storage**.

Here's the concept that makes it really useful: the **presigned URL**. Think about a user uploading a two-gigabyte video. The naive design sends the video to your server, and your server forwards it to storage. Your server is now a bottleneck carrying two gigabytes it doesn't care about. Instead, your server creates a special URL that grants permission to upload exactly one object, to one name, for the next fifteen minutes, signed with your storage key. The server hands that URL to the browser, and the browser uploads straight to storage. Your server never touches the bytes. On Azure this signed permission is called a **shared access signature**, or S-A-S, often said "sass".

The catch: a presigned URL is a bearer credential. Anyone holding it has that permission until it expires, so keep the lifetimes short and the permissions narrow, such as upload only, to one name only.

## Section three: the kinds of search

The smell: "users need to find things by typing", in your notes, your logs, or your product catalog. A naive substring match, checking whether a field contains the typed word, misses plurals and typos, ignores relevance, and gets slow as data grows.

There are kinds of search, and knowing which kind you need is the whole skill.

**Full-text search** works on words. The text is broken into tokens, reduced to root forms so that "running" and "runs" match "run", and stored in an **inverted index**: a map from each word to the documents containing it, like the index at the back of a book. Results are ranked by relevance, with a standard formula called B-M-twenty-five that rewards rare words appearing often. You may not need a new service: Postgres has full-text search built in, and SQLite has an extension called F-T-S-five. Dedicated engines include Elasticsearch and OpenSearch, and simpler ones like Meilisearch, which tolerate typos out of the box.

**Vector search**, which Timothy already used with pgvector, works on *meaning*. A model turns text into a list of numbers, an embedding, and search finds the nearest lists. It finds "car" when you type "automobile", but it's weak on exact things like part numbers, error codes, and names.

**Hybrid search** runs both and merges the rankings. A common merging method is called reciprocal rank fusion. For AI retrieval systems, hybrid is often noticeably better than vectors alone, because user questions mix meaning with exact identifiers.

The catch: picking vector search for everything because it's fashionable. If users search for error code E-four-oh-one-seven, plain full-text search beats embeddings.

## Section four: Redis, data structures with an expiry date

The smell takes several forms: "this result is expensive to compute and is read constantly", "count how many requests this user made in the last minute", "keep a ranked list of the top scores", "remember this login session for thirty minutes."

**Redis** is a server that keeps data in memory, so it's very fast, but its real strength is that it stores *data structures*, not just values: strings, counters you can increase in one atomic step, lists, sets, hashes, and sorted sets. And any key can have a **time to live**, after which it deletes itself.

Those pieces combine into common patterns. A **cache**: store the expensive result with a time to live of five minutes, so it refreshes itself. A **rate limiter**: increase a counter named after the user and the current minute, and give it a time to live of one minute. Timothy's rate-limiter design work fits right here. A **leaderboard**: a sorted set keeps members ordered by score automatically. Redis also offers lightweight pub-sub and streams, which connects back to part one. A fork called Valkey and Azure's managed Redis service are the related names you'll run into.

The catch: memory is limited and, depending on configuration, data can be lost on restart. So Redis is usually the fast copy, and the real copy lives in a database. The classic cache mistake is **invalidation**: the database changes and the cache keeps serving the old value until it expires. Decide on purpose how stale is acceptable.

## Section five: spec-first, letting the contract generate the code

The smell: "my front end and back end keep disagreeing about the shape of the data", or "I need to call this company's API, and I'm hand-writing request classes", or "I'm changing an API and don't know who I'll break."

An **OpenAPI** document, formerly known as Swagger, is a machine-readable description of an HTTP API: every endpoint, every parameter, and the exact shape of every request and response. ASP.NET Core can produce one from your controllers automatically. The multiplier is what tools can *do* with it. They can **generate a typed client** in any language, so calling the API becomes calling ordinary methods, with the compiler catching mismatches. Microsoft's generator is called Kiota, said "kee-OH-tuh". Others include NSwag and the OpenAPI Generator. Tools can generate interactive documentation, mock servers for testing before the real one exists, and checks in your build pipeline that flag a **breaking change** before it ships.

The same idea exists for other kinds of contracts. **JSON Schema** describes the shape of a JSON document. It's what powers structured output from AI models, which Timothy has used. **Protocol Buffers**, used by gRPC, is the same idea for binary messages. The general principle is one source of truth, from which everything else is generated.

Why this matters especially with AI: generated code drifts. When an AI writes both the server and the client by hand, they slowly stop matching. When both are generated from one specification, they can't drift. And a specification is a great thing to hand to an AI: "here is the OpenAPI document, implement the server to match it."

The catch: the specification must stay the source of truth. If people edit the generated code by hand, the next generation wipes their changes out.

## Section six: identity without passwords

The smell: "my program needs to act on a user's GitHub, Google, or Microsoft account", or "my service needs credentials to reach the database and I'm about to paste a password into a config file."

**OAuth**, said "oh-auth", is the standard for **delegated access**. Instead of giving your program their password, the user is sent to the provider, logs in there, and approves a specific list of permissions, called **scopes**, such as "read your repositories" but not "delete them." The provider then gives your program an **access token** that carries only those permissions and expires. Its companion, **OpenID Connect**, or O-I-D-C, adds identity on top: "sign in with Microsoft" is OpenID Connect.

Two particular flows are worth knowing by name.

The **device code flow** is for devices without a good keyboard or browser, like a Raspberry Pi, a command-line tool, or a TV. The device shows a short code and a URL. You open that URL on your phone, type the code, and approve, and the device, which has been checking in the background, receives its token. When you've logged into the Azure command line or the GitHub command line by typing a code on another screen, that was the device code flow.

**Managed identity** is the Azure concept that removes secrets entirely. Code running in Azure (a function, a web app, a virtual machine) can be given its own identity by the platform. It asks the platform for a token, and the platform, which already knows which machine is asking, hands one over. You then grant that identity access to the database or storage. There's no password stored anywhere, so there's nothing to leak and nothing to rotate. For the Microsoft path this is close to essential. "Use managed identity instead of a connection string with a password" is a sentence interviewers and reviewers want to hear.

The catch: tokens are bearer credentials, like presigned URLs. Ask for the narrowest scopes, never log tokens, and never put them in front-end code.

## Section seven: headless browsers, operating a website as code

The smell: "the data I need is only on a website, with no API", or "I need to test that my web app's sign-up flow actually works end to end", or "I do the same twenty clicks every week."

A **headless browser** is a real browser engine running without a visible window, controlled by code. The code can open pages, click, type, wait for elements to appear, take screenshots, and read what's on the page, the way a person would. The leading library is **Playwright**, made by Microsoft, with versions for dot net, Python, Java, and JavaScript. It can even record your clicks and write the code for you. It's the standard tool for **end-to-end tests** of web apps.

The catches: websites change their layout and break your script, so automating a site you don't control is fragile. Prefer an official API whenever one exists. And respect the site's terms of service. Automating your own app's tests is the clearly safe, high-value use.

## Section eight: two checks the AI can't easily fool

This is the verification family promised at the start, and these two tools have the best ratio of value to effort.

**Property-based testing.** A normal unit test checks one example: "sorting three, one, two gives one, two, three." The AI that wrote the code can also write examples that happen to pass. A property-based test states a *rule* that must hold for every input. For example: "the output of sort has the same length as the input, contains the same items, and every item is less than or equal to the next." The library then generates hundreds of random inputs (empty lists, huge lists, duplicates, negative numbers, odd edge cases) and checks the rule on each. When it finds a failure, it **shrinks** the input to the smallest example that still fails, so you get "the list containing zero and minus zero" instead of a thousand-item mess. The names: in dot net, FsCheck and CsCheck. In Python, Hypothesis. A related idea is **fuzzing**, which throws malformed input at a parser until it crashes.

This connects to Timothy's way of learning. Writing a property means stating what must always be true, which is an invariant. That's exactly the skill his LeetCode and state-machine work keeps building. The AI writes the code, you write the properties, and the machine checks the code against your rules thousands of times.

**Git bisect.** The smell: "this worked last week, it's broken now, and there are eighty commits in between." Git bisect is a binary search over history. You tell git one commit that's good and one that's bad. It checks out the commit halfway between, and you test it and say "good" or "bad." It halves the range again. Eighty commits take about seven steps. If you can write a script that exits successfully when things work, git will run the whole search by itself.

Timothy will recognize the structure from his binary-search lecture: history is a monotone sequence, good, good, good, then bad, bad, bad, and bisect finds the first bad one, the "first True" boundary. A concept he learned for interviews turns out to be a daily debugging tool.

## Section nine: eBPF, a warning that this one is niche

This last concept comes with an honest warning: most application developers never need it. It's here because, for someone with an embedded Linux background, knowing it exists makes a whole category of "I wish I could see what's happening" problems possible.

**eBPF**, said "E-B-P-F", lets you load small, verified programs into the running Linux kernel and attach them to events: a system call, a network packet arriving, a function in the kernel or in your own program being entered. The kernel first checks each program to make sure it can't crash or hang the system, then runs it at that point and passes data out to your tools. The result is that you can watch, measure, or filter almost anything the system does, on a live production machine, without rebooting, without changing the kernel, and without changing the program being watched.

The smell: "which process is opening this file?", "where is this latency coming from?", "something is talking on the network, and I don't know what." The easiest way in is a tool called bpftrace, which turns one-line questions into eBPF programs, along with a ready-made collection called B-C-C tools. eBPF also powers modern networking and security tools like Cilium.

The catch: it needs root privileges and a reasonably recent kernel, and writing eBPF programs yourself is genuinely specialized. Treat it as a power tool you reach for with an AI's help when ordinary logs and profilers have run out.

## Connections across the series

Step back and look at the whole map. Part one was about **events**: how a program finds out, with webhooks, tunnels, watchers, NOTIFY, change data capture, queues, Server-Sent Events, and idempotency holding them together. Part two was about **execution**: who starts code and what keeps it going, with timers, udev, job queues, serverless functions, durable workflows, reconciliation, leases, and flags. Part three was about **data, connections, and verification**: SQLite, blobs and presigned URLs, kinds of search, Redis, specifications, delegated identity, headless browsers, property tests, bisect, and eBPF.

The habit that turns this into a multiplier is the smell. When you're sketching a system, listen for the phrases: "checks every few seconds", "only one at a time", "must not be lost", "the user uploads", "it worked last week", "every night", "when it's plugged in." Each phrase is a doorway to a concept that already exists, has a name, and can be handed to an AI.

And one more habit, to keep the map growing: when an AI proposes a design, ask it, "what are two other standard ways to solve this, and what does each cost?" That's how you meet the concepts this series missed.

## Recap

SQLite is a full database in one file inside your program. It's excellent on one machine, with one writer at a time.

Object storage holds big files cheaply. Presigned URLs, or shared access signatures on Azure, let clients move bytes directly with narrow, short-lived permission.

Choose the kind of search on purpose: full text for words and exact codes, vectors for meaning, hybrid for both.

Redis offers in-memory data structures with expiry, for caches, rate limits, counters, and leaderboards. It's the fast copy, not the real one, and watch for stale caches.

Spec-first means one contract, like OpenAPI, JSON Schema, or protocol buffers, generates everything else, so client and server can't drift.

OAuth delegates scoped, expiring access without passwords. The device code flow serves gadgets, and managed identity removes secrets on Azure entirely.

Headless browsers like Playwright let code drive a website, best used for your own end-to-end tests.

Property-based tests check your rules against hundreds of generated inputs and shrink failures to the smallest example. Git bisect is binary search over history.

eBPF is a niche power tool for watching the live Linux kernel safely.

## Walk questions

One. Explain the presigned URL design for a large upload: who creates the URL, who uses it, what it permits, and why the server never touches the bytes.

Two. Pick a function you might ask an AI to write, like parsing your telemetry frames, and state two properties that must hold for every input. Then explain what "shrinking" gives you when a property fails.

Three. Without looking anything up, list as many concepts from the whole series as you can, each with its smell phrase. Notice which ones you couldn't recall, and those are the ones to listen to again.
