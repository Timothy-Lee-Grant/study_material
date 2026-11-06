<!-- id: c02_elevator_system | family: C | level: core | minutes: 45 | bridge: none -->
# C02 · Elevator System

## The prompt

Design the control software for a building with 20 floors and 4 elevators. Each floor has an Up and a Down call button (one each at the top and bottom floors). Each elevator car has a button for every floor, plus door-open and door-close buttons. When someone presses a call button, the system assigns an elevator to serve it. Each car moves one floor at a time, stops at floors it's been asked to serve in its direction of travel, opens its doors for a few seconds, and continues.

Design the classes, the state of each car, and the logic that decides which car answers a call. Pseudocode is fine.

## What this case trains

- A **state machine** for each car (see `../../../general_skills/001-thinking_in_states.md`).
- Separating **mechanism** (a car moves and opens doors) from **policy** (which car answers a call).
- Events from many sources (hall buttons, car buttons, sensors) changing shared state.

## Interviewer's notes (open only after your self-review, or give to the interviewer)

<details><summary>Answers to clarifying questions</summary>

- **Time:** the system receives a `tick()` every 100 ms; cars move one floor in 2 seconds.
- **Capacity / weight sensors:** a car reports "full"; a full car doesn't take new hall calls.
- **Dispatch policy:** start with "nearest car moving toward the call, or idle"; it may change.
- **Maintenance mode:** a car can be taken out of service by an operator.
- **Emergency (fire) mode:** stretch only.

</details>

<details><summary>Pushback questions the interviewer will ask</summary>

1. Draw a car's states and the event that causes each transition. Which transitions are illegal?
2. A car is moving up past floor 8 and someone on floor 8 presses Down. What does your system do?
3. Where does the dispatch policy live, and how would you swap it for a different one?
4. A car is put into maintenance while it has passengers' floor requests queued. What happens to them?
5. Two hall calls arrive in the same tick. Is there any shared state that can be corrupted?
6. How would you test the dispatcher without a real building?

</details>

## After your attempt

- Compare with: Hello Interview, "Low-Level Design in a Hurry" (https://www.hellointerview.com/learn/low-level-design/in-a-hurry/delivery) and its worked problems.
