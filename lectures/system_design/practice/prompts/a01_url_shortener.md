<!-- id: a01_url_shortener | family: A | level: starter | minutes: 45 | bridge: e02_lru_cache_with_ttl -->
# A01 · URL Shortener

## The prompt

Design a URL-shortening service. A user submits a long URL and gets back a short link (for example `https://sho.rt/aZ3k9Qx`). Anyone who opens the short link is redirected to the original URL. Users may optionally choose a custom alias (`https://sho.rt/my-talk`) and an expiration date.

Assume about 100 million new short links per month, and about 100 redirects for every link created. Redirects should feel instant (tens of milliseconds on the server side), and links should keep working for years.

## What this case trains

- A **read-heavy** path: reads outnumber writes 100:1, so the design is shaped by the redirect path.
- **Generating unique IDs** across many servers without collisions.
- **Estimation that decides something** (how long must the code be? does the data fit on one machine?).
- Caching a hot read path.

**Bridge coding piece:** `e02_lru_cache_with_ttl` (the cache in front of the redirect lookup), and base-62 encoding of a number as a 15-minute warm-up.

## Interviewer's notes (open only after your self-review, or give to the interviewer)

<details><summary>Answers to clarifying questions</summary>

- **Custom aliases:** yes, optional. Must be unique; first come, first served.
- **Expiration:** optional; default is never expire.
- **Same long URL submitted twice:** may get two different short codes. (Deduplication is optional; ask what it would cost.)
- **Accounts / login:** out of scope; anyone can create links.
- **Analytics (click counts):** out of scope for the core; a good stretch topic if time allows.
- **Code alphabet:** letters and digits (62 characters) are fine.
- **Scale numbers:** 100M writes/month ≈ 40 writes/second average; ~4,000 redirects/second average; plan for peaks of ~3× that.

</details>

<details><summary>Pushback questions the interviewer will ask</summary>

1. How do you guarantee two servers never hand out the same short code at the same time?
2. How many characters does the code need? Show the derivation.
3. Do you return HTTP 301 or 302 for the redirect, and what does that choice cost you?
4. One link goes viral and gets 50,000 requests a second. What happens in your design?
5. The database holding the mappings is down. What do users who click links see?
6. Two users ask for the same custom alias at the same moment. Who wins, and how does your design enforce it?
7. How much storage do you need after five years?

</details>

## After your attempt

- Compare with: Hello Interview problem breakdowns (overview: https://www.hellointerview.com/learn/system-design/problem-breakdowns/overview), the URL-shortener ("Bitly") breakdown; Alex Xu, *System Design Interview* vol. 1, "Design a URL Shortener".
- Ask for a review to get a reference design in `review.md`.
