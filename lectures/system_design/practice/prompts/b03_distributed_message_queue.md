<!-- id: b03_distributed_message_queue | family: B | level: advanced | minutes: 45 | bridge: e03_bounded_blocking_queue -->
# B03 · Distributed Message Queue

## The prompt

Design a message queue service (in the spirit of Kafka). Producers publish messages to named topics. Consumers subscribe to a topic and read its messages. Several consumers can share the work of one topic as a group, so each message is processed by one member of the group; a different group reading the same topic gets every message too. Messages within a key (for example all messages for one order id) must be read in the order they were published. Messages are kept for 7 days whether or not they've been read.

Assume 1 million messages per second published at peak, average size 1 KB.

## What this case trains

- **Partitions** as the unit of ordering, parallelism and storage.
- **Offsets**: consumers track where they are; at-least-once vs at-most-once delivery.
- **Replication** of partitions and leader failover.
- Slow consumers and backpressure.

**Bridge coding piece:** `e03_bounded_blocking_queue` (the single-machine version: what blocks, who wakes whom).

## Interviewer's notes (open only after your self-review, or give to the interviewer)

<details><summary>Answers to clarifying questions</summary>

- **Delivery:** at-least-once is the default; consumers must tolerate duplicates.
- **Ordering:** only within a key, not across a whole topic.
- **Durability:** an acknowledged publish survives loss of one machine.
- **Consumers:** pull model (consumers ask for the next batch).
- **Message size limit:** 1 MB.

</details>

<details><summary>Pushback questions the interviewer will ask</summary>

1. Estimate the storage for 7 days of retention. How many machines is that, roughly?
2. Why does ordering per key force all messages of a key into one partition? What does that cost if one key is very hot?
3. A consumer processes a message, then crashes before recording its offset. What happens on restart?
4. The machine leading a partition dies. Which machine takes over, and how is no acknowledged message lost?
5. One consumer group falls 3 days behind. Does that affect other groups or producers?
6. A consumer group goes from 4 to 6 members. How are partitions reassigned?
7. Why store messages in an append-only log on disk rather than deleting them when read?

</details>

## After your attempt

- Compare with: Alex Xu, *System Design Interview* vol. 2, "Distributed Message Queue"; Apache Kafka documentation, "Design" section (⚫ optional depth).
