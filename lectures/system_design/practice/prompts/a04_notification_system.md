<!-- id: a04_notification_system | family: A | level: core | minutes: 45 | bridge: e03_bounded_blocking_queue -->
# A04 · Notification System

## The prompt

Design a service that other internal services call to notify users. A caller says "send notification X to user U" (or to a list of users), and the system delivers it over the channels the user has enabled: mobile push, email, and SMS. Users can turn channels off and set quiet hours. Delivery goes through third-party providers (a push service, an email provider, an SMS provider).

Assume 10 million notifications on a normal day, with marketing campaigns that send 20 million in an hour. Security notifications (password reset, login codes) must arrive within seconds even during a campaign. A user should not receive the same notification twice.

## What this case trains

- **Queues** to absorb bursts and decouple callers from slow providers.
- **Retries with backoff** and **idempotency** (no duplicates despite retries).
- **Priorities**: keeping urgent traffic fast while bulk traffic waits.
- Dealing with an unreliable third party.

**Bridge coding piece:** `e03_bounded_blocking_queue` (the producer–consumer core of every worker here).

## Interviewer's notes (open only after your self-review, or give to the interviewer)

<details><summary>Answers to clarifying questions</summary>

- **Templates:** callers send a template id plus variables; the system renders the text.
- **Delivery guarantee:** at least once to the provider, with deduplication so the user sees it once.
- **Ordering:** not required across notifications.
- **Tracking:** record sent / failed / delivered (where the provider reports it).
- **Rate limits:** providers limit how fast you can send (e.g. the SMS provider allows 500/second); the system must respect that.
- **Per-user limits:** no more than 5 marketing notifications per user per day.

</details>

<details><summary>Pushback questions the interviewer will ask</summary>

1. A campaign of 20 million is enqueued at 9:00, and at 9:01 someone requests a password reset. How does the reset get out in seconds?
2. The email provider times out on a request. Did the email go out or not? What do you do?
3. How exactly do you prevent a user from receiving a duplicate after a worker crashes mid-send?
4. The SMS provider is down for 20 minutes. What happens to the queue, and what happens when it comes back?
5. Where are user preferences stored, and what happens if that store is slow?
6. How do you respect the provider's 500/second limit with 50 workers running?
7. How would you know, from a dashboard, that something is wrong?

</details>

## After your attempt

- Compare with: Alex Xu vol. 1, "Design a Notification System"; Hello Interview problem breakdowns overview (https://www.hellointerview.com/learn/system-design/problem-breakdowns/overview).
