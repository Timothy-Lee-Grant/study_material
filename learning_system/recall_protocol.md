# Recall Protocol — analyzing Timothy's summaries ("walk-and-talk" recall checks)

> Read this before responding to any summary Timothy gives of a lecture or concept.
> **Why this exists:** Timothy learns by explaining out loud. He often talks into his phone on a walk, and the gaps show up when something "doesn't sound right" as he says it. This is a strong, research-backed strategy (retrieval practice plus self-explanation). These transcripts are the most valuable evidence in the whole system. Treat them carefully.

---

## 1. What the input looks like

- **Voice-transcribed, stream of consciousness.** Long, looping, self-correcting, with false starts. That's how he thinks. Don't penalize it.
- **Transcription errors are expected.** Read for intended meaning. Known mishearings (add to this list as you find them):

| Transcript says | He means |
|---|---|
| "state surface" | state service |
| "drive states" | derived states |
| "rose" (in a table context) | rows |
| "raspberry pie" | Raspberry Pi |
| "Marshall" | marshal (P/Invoke marshalling) |
| "C-sharp", "dot net", "net10" | C#, .NET, .NET 10 |
| "pinvoke" | P/Invoke |
| "powerful commands" | PowerShell commands (cmdlets) |

- He usually signals the mode: "I read X and want to summarize it." If he summarizes without saying whether he read it, ask. The analysis differs (first-pass reasoning vs retention).

## 2. The analysis (do it in the private recall-check file)

**Step 1: identify the target.** Which lecture(s), which sections? Load that lecture's **Core ideas** list (create it first if the lecture predates the requirement).

**Step 2: build the claim map.** Split the transcript into distinct claims and classify each:

| Mark | Meaning |
|---|---|
| ✅ Accurate | Matches the lecture/reality at a reasonable level of precision |
| 🟡 Imprecise | Right direction, wrong detail or fuzzy boundary (e.g. right mechanism, wrong layer) |
| ❌ Misconception | Confidently wrong. **Highest priority to correct.** |
| ❓ Flagged doubt | He said he wasn't sure. Record whether his doubt was *justified*: calibration matters. |
| 💡 Extension | A correct idea *beyond* the lecture: connection-making. Celebrate it and log it. |

**Step 3: find the gaps.** Which Core ideas didn't appear at all? A gap is omission, not error.

**Step 4: score it.**
- **Core recall:** accurately covered core ideas / total core ideas (count ✅ as 1, 🟡 as 0.5).
- **Misconceptions:** count, with severity (would it cause a bug or a wrong design decision?).
- **Calibration:** of the claims he doubted, how many were actually wrong? Of the confident claims, how many were wrong?
- **Altitude:** did he explain top-down (purpose → components → flow) or bottom-up? Where did he start?
- **Transfer:** did he connect the concept to firmware, his work, or another lecture?

**Step 5: diagnose the likely cause of each error.** Transcription? Never read that section? The lecture explained it poorly? A prior misconception resisting? A layer confusion (a known pattern)? This is what improves teaching.

## 3. The reply to Timothy (keep it tight; he may read it on his phone)

```
1. One-line verdict           e.g. "Strong recall of the mechanism; one real misconception about where the timeout lives."
2. What's solid (2–4 bullets) Specific, so he knows what to trust.
3. Corrections (max 3)        Highest impact first. For each: what you said → what's accurate → why,
                              at the right altitude, with a firmware twin if it helps. Quote his words briefly.
4. Gaps (max 3)               Core ideas he didn't mention, one line each, with the section to re-read.
5. Your doubts, checked       Tell him which of his flagged doubts were justified. This builds calibration.
6. Next walk (2–3 prompts)    Retrieval questions aimed at the gaps and corrections, not re-reading.
```

Target: **under ~500 words**. The full analysis lives in the private file. Offer it ("full claim map saved in your recall-check file").

Tone: he responds to honesty paired with respect. Lead with what's solid, but don't inflate. Never call an error "small" if it would cause a wrong design decision. Praise *specific* reasoning moves ("you deduced the keep-alive fix from first principles"), not generic effort.

## 4. After replying

1. Save `private/recall_checks/YYYY-MM-DD_<lecture-id>.md` using the template in `private/recall_checks/README.md`.
2. Update `private/reading_status.md`: status **recalled**, score, and the next spaced check dates (**+2 days, +1 week, +1 month** from this check; reset to +2 days after a check that scores under 60%).
3. Append to `private/observation_log.md`: learning-process observations (not just content). For example: "Explained bottom-up again, starting from the socket call," or "Used a firmware analogy unprompted."
4. If the evidence bears on a technique (e.g. the section with a personified cast was recalled much better), update `private/technique_experiments.md`.
5. Every 3rd recall check: run a consolidation (README §4).

## 5. Spaced follow-ups

When a check is due (see `reading_status.md`), add **one** line at the end of an unrelated reply: *"Next time you're walking: can you explain X without notes?"* Never more than one prompt per session, and never interrupt focused work with it.
