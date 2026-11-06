<!-- id: e04_ring_buffer | family: E | level: starter | minutes: 45 | bridge: pairs with d01, d02, d03 -->
# E04 · Ring Buffer (code)

## The prompt

Write a fixed-capacity circular buffer `RingBuffer(capacity, overwrite=False)` backed by an array allocated once:

- `push(item) -> bool`: add `item` at the back. If the buffer is full: with `overwrite=False`, don't add it and return `False`; with `overwrite=True`, discard the **oldest** item, add the new one, count one drop, and return `True`.
- `pop() -> item or None`: remove and return the oldest item, or `None` if empty.
- `dropped() -> int`: how many items have been discarded by overwrite so far.

No allocation after construction; every operation O(1).

Example with `RingBuffer(3)`:

| Calls | Returns |
|---|---|
| `push(1)`, `push(2)`, `push(3)`, `push(4)` | `True`, `True`, `True`, `False` |
| `pop()` | `1` |
| `push(4)` | `True` |
| `pop()`, `pop()`, `pop()`, `pop()` | `2`, `3`, `4`, `None` |

Example with `RingBuffer(3, overwrite=True)`:

| Calls | Returns |
|---|---|
| `push(1)`, `push(2)`, `push(3)`, `push(4)` | all `True` |
| `pop()`, `pop()`, `pop()`, `pop()` | `2`, `3`, `4`, `None` |
| `dropped()` | `1` |

## What this case trains

- **What each index stands for** (a box or a cut: see `../../../leetcode/008-indices_and_bounds_toolkit.md`), and the classic **full vs empty ambiguity** when `head == tail`.
- The **overflow policy** from the D cases, as code.
- Wrap-around arithmetic with `%`.

## Interviewer's notes (open only after your self-review, or give to the interviewer)

<details><summary>Answers to clarifying questions</summary>

- **Threads:** single-threaded for the base version.
- **capacity:** at least 1.
- **Which state to keep:** your choice (head + tail, head + count, …); be ready to defend it.

</details>

<details><summary>Pushback questions the interviewer will ask</summary>

1. If you store only `head` and `tail`, how do you tell a full buffer from an empty one? Give two different fixes and their costs.
2. What exactly does `head` stand for in your code: the next box to read, or the last box read? What about `tail`?
3. Trace `RingBuffer(3, overwrite=True)` through the example with your index values in a table.
4. One producer (an interrupt handler) and one consumer (a thread) use this buffer with no lock. Which variable does each side write? Why can that work for exactly one producer and one consumer?
5. Capacity is a power of two. What can replace `%`, and why is that faster?
6. In D01, would you choose `overwrite=True` or `False` for the driver's buffer? Why?

</details>

## After your attempt

- Compare with: `../../../windows_internals/014-device_to_app_data_path.md` §4–5 (kfifo / ring buffer in a driver) and §7 (overflow policy); ask for a review for a reference solution.
