# Case Prompts

One file per case. Each file has:

1. **The prompt**: the full problem, with scale numbers. This is all you need for an attempt (`practice.py start` copies it into your attempt sheet).
2. **What this case trains**: OK to read before the attempt; it doesn't give answers.
3. **Interviewer's notes** (collapsed): answers to clarifying questions and the pushback questions an interviewer would ask. **Open only after your self-review**, or hand the whole file to the interviewer in interviewer mode.
4. **After your attempt**: where to compare.

| Id | Case | Family | Level | Bridge |
|---|---|---|---|---|
| `a01` | [URL shortener](a01_url_shortener.md) | A product | starter | e02 |
| `a02` | [News feed](a02_news_feed.md) | A product | core | LeetCode 23 |
| `a03` | [Chat](a03_chat.md) | A product | core | — |
| `a04` | [Notification system](a04_notification_system.md) | A product | core | e03 |
| `a05` | [Ride hailing](a05_ride_hailing.md) | A product | advanced | — |
| `b01` | [Distributed rate limiter](b01_distributed_rate_limiter.md) | B component | core | e01 |
| `b02` | [Distributed key-value store](b02_distributed_kv_store.md) | B component | advanced | e02 |
| `b03` | [Distributed message queue](b03_distributed_message_queue.md) | B component | advanced | e03 |
| `c01` | [Parking lot](c01_parking_lot.md) | C low-level | starter | — |
| `c02` | [Elevator system](c02_elevator_system.md) | C low-level | core | — |
| `d01` | [Device FIFO to a GUI](d01_device_fifo_to_gui.md) | D device | core | e04 |
| `d02` | [Power-safe event log](d02_power_safe_event_log.md) | D device | core | e04 |
| `d03` | [Sensor telemetry to a live plot](d03_sensor_telemetry_to_live_plot.md) | D device | core | leetcode/019 |
| `d04` | [Fleet firmware update that can't brick](d04_firmware_update_ab.md) | D device + A | advanced | — |
| `d05` | [Touch-to-pixel latency](d05_touch_to_pixel_latency.md) | D device | advanced | — |
| `e01` | [Token bucket](e01_token_bucket.md) | E code | starter | b01 |
| `e02` | [LRU cache with expiry](e02_lru_cache_with_ttl.md) | E code | core | a01, b02 |
| `e03` | [Bounded blocking queue](e03_bounded_blocking_queue.md) | E code | core | a04, b03 |
| `e04` | [Ring buffer](e04_ring_buffer.md) | E code | starter | d01–d03 |

**Adding a case:** copy any file, keep the `<!-- id: … -->` line at the top (the script reads it), and keep the `## The prompt` heading exactly as written. Or ask me to add one, for example from a question you got in a real interview.
