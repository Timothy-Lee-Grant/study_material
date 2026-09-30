# Audio Lecture Standards — lectures written for NotebookLM podcasts

> **When this applies:** ONLY when Timothy explicitly asks for an audio / listening / NotebookLM lecture. A plain "generate a lecture" always means the normal reading lecture (`lecture_standards.md`).
> **What happens to it:** Timothy uploads the file to Google NotebookLM as a source and generates an **Audio Overview** (a two-host, podcast-style conversation), then listens, often on a walk. He never reads the file itself. **The document is a script source for two AI hosts, not a page for a reader.**

---

## 1. Where it goes

- Folder: `lectures/<domain>/audio/`, file `NNN-title_audio.md` (numbering independent of the reading lectures in that domain).
- A small companion file `NNN-title_audio_prompt.txt` holds the **NotebookLM customization prompt** (§5). Keep it out of the source file so the hosts don't read production notes aloud.
- Add a row to `private/reading_status.md` with status **🎧 generated (audio)**. After he listens, the status becomes **🎧 listened**. Recall checks work the same way as for reading lectures.

## 2. Principles: write for the ear, and for two hosts who will paraphrase

NotebookLM's hosts summarize and discuss the source; they don't read it verbatim. So the source must make the *important* things hard to skip and the *visual* things unnecessary.

| Do | Don't |
|---|---|
| Flowing prose paragraphs with clear topic sentences | Tables, ASCII diagrams, box drawings: they can't be heard. Describe them in words. |
| **Describe code in words** ("a loop that keeps reading until the read returns zero, which means the other side hung up") | Code blocks. Allow at most one tiny snippet if the exact name is the point, and explain it in prose too. |
| Stories, scenarios, and **personified characters** ("the Doorman, Kestrel, accepts the connection…"). Audio thrives on narrative. | Dense lists of settings, defaults, and API members |
| Firmware analogies, stated explicitly ("For a firmware engineer, this is exactly an interrupt handler pushing into a ring buffer") | Emoji, 🟢/🔵/⚫ tags, `<details>` blocks, footnote-style references |
| **Signposting**: "There are three reasons. First… Second… Third…" | Nested bullet hierarchies |
| **Deliberate repetition** of the core ideas: state them early, use them in the middle, recap at the end | Assuming the listener can scroll back |
| Pronunciation help on first use: "YARP, said like 'yarp'", "C sharp", "P-invoke", "E-poll", "S-Q-L" | Unexplained acronyms, or symbols like `->`, `::`, `=>` |
| Numbers that matter, stated plainly and with meaning ("one hundred seconds, which is shorter than the server's two-minute default, and that's the whole bug") | Long numeric lists |
| Moments for the listener to think: "Pause here and predict: what happens if neither side sends anything?" | Self-check sections with hidden answers |
| One focused topic per source | Sprawling multi-topic sources. The hosts will pick highlights and skip the rest. |

## 3. Required structure

```
# <Title> (audio lecture)

Opening: why this matters to Timothy specifically (his situation, his words), and a one-paragraph promise of what the listener will understand by the end.

The core ideas, stated up front in plain sentences (5–8 of them). This doubles as the recall answer key.

Body: 3–6 sections, each built around ONE idea:
  - a concrete scenario or story
  - the mechanism, explained step by step in words
  - the firmware/hardware analogy
  - a common misconception, and why it's wrong
  - a "pause and predict" question

Connections: how this links to what he already knows (earlier lectures, his work, his open-source issue).

Recap: the core ideas again, in slightly different words.

Walk questions: 3 questions for him to answer out loud on his next walk (these feed the recall protocol).
```

## 4. Length

- Target **roughly 1,500–3,500 words** per source. Audio Overviews compress, so a longer source mostly means more gets skipped, not a longer podcast. (Recent NotebookLM versions offer length/format options; they don't change this principle.)
- For a big topic, make a **numbered audio series** (one idea cluster per episode) rather than one giant source.
- It's fine to write an audio version of an existing reading lecture. Keep the audio version self-contained, and don't edit the reading lecture.

## 5. The companion customization prompt (`_audio_prompt.txt`)

NotebookLM lets you "customize" an Audio Overview with instructions. Write 3–6 sentences, for example:

> The listener is a firmware engineer transitioning into .NET backend engineering, who prefers top-down explanations and firmware analogies. Focus on the core ideas listed at the start of the source, and make sure each one is explained with its mechanism, not just named. Spend the most time on [the key section]. Include the misconceptions and why they're wrong. End by restating the core ideas and posing the three walk questions.

## 6. Verification

The same standards apply as for reading lectures: research present-day facts first and verify claims. Put sources in a short **"Sources"** paragraph at the very end, as plain prose, or omit them from the audio file and list them in the prompt file. Hosts reading URLs aloud is useless.

## 7. Changelog

| Date | Change |
|---|---|
| 2026-09-29 | Created at Timothy's request (audio lectures for NotebookLM, only when explicitly asked). |
