<!-- id: c01_parking_lot | family: C | level: starter | minutes: 45 | bridge: none -->
# C01 · Parking Lot

## The prompt

Design the classes for a parking garage system. The garage has several levels. Each level has spots of three sizes: motorcycle, compact and large. A motorcycle fits any spot, a car fits compact or large, and a bus needs a large spot. When a vehicle enters, the system assigns it a spot that fits and issues a ticket. When it exits, the system computes the fee from the time parked (for example $2 per started hour, with a daily maximum) and frees the spot. A display at the entrance shows how many free spots of each size each level has.

Design the classes, their responsibilities, their public methods, and how they interact. Pseudocode is fine; it doesn't need to run.

## What this case trains

- Turning use cases into **entities with one responsibility each**.
- Class **APIs** (inputs and outputs) before internals.
- **State**: what a spot and a ticket can be, and what changes them.
- **Extensibility**: adding a requirement without rewriting everything.

## Interviewer's notes (open only after your self-review, or give to the interviewer)

<details><summary>Answers to clarifying questions</summary>

- **Multiple entrances/exits:** yes, two of each.
- **Assignment policy:** lowest level first, smallest spot that fits; may change later.
- **Payment:** at an exit machine; payment processing itself is a black box (`PaymentProcessor.charge(amount)`).
- **Lost ticket:** charge the daily maximum.
- **Reservations:** out of scope.

</details>

<details><summary>Pushback questions the interviewer will ask</summary>

1. Add electric-vehicle charging spots that charge an extra per-hour fee. What changes in your classes?
2. Management wants a different assignment policy on weekends. Where does that change go?
3. Two cars arrive at two entrances at the same instant and the lot has one free compact spot. What does your code do?
4. Where does the "free spots per level" count live, and how does it stay correct?
5. What does a `Ticket` hold, and who is allowed to change it?
6. How would you test the fee calculation?

</details>

## After your attempt

- Compare with: Hello Interview, "Low-Level Design in a Hurry" (https://www.hellointerview.com/learn/low-level-design/in-a-hurry/delivery) and its worked problems.
