<!-- id: a03_chat | family: A | level: core | minutes: 45 | bridge: none -->
# A03 · Chat (one-to-one and groups)

## The prompt

Design a messaging service like WhatsApp or Messenger. Users can send text messages one-to-one and in groups of up to 100 members. Messages are delivered in real time when the recipient is online; if they're offline, they receive the messages when they reconnect. Within a conversation, everyone sees messages in the same order. Message history is kept and can be scrolled back on any of a user's devices.

Assume 50 million daily active users, each sending about 40 messages a day. Delivery to an online recipient should take under a second.

## What this case trains

- **Server-to-client push**: persistent connections (WebSockets), and which server holds which user's connection.
- **Ordering** within a conversation (sequence numbers) and **exactly-once display** with at-least-once delivery (dedupe).
- **Offline delivery** and multiple devices per user.
- Fan-out for groups.

**Bridge coding piece:** none required. Optional: write `deliver(msg)` on the client side that discards duplicates and buffers out-of-order messages until the gap is filled (sequence numbers per conversation).

## Interviewer's notes (open only after your self-review, or give to the interviewer)

<details><summary>Answers to clarifying questions</summary>

- **Media, voice, video calls:** out of scope.
- **End-to-end encryption:** out of scope (mention it changes what the server can see).
- **Read receipts ("delivered", "read"):** nice to have; "delivered" is in scope.
- **Online/last-seen status:** stretch only.
- **Devices:** a user may have a phone and a laptop; both get every message.
- **Message size:** up to 4 KB of text.

</details>

<details><summary>Pushback questions the interviewer will ask</summary>

1. Alice and Bob are connected to different chat servers. Trace one message from Alice's phone to Bob's laptop.
2. How does the sending server know which server holds Bob's connection?
3. Two members of a group send a message at the same instant. How does everyone end up with the same order?
4. The chat server holding 200,000 connections crashes. What happens to those users and to messages in flight?
5. A message gets delivered twice because of a retry. How does the client avoid showing it twice?
6. Bob was offline for three days. What happens when he reconnects?
7. Estimate messages per second and storage per year. Which store do you choose for history, and why?

</details>

## After your attempt

- Compare with: Hello Interview problem breakdowns (overview: https://www.hellointerview.com/learn/system-design/problem-breakdowns/overview), the WhatsApp breakdown; Alex Xu vol. 1, "Design a Chat System".
