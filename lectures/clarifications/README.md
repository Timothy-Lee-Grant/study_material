# Clarifications — lectures built from my talk-throughs

This folder is different from the other lecture folders. The lectures here aren't requested on a topic. They're built from free-form talk-throughs: I describe what I *think* is true about whatever I've been studying (usually by voice on a walk), and the assistant keeps a running log of what's solid, what's fuzzy, and the higher-level concept each fuzzy spot comes from. When I ask, it writes a clarification lecture from that log.

Everything is here in the open on purpose: everyone has fuzzy spots, and this is just how I get to a clearer picture.

**How the loop works**
1. I paste a talk-through (voice-to-text, stream of consciousness, any mix of topics).
2. The transcript goes in [`intakes/`](intakes/), and the claims, root concepts and plan go in [`log.md`](log.md). (Method: `learning_system/clarifications_protocol.md`.)
3. I say "generate the clarifications lecture."
4. The assistant writes the next `NNN-title.md` here: grouped by topic, root concept first, then each confusion cleared up with one layer of context above it. Breadth, not depth.

**Why roots:** when I'm stuck on something, the real problem usually lives one level up. Fix that, and the things that grew out of it become easy.

## Index

| # | Lecture | Built from talk-throughs | Topics |
|---|---|---|---|
| — | *(none yet)* | | |

## Talk-throughs logged

| Date | Intake | Topics |
|---|---|---|
| 2026-11-04 | [CPU addresses, MMU, IPC, boot tables](intakes/2026-11-04_cpu-addresses-ipc-boot.md) | how addresses reach hardware, controllers/MMIO, virtual memory, plug-in devices, firmware + ACPI, pipes/sockets/TCP, blocking reads, framing |
