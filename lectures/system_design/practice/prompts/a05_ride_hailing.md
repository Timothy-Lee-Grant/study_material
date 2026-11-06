<!-- id: a05_ride_hailing | family: A | level: advanced | minutes: 45 | bridge: none -->
# A05 · Ride Hailing (Uber-style)

## The prompt

Design the backend for a ride-hailing app. A rider requests a ride from their current location to a destination. The system finds nearby available drivers and offers the ride to them; the first one to accept gets it. From then until drop-off, the rider sees the driver's location update live on a map, and the driver sees the rider's pickup point.

Assume a large metro area with 500,000 active drivers, each sending their GPS location every 4 seconds while the app is open, and about 1 million ride requests per day. A rider should get a match in under 10 seconds when drivers are available.

## What this case trains

- **High-frequency writes** (location updates) that mostly don't need to be stored forever.
- **Geospatial lookup**: "drivers near this point" (grids, geohash, quadtrees).
- **Contention**: two riders must never get the same driver.
- Live updates to a client.

**Bridge coding piece:** none required. Optional: write `nearby(lat, lng, radius)` over a grid index (a dict from cell → set of drivers) and `update(driver, lat, lng)` that moves a driver between cells.

## Interviewer's notes (open only after your self-review, or give to the interviewer)

<details><summary>Answers to clarifying questions</summary>

- **Payments, pricing, surge:** out of scope (show where a fare would be computed).
- **Ride types (pool, XL):** out of scope.
- **Matching policy:** offer to the nearest available driver; if they don't accept in 10 seconds, offer to the next.
- **Location history:** store the route of each trip; raw idle-driver pings don't need to be kept.
- **Map rendering / ETA computation:** use a third-party maps service (black box).

</details>

<details><summary>Pushback questions the interviewer will ask</summary>

1. Estimate location updates per second. Can one database take that write rate? What do you do instead?
2. How do you find the 10 nearest available drivers to a point quickly?
3. Two riders' requests are offered to the same driver, and the driver taps accept. How do you guarantee only one ride gets the driver?
4. The driver doesn't respond to the offer. What does the system do, and where does that timer live?
5. How does the rider's map receive the driver's new position every few seconds?
6. The service holding the location index restarts. How quickly can it rebuild, and from what?
7. A driver's phone loses signal for 2 minutes mid-trip. What do both sides see?

</details>

## After your attempt

- Compare with: Hello Interview problem breakdowns (overview: https://www.hellointerview.com/learn/system-design/problem-breakdowns/overview), the Uber breakdown; Alex Xu, *System Design Interview* vol. 2, "Proximity Service" and "Nearby Friends".
