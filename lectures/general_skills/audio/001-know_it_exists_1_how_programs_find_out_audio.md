# Know It Exists, Part 1: How Programs Find Out That Something Happened (audio lecture)

This is part one of a three-part series about concepts worth knowing just because they exist. Part one covers how programs find out that something happened. Part two covers how work gets started, scheduled, and kept running. Part three covers storing data, connecting to other systems, and checking that what got built is correct.

## Why this series exists

Timothy noticed something while building with AI. Some concepts multiply what he can build, even when all he knows is that they exist. He gave three examples from his own work. The first is webhooks: once you know that another system can call your URL when something happens, you design differently. The second is custom PowerShell cmdlets: a C sharp class with an attribute on top becomes a command a user can type, and once you know that's possible, "let the user talk to my program from a shell" is an option you can reach for. The third is background daemons on Linux: systemd reads a small configuration file, starts your program, and keeps it running. In every case he didn't need the implementation. The AI handles that. He needed to know the move was available.

That observation is correct, and it explains a lot. Innovation researchers call it the adjacent possible: you can only reach for what you know is there. AI has made implementation cheap. It has not made the map cheap, because you can't ask for something you can't name. If you've never heard of a message queue, you will never ask for one. You'll ask the AI to make your loop faster, and it will happily do that.

There is one refinement worth adding to Timothy's version. He said a high-level understanding is helpful but not required, and deep understanding isn't required at all. Mostly true. But one fact one level below the name is worth carrying for every concept: **how it fails.** The AI will build whatever you name, including the wrong thing, confidently. What's left for you is the review: noticing that the thing built doesn't fit, or will break in a particular way. Knowing the failure mode is the cheapest bit of depth that gives you real review power.

So each concept in this series comes as a card with five parts, always in the same order:

First, **the smell**: the moment while designing that should make you think of this concept. This is the most important part. Existence knowledge only multiplies if it comes to mind *at design time*. A concept you know but don't recall while sketching a system is worth nothing.
Second, **what it is**, in one sentence.
Third, **where it lives and who calls whom**.
Fourth, **the catch**: how it fails, or what it costs.
Fifth, **the words to say to the AI**, the names that unlock the right implementation.

Today's theme is the most common smell of all: the polling loop. The first design almost everyone writes to notice a change is to loop, check, sleep a few seconds, and check again. Almost every concept today is a way to replace that loop with a push, where whoever knows about the change tells you.

## The core ideas

Here are today's core ideas, stated plainly. They're the answer key for the walk questions at the end.

One. The multiplier is the map, and each entry on the map has a smell, a one-sentence definition, a location, and a catch. The smell is what makes the knowledge usable.

Two. Polling means you keep asking. Pushing means you get told. Push is faster and cheaper, but someone has to keep a list of who to notify, and every push system has to deal with missed and duplicated messages.

Three. A webhook is another system calling your URL when an event happens. Verify its signature, reply quickly, do the real work afterwards, and expect the same event more than once.

Four. A tunnel makes a machine with no public address reachable from the internet. The machine opens an outbound connection to a relay, and the relay sends inbound traffic back down that already-open connection.

Five. Files and databases can announce their own changes: file watchers for files, LISTEN and NOTIFY in Postgres for lightweight signals, and change data capture for a durable stream of every row change.

Six. A message queue separates the producer of work from the consumer in time. The broker holds messages until a consumer confirms them. Publish-subscribe gives every interested subscriber its own copy.

Seven. Server-Sent Events are a one-way stream from a server to a browser over plain HTTP. That's how AI chat apps stream text token by token.

Eight. Push systems deliver at least once, so the handler must be idempotent: handling a message twice has the same effect as handling it once.

## Section one: the polling smell, and why push needs a list

Picture a program that needs to know when a file has arrived in a folder, or when a new row lands in a table, or when a payment has gone through. The first design is a loop: check, sleep five seconds, check again. It works, and it has three costs. It's slow, because you find out up to five seconds late. It's wasteful, because nearly every check finds nothing. And it doesn't scale: a thousand programs polling one server every five seconds is two hundred requests a second, all asking the same question.

The push alternative turns the direction around. The thing that knows about the change tells the interested parties. But think about what that requires. The source has to keep a list of who wants to know, and it has to decide what to do when someone on the list is unreachable. Every concept today is a different answer to those two questions: who keeps the list, and what happens when delivery fails.

Here's the smell, in a sentence you can catch yourself saying: "and then it checks every few seconds to see if..." Whenever you hear that in your own design, stop and ask: who already knows when this changes, and can they tell me?

## Section two: webhooks, and the parts the AI won't warn you about

You already know what a webhook is: you give a service, say GitHub or Stripe or Azure DevOps, a URL, and when an event happens it sends an HTTP POST request to that URL with a description of the event. The list of who to notify is your webhook registration, stored at their end.

Here are the three catches. They are what separate a demo from something that holds up.

First, **anyone can call your URL.** Your endpoint is on the internet, so how do you know a request came from GitHub and not from someone pretending to be GitHub? Most webhook senders sign each request. You and the sender share a secret. The sender computes a signature over the request body using that secret, with a method called H-MAC, said "aitch-mack", and puts it in a header. Your code recomputes it and compares. If they match, the message is genuine and hasn't been changed. The words to say to the AI are "verify the webhook signature."

Second, **reply fast, work later.** Senders wait only a few seconds for your reply. If you do the slow work, like calling an AI model or shutting down a virtual machine, before replying, the sender times out, assumes you failed, and sends the event again. So the pattern is: verify, record the event somewhere safe, reply "OK" immediately, then process it in the background. Section five covers where that "somewhere safe" usually is.

Third, **you will get the same event twice.** Because senders retry on timeouts and errors, duplicates aren't a rare edge case. They are part of the contract. Section seven covers how to make that harmless.

Pause here and predict: your server is down for an hour, and during that hour GitHub tries to send you ten events. What happens to them? The answer depends on the sender. Most retry for a while with growing gaps, then give up, and many keep a delivery log you can replay by hand. So a webhook is a strong hint that something happened, but not a guarantee. Systems that can't miss an event usually do a catch-up poll as a safety net: rely on push for speed, and run an occasional poll for completeness.

## Section three: tunnels, or how a webhook reaches your laptop or your Pi

Here's a problem that stops a lot of people the first time they try webhooks. Your code runs on your laptop or on a Raspberry Pi at home. GitHub needs to send it a request, but your machine has no public address. It sits behind a home router, and home routers block connections coming in from the internet.

The concept that solves this is a **tunnel**. Your machine runs a small agent that opens an *outbound* connection to a relay service on the internet. Routers allow outbound connections, which is how you browse the web at all. The relay gives you a public URL. When a request arrives at that URL, the relay sends it down the connection your machine already opened. Nothing ever had to connect *in* to your machine. That's the whole trick: the inside reaches out first, and replies come back along the same path.

The names to know are ngrok, said "en-grok", and Cloudflare Tunnel, which both give you a public URL for a local service. Tailscale works a bit differently. It builds a private network among only your own devices, so your laptop at a coffee shop can reach your Pi at home as if they were on the same desk, and nothing is exposed to the public internet. Tailscale also has a feature called Funnel for when you do want something public.

The smell: "this works on my machine, but the outside service can't reach it", or "I want to reach my device from anywhere without configuring my router."

The catch: a public tunnel puts a development machine on the internet. Anything reachable through that URL is reachable by everyone, so the signature verification from section two and real authentication stop being optional.

## Section four: files and databases that announce their own changes

Now consider changes inside your own machine or your own database.

For files, the concept is a **file watcher**. Operating systems can notify a program when a file or folder changes, so the program doesn't have to rescan. On Linux the kernel feature is called inotify, said "eye-notify". On a Mac it's FSEvents. In dot net you use a class called FileSystemWatcher, and every major language has an equivalent. The smell: "watch this folder and process anything that shows up."

The catch with file watchers is that one human action is often several events. When an editor saves a file, it often writes a temporary file, deletes the original, and renames the temporary file into place. That's three events for one save. And a large file that's still being copied triggers an event before it's finished. The fix has a name: **debouncing**. You wait until events have stopped for a short moment before you act. Watchers also tend to be unreliable on network drives and inside some container setups. The words to say to the AI are "file watcher with debouncing."

For databases, there are two levels, and the difference between them is the important part.

The lightweight level, in Postgres, is a pair of commands called LISTEN and NOTIFY. One connection says "I'm listening on the channel called new readings." Any other connection, or a trigger that runs automatically on insert, can say "notify the new readings channel", with a small text message attached. Every connection that's listening hears it right away. This is a push built into the database you're already running, with no extra service needed.

The catch is what makes the second level necessary. LISTEN and NOTIFY doesn't store anything. If no one is listening at the moment the notification fires, because your service was restarting, say, the message is simply gone. It's a doorbell, not a mailbox. So the correct use is to treat the notification as a hint ("go look, something changed") while the data itself stays in the table.

The durable level is called **change data capture**, often shortened to C-D-C. Every serious database already writes each change to an internal log before applying it. This is called the write-ahead log, and it's how the database recovers after a crash. Change data capture reads that log and turns every insert, update, and delete into a stream of events that other systems can consume, in order, without losing any. The best-known tool is called Debezium, said "duh-BEE-zee-um". The smell: "every time this table changes, another system needs to know, and it must never miss one", for example keeping a search index or a cache in step with the main database.

Pause and predict: you want a dashboard to update the instant a new telemetry row is written, and missing one update is fine because the dashboard re-reads the latest values anyway. Which level do you need? The doorbell. The data lives in the table, and the notification only says "refresh now." If a downstream billing system had to see every row exactly, you'd want the mailbox.

## Section five: message queues and publish-subscribe

This is probably the single highest-value concept in this episode. It's the one that most often separates a script from a system.

The smell has three versions. One: one part of the system produces work faster or more unevenly than another part can consume it. Two: work must not be lost if the consumer crashes halfway through. Three: one event has several interested parties, and the producer shouldn't have to know who they are.

A **message queue** is a separate service, called a broker, that holds messages. A producer drops a message in and moves on immediately. A consumer takes a message, does the work, and then sends back a confirmation called an acknowledgement, or ack. If the consumer crashes before acknowledging, the broker notices and hands the message to someone else. So the queue separates the two sides *in time*: the producer doesn't wait for the consumer, and the consumer can be down for a while without anything being lost. It also smooths out bursts. A thousand webhooks in one second become a backlog that two workers work through calmly.

Go back to the webhook rule "reply fast, work later." The "somewhere safe" you record the event in is very often a queue. Verify, enqueue, reply OK, and a worker processes it.

There are two delivery shapes, and the difference matters. In a plain **queue**, each message goes to exactly one of the competing workers, which is how you spread work across many workers. In **publish-subscribe**, usually shortened to pub-sub, a message is published to a topic, and *every* subscriber gets its own copy. That's how one "order placed" event reaches the email service, the inventory service, and the analytics service, without the order service knowing any of them exist.

The names to know: RabbitMQ, Azure Service Bus (worth knowing given the Microsoft goal), Amazon SQS, and Kafka. Kafka is worth singling out because it's built differently: it's a **log**, not a queue. Messages aren't removed when they're read. They stay for days, and each consumer keeps its own place in the log, so a new consumer can replay history from the beginning.

There are two catches, each with a name you should know.

The first is the **poison message**: a message that crashes the consumer every time it's processed. If nothing catches it, it's retried forever and blocks everything behind it. The standard defense is a **dead-letter queue**. After a few failed attempts, the broker moves the message to a side queue for a human to look at.

The second is the **dual-write problem**, and it's subtle. Your code saves an order to the database and then publishes an "order placed" message. What if the program crashes between those two steps? Now the database has the order but nobody was told. Or, if you publish first, the message went out but the order was never saved. The fix is called the **outbox pattern**. In the same database transaction that saves the order, you also insert a row into a table called the outbox. Both succeed together or neither does. A separate process reads the outbox and publishes the messages. If you remember one pattern name from this section, make it this one, because AI-generated code makes the dual-write mistake all the time.

## Section six: Server-Sent Events, pushing to a browser

Now push all the way to a person's screen. The smell: "the web page should update by itself without the user refreshing", like a live dashboard, a progress bar for a long job, or text appearing word by word.

The simplest tool is **Server-Sent Events**, often shortened to S-S-E. The browser makes one ordinary HTTP request, and the server simply never finishes the response. It keeps the connection open and writes a new line of text whenever it has something to say, each line starting with the word "data". The browser has a built-in object called EventSource that reads this stream and, importantly, reconnects automatically if the connection drops.

Here's the part that makes it click: this is how AI chat interfaces stream their answers. When text appears token by token, the model's API is usually sending Server-Sent Events. You've been watching this concept all along.

When do you need a WebSocket instead, which you covered in an earlier networking lecture? When traffic has to flow *both* ways continuously, as in a chat room, a multiplayer game, or a collaborative editor. Server-Sent Events are one direction only, server to browser, but they're plain HTTP, so they pass through proxies and load balancers with less trouble.

The catch: some proxies hold back, or buffer, the response until it's finished, which defeats streaming, so streaming endpoints often need buffering turned off. Long-lived connections also tie up server resources, so thousands of watchers need a server designed for many open connections.

## Section seven: idempotency, the rule that ties it all together

Every push mechanism today shares a hidden property. Webhooks retry. Queues redeliver if an acknowledgement is lost. Server-Sent Events reconnect and may resend. Networks generally can't guarantee a message arrives *exactly* once. What they can promise is *at least* once. The phrase to know is **at-least-once delivery**.

So the receiving side has to make duplicates harmless. The word is **idempotent**, said "eye-dem-POH-tent". An operation is idempotent if doing it twice has the same effect as doing it once. "Set the temperature reading for 3:00 to 41 degrees" is idempotent. "Add 41 to the running total" is not. "Mark order 5 as shipped" is idempotent. "Send the customer a shipping email" is not, unless you make it so.

The standard way to make an action idempotent is an **idempotency key**. The sender attaches a unique ID to each event. Most webhook senders already include an event ID. Before acting, the receiver checks a table of IDs it has already processed. If the ID is new, it does the work and records the ID, ideally in the same transaction. If the ID has been seen, it replies "already done" and does nothing. Stripe made this famous with an HTTP header literally called Idempotency-Key.

Pause and predict, using Timothy's work domain in general terms: imagine a system that receives a "shut down this virtual machine" command through a queue, and the acknowledgement gets lost, so the command arrives twice. What should the second delivery do? It should notice the machine is already shutting down, or that this command ID was already handled, and do nothing. If the handler instead started a second shutdown sequence, or worse, interpreted the second message as "the shutdown failed, try harder", the duplicate would cause real harm. The question "what happens if this arrives twice?" is one of the most valuable review questions you can ask about AI-written code.

The words to say to the AI: "make this handler idempotent using the event ID as an idempotency key."

## Connections to what you already know

This episode fits with your earlier work in a few ways. The state-machine lectures in general skills treated an event as an input that can cause a transition. Everything in this episode is plumbing for delivering those events. A webhook, a NOTIFY, a queue message, or a file event is just an input arriving at the edge of your state machine, and idempotency is the property that a repeated input doesn't cause a repeated transition. Your work application already has a worker that periodically triggers recalculation. That's a polling design, which may be exactly the right choice there, and now you have a name for the alternative and the trade-off: push is faster, while polling is simpler and naturally catches up after downtime. Your earlier networking and YARP lectures covered sockets and WebSockets. Server-Sent Events are the lighter sibling you can now place beside them.

## Recap

Let's restate the core ideas in slightly different words.

The power comes from the map, and every entry on the map carries a smell, a sentence, a place, and a catch. The smell is what makes you remember the concept at design time.

If you hear yourself say "it checks every few seconds", look for a push. Push means someone keeps a list of who to tell and has to handle failed delivery.

Webhooks: verify the signature, reply immediately, do the work later, and expect repeats, with an occasional catch-up poll if you can't miss anything.

Tunnels: the inside machine reaches out to a relay first, so the outside world can reach in without any open ports. Names: ngrok, Cloudflare Tunnel, Tailscale.

Changes can announce themselves: file watchers with debouncing, Postgres NOTIFY as a doorbell that stores nothing, change data capture as a durable mailbox read from the database's own log.

Queues separate producer and consumer in time and survive crashes through acknowledgements. Pub-sub gives every subscriber a copy. Watch for poison messages, which go to a dead-letter queue, and dual writes, which the outbox pattern fixes.

Server-Sent Events stream one way from server to browser over plain HTTP, the way AI chat answers appear word by word.

And under all of it: delivery is at least once, so handlers must be idempotent, using an idempotency key.

## Walk questions

Answer these out loud on your next walk.

One. Explain the difference between Postgres NOTIFY and change data capture, using the words "doorbell" and "mailbox", and give one situation where each is the right choice.

Two. Walk through the full, correct handling of a webhook, from the request arriving to the work being done, and say what goes wrong if you skip each step.

Three. Describe the dual-write problem in your own words, then explain how the outbox pattern fixes it, and why the fix depends on a single database transaction.
