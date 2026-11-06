<!-- id: e03_bounded_blocking_queue | family: E | level: core | minutes: 45 | bridge: pairs with a04_notification_system, b03_distributed_message_queue -->
# E03 · Bounded Blocking Queue (code, threads)

## The prompt

Write a thread-safe class `BoundedBlockingQueue(capacity)` with three methods:

- `enqueue(item)`: add `item` at the back. If the queue already holds `capacity` items, **block** (wait without spinning) until there's room.
- `dequeue() -> item`: remove and return the item at the front. If the queue is empty, **block** until an item arrives.
- `size() -> int`: the number of items currently in the queue.

Several producer threads and several consumer threads use the same queue at once. Use Python's `threading` module (or C#'s `Monitor`, or C with pthreads, your choice).

Single-thread example with `BoundedBlockingQueue(2)`:

| Call | Returns |
|---|---|
| `enqueue(1)` | |
| `enqueue(2)` | |
| `size()` | `2` |
| `dequeue()` | `1` |
| `enqueue(3)` | |
| `dequeue()` | `2` |
| `dequeue()` | `3` |
| `dequeue()` | blocks until another thread enqueues |

Multi-thread test you must pass: capacity 5; 3 producer threads each enqueue 1,000 distinct integers; 2 consumer threads each dequeue 1,500. Afterwards all 3,000 integers were dequeued exactly once, the queue never held more than 5 items, and no thread is stuck.

## What this case trains

- **Producer–consumer** in code: the single-machine version of every queue box (lecture 001 §6).
- **Condition variables**: waiting, signaling, and why the wait sits in a `while` loop.
- Writing a **concurrency test** that would catch a bug.

## Interviewer's notes (open only after your self-review, or give to the interviewer)

<details><summary>Answers to clarifying questions</summary>

- **Ordering:** FIFO.
- **Fairness between waiting threads:** not required.
- **Timeouts:** not in the base version (follow-up).
- **Library:** you may not use `queue.Queue` (that's the thing being built); `threading.Lock` and `threading.Condition` are fine.

</details>

<details><summary>Pushback questions the interviewer will ask</summary>

1. Why must the wait be inside `while queue_is_full:` and not `if queue_is_full:`? Describe the exact interleaving that breaks the `if` version.
2. You use one condition variable with `notify()` (not `notify_all()`). Construct a case where every thread ends up waiting forever.
3. Two conditions (`not_full`, `not_empty`) vs one: what does each cost?
4. Add `enqueue(item, timeout)` that returns `False` if there's no room in time.
5. Add `close()`: after it, producers get an error and consumers drain what's left, then get an end marker. What do blocked threads do?
6. Where would this structure appear inside a device driver or a notification worker, and what would be different there?

</details>

## After your attempt

- Compare with: `../../../concurrency/002-how_the_os_runs_programs_and_threads.md` §6 (wait lists and run queues) for what "block" means underneath; ask for a review for a reference solution.
