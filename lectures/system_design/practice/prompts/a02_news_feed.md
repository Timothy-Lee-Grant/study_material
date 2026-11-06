<!-- id: a02_news_feed | family: A | level: core | minutes: 45 | bridge: leetcode 23 merge k sorted lists -->
# A02 · News Feed (Twitter-style)

## The prompt

Design the backend for a social app where users post short text messages and read a home timeline. Users can follow other users. A user's home timeline shows recent posts from the people they follow, newest first, a page at a time. Opening the app should show the timeline in well under a second.

Assume 200 million daily active users. Each user opens their timeline about 10 times a day and posts about once every two days. Most users follow a few hundred accounts; a few accounts have tens of millions of followers.

## What this case trains

- **Read path vs write path**, and precomputing a view (a timeline) vs building it on demand.
- **Fan-out** (on write vs on read) and the **celebrity problem**.
- Pagination with a cursor; eventual consistency that the product can tolerate.

Lecture 001 §7 walks a compressed version of this case. Attempt it **without looking**, and go deeper than that walk-through, especially in steps 6 and 7.

**Bridge coding piece:** LeetCode 23, *Merge k Sorted Lists*: you're given `k` linked lists, each sorted ascending; return one sorted list containing all their nodes. Example: `[[1,4,5],[1,3,4],[2,6]] → [1,1,2,3,4,4,5,6]`. Constraints: `0 <= k <= 10^4`, each list up to 500 nodes. (It's exactly "merge recent posts from the accounts you didn't fan out for, at read time".)

## Interviewer's notes (open only after your self-review, or give to the interviewer)

<details><summary>Answers to clarifying questions</summary>

- **Ranking:** out of scope; reverse-chronological only.
- **Media (images, video):** out of scope.
- **Likes, replies, search:** out of scope.
- **Freshness:** a new post may take up to ~10 seconds to appear in followers' timelines. The author must see their own post immediately.
- **Page size:** 20 posts; infinite scroll.
- **Deleted posts:** must stop appearing within a minute.

</details>

<details><summary>Pushback questions the interviewer will ask</summary>

1. An account with 40 million followers posts. Walk me through what your system does, and how long it takes.
2. Estimate timeline reads per second at peak. What does that number force in your design?
3. A user follows a new account. When do that account's posts show up in their timeline?
4. How does the author see their own post instantly if fan-out is asynchronous?
5. How does pagination work if new posts arrive while the user is scrolling?
6. The timeline cache for a user is lost. How is it rebuilt, and what does the user see meanwhile?
7. How do you handle a deleted post that's already been fanned out to millions of timelines?

</details>

## After your attempt

- Compare with: Hello Interview problem breakdowns (overview: https://www.hellointerview.com/learn/system-design/problem-breakdowns/overview), the news feed breakdown; Alex Xu vol. 1, "Design a News Feed System".
