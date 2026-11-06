# System Design

| Path | What it is |
|---|---|
| [`000-gradient_roadmap.md`](000-gradient_roadmap.md) | **The lecture plan:** how this series teaches (forced moves, one request traced, labs, paired practice cases) and which lecture comes next |
| [`001-system_design_orientation.md`](001-system_design_orientation.md) | The map: five families of design questions, one seven-step skeleton, the two toolkits, rate limiter as design vs code, how to practice |
| [`002-the_read_path.md`](002-the_read_path.md) | Lecture 1 of the gradient: one request traced end to end, then index → separate DB → stateless servers + load balancer → object storage → cache → replicas, each forced by a number. Lab: `code/read_path_lab.py`. Practice next: `a01` |
| [`practice/`](practice/) | **Where practice happens**: timed cases, a phase timer, rubric, drills, interviewer mode, attempt reviews and progress. Start at [`practice/README.md`](practice/README.md) |
| [`code/`](code/) | Runnable code from the lectures (`token_bucket.py`, `read_path_lab.py`) |

Related lectures elsewhere in the repo: `windows_internals/014` (a full device-to-app design), `leetcode/012` (data-structure design problems), `yarp/009` (distributed systems fundamentals), `general_skills/001` (thinking in states), `storage/001` (crash consistency).
