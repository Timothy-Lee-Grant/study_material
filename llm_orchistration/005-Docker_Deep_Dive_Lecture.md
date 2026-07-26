2026_06_29_02_24-Docker_Deep_Dive_Lecture

# Lecture: Docker, From the Ground Up — Images, Containers, Volumes, Caches, Compose, and How Your Startup Scripts Drive It All

> A concepts lecture for Timothy Grant, written to directly answer the gaps you listed in `ConceptsINeedToReview.md` and to give you a mental model strong enough to **troubleshoot** your own system instead of "randomly doing commands."
> **Method (per `persona.md`):** macro → components → interactions → control flow → implementation in *your* files → edge cases, with embedded analogies and diagrams.
> You said: *"I don't know how to troubleshoot AT ALL because I don't understand the actual docker system being built up."* By the end of this you will have a model of every moving part and a troubleshooting procedure. This is the longest lecture in the project on purpose — Docker is the foundation everything else sits on.

---

## 0. The one paragraph that fixes your biggest pain (read this first)

Your `test_start_up.sh` runs `docker compose down -v` on every startup. The `-v` **deletes your `ollama_data` volume** — which is the *only place the downloaded LLM is stored*. So every single time you start your system, you **re-download the entire `qwen2.5:1.5b` model from scratch**, and then Ollama must **re-load it into memory** before it can answer. On an M1 Air, that is minutes of work *before your `curl` can possibly get a response.* The "freeze" you're seeing is almost certainly **not broken** — it's your machine re-pulling and cold-loading a model because the cache that was supposed to prevent that is being wiped every run. Understanding *why* `-v` does that is the single highest-value thing in this lecture, and it requires understanding volumes vs. caches (Module 4). Everything below builds the model that makes that obvious.

---

## 1. Executive overview — what Docker actually is

Docker solves one sentence: **"it works on my machine."** It packages an application *together with its entire operating-system userland* (Python version, system libraries, your code) into a single artifact that runs identically anywhere Docker runs.

For your project specifically, Docker is doing something more ambitious: it's letting you run **four independent services** — your .NET server, your Flask/LangChain service, the Ollama LLM runtime, and a one-shot model-puller — as if they were four separate computers on a private network, on one laptop. That is a miniature **distributed system**, which is exactly the skill you're trying to build.

```
        YOUR MACBOOK (the "host")
 ┌───────────────────────────────────────────────────────┐
 │   Docker Engine (a background daemon)                  │
 │                                                        │
 │   ┌────────────┐  ┌──────────────┐  ┌──────────────┐   │
 │   │  ollama    │  │ langchain_   │  │ ollama_pull_ │   │
 │   │  service   │  │ service      │  │ model (job)  │   │
 │   └─────┬──────┘  └──────┬───────┘  └──────┬───────┘   │
 │         └─────────── private network ──────┘           │
 │                          │                             │
 │                  ┌───────┴────────┐                    │
 │                  │  ollama_data   │  (a volume = disk) │
 │                  └────────────────┘                    │
 └───────────────────────────────────────────────────────┘
```

---

## 2. The four nouns you must never confuse: Image, Container, Volume, Network

This is the heart of your confusion ("all the ways images, containers, volumes, caches... interact"). Lock these four down and everything else follows.

| Noun | What it is | Lifecycle | Embedded analogy |
|------|-----------|-----------|------------------|
| **Image** | A *read-only template* — a frozen filesystem snapshot + a startup command. Built once. | Built, then immutable. Deleted with `docker rmi` / `image prune`. | A compiled, flashed firmware `.bin` |
| **Container** | A *running instance* of an image — a live process with its own isolated filesystem, network, PID space. | Created → running → stopped → removed. Ephemeral. | An MCU actually executing that firmware |
| **Volume** | A *persistent disk* that lives *outside* any container, mounted into one. Survives container death. | Independent of containers. Deleted only by `docker volume rm` or `down -v`. | An external EEPROM/SD card the MCU writes to |
| **Network** | A *private virtual LAN* connecting containers so they can address each other by name. | Created/destroyed with the compose project. | A backplane bus wiring boards together |

### Why this matters — the mental model that ends the confusion
- A **container's own filesystem is throwaway.** When a container is removed, *everything written inside it is gone* — unless it was written to a **volume**.
- That is *the entire reason volumes exist*: to hold data you want to keep across container rebuilds — databases, downloaded models, uploaded files.
- An **image** has no running anything; it's a template. You can make 100 containers from 1 image (like 100 MCUs flashed with the same firmware).

```
 IMAGE (template, read-only)
   │  docker run / compose up
   ▼
 CONTAINER (running, writable scratch layer that dies with it)
   │  mounts
   ▼
 VOLUME (persistent disk, outlives the container) ← your model lives HERE
```

### In *your* system
- **Images:** `llm_monitor-langchain_service` (you build it), `ollama/ollama:latest`, `curlimages/curl:latest` (you pull these).
- **Containers:** `langchain_service`, `ollama_service`, `ollama_pull_model` (instances of those images).
- **Volume:** `ollama_data`, mounted into the ollama container at `/root/.ollama` — **this is where the pulled model is saved.**
- **Network:** `llm_monitor_default`, auto-created by compose, lets `langchain_service` reach `http://ollama:11434`.

---

## 3. How an image is built: layers and the build cache (your "what is the cache?" question)

When Docker builds an image from your `dockerfile`, it executes each instruction and saves the result as a **layer** — a stacked, content-addressed filesystem diff.

Your Flask `dockerfile`:
```dockerfile
FROM python:3.9.13-slim-buster      # Layer 1: base OS + Python
COPY requirements.txt requirements.txt   # Layer 2: just that file
RUN pip install -r requirements.txt      # Layer 3: all the installed packages  ← the 30-second one
COPY . .                                  # Layer 4: your source code
CMD ["python3", "main.py"]                # metadata: what to run
```

### The build cache — what it is and why you want it
Docker caches each layer. On a rebuild, it walks top-down and **reuses a cached layer if that instruction *and everything above it* are unchanged.** The moment one layer changes, every layer below it must be rebuilt.

This is why the layer **order** in your Dockerfile is deliberately smart: `requirements.txt` is copied and `pip install`-ed *before* `COPY . .`. So when you edit `main.py` (changing only Layer 4), Docker **reuses the cached Layer 3** — your 30-second `pip install` is skipped. If you'd copied all source first, every code edit would re-install every package.

```
Edit main.py  ──▶  Layer 1 ✓cache  Layer 2 ✓cache  Layer 3 ✓cache  Layer 4 ✗rebuild
                   (base)           (requirements)   (pip install)   (your code)
                                    ▲ this is why pip install is skipped — huge time save
```

### The critical connection to YOUR pain
Your `test_start_up.sh` runs `build --no-cache`. **`--no-cache` throws away that entire optimization** and rebuilds every layer from scratch — re-running `pip install` (the ~30s download of flask, langchain, numpy, etc. you saw scroll by) on *every startup*. You almost never want `--no-cache`; it's a debugging tool for when you suspect a stale layer, not a daily-driver flag.

### Build cache vs. Volume — the distinction you explicitly asked about
You asked: *"How does Docker cache interact with Docker volumes?"* The honest answer: **they don't — they're unrelated systems that people confuse because both say 'saved'.**

| | Build cache | Volume |
|---|-------------|--------|
| **Purpose** | Speed up *building images* | Persist *runtime data* |
| **Created during** | `docker build` | `docker run` (a container writes to it) |
| **Holds** | Reusable layer-build steps | Your actual data (the LLM model, a DB) |
| **Cleared by** | `docker builder prune` / `build --no-cache` | `docker volume rm` / `compose down -v` |
| **In your project** | the cached `pip install` layer | `ollama_data` (the model) |

So `--no-cache` slows your *build*; `-v` wipes your *model*. Two different costs, both in your one script. Neither touches the other.

---

## 4. Volumes in depth — and the exact reason `down -v` is hurting you

A **volume** is storage managed by Docker that exists independently of containers. You mount it into a container at a path; whatever the container writes there is *actually* written to the volume on the host disk, and stays there after the container is gone.

Your compose declares:
```yaml
ollama:
  volumes:
    - ollama_data:/root/.ollama      # mount the named volume at Ollama's data dir
volumes:
  ollama_data:                       # declare the named volume
```
Ollama stores downloaded models under `/root/.ollama`. By mounting `ollama_data` there, the **model survives container restarts** — pull once, reuse forever. That is the *entire point*.

### The teardown spectrum (memorize this)
| Command | Stops containers | Removes containers | Removes network | **Removes volumes** |
|---------|:---:|:---:|:---:|:---:|
| `docker compose stop` | ✓ | ✗ | ✗ | ✗ |
| `docker compose down` | ✓ | ✓ | ✓ | ✗ (**keeps your model**) |
| `docker compose down -v` | ✓ | ✓ | ✓ | ✓ (**deletes your model**) |

Your `test_start_up.sh` uses the last row. So every run = model gone = re-download (~1 GB over your network) + re-load. On an M1 Air that's the difference between a ~5-second startup and a multi-minute one. The fix (covered in the AI_Suggestions doc) is to drop `-v` for normal runs and only wipe volumes when you *deliberately* want a clean slate.

> **Rule of thumb:** `down` for daily work; `down -v` only when you intend to destroy data. Treat `-v` like `rm -rf` on your data — because that's what it is.

---

## 5. The container lifecycle and *readiness vs. liveness* (your most important troubleshooting gap)

You wrote: *"I was told I need to wait until docker has fully started up... I don't understand what is failing, why, or how to use logs to determine the state."* This is the concept that unlocks troubleshooting.

### Two different questions
- **Liveness — "is the container running?"** This is what `docker ps` shows and what plain `depends_on` waits for. It flips to "up" the instant the process starts.
- **Readiness — "can the service actually do its job yet?"** A container can be *live* but not *ready*: Ollama's process is up, but it hasn't finished loading the model into RAM; Flask's process is up, but it's still importing langchain.

**The trap:** "container started" ≠ "service ready." Almost every "it works sometimes / hangs sometimes" bug in multi-container systems is a readiness race.

### How this bites your exact system
Your compose uses bare `depends_on`:
```yaml
langchain_service:
  depends_on:
    - ollama          # waits for ollama CONTAINER to start, NOT for it to be ready
ollama-pull-model:
  depends_on:
    - ollama          # same — starts pulling the moment ollama's process exists
```
Two race conditions result:
1. `ollama-pull-model` may start hitting Ollama before Ollama's API is actually listening. (You partly defended against this — your pull command has a `until curl ... do sleep 1` loop. That's a hand-rolled readiness wait! Good instinct.)
2. **Nothing waits for the model pull to *finish*.** When you `curl` `/test`, your Flask → `ChatOllama` → Ollama call may arrive while the model is *still downloading* or *loading*. Result: the request blocks (or errors), and you can't tell which.

### The timeline of what actually happened in your run
```
t=0   compose up: ollama, langchain, pull-model containers all START (live)
t=0   langchain is "live" → your curl could reach Flask immediately
t=1   pull-model waits for ollama API, then POSTs /api/pull qwen2.5:1.5b
t=1→? model DOWNLOADS (the repeating {"status":"pulling..."} lines you saw)
t=?   pull completes ({"status":"success"})
      ── only NOW can inference work ──
your curl  → Flask → ChatOllama → Ollama: if sent before t=?, it waits/cold-loads
            → on M1 Air, first inference also pays a model-load-into-RAM cost
```
So: **your system was very likely working — it was just not *ready* when you tested, and a 1.5B model on an M1 Air is genuinely slow on first call.** Not a bug; a readiness + hardware reality. The fix is to (a) stop wiping the model each run, and (b) make dependents *wait for readiness* (healthchecks — see AI_Suggestions).

---

## 6. Reading logs to determine system state (the skill you said you lack)

Logs are how you replace "I have no idea if it's working" with "I can see exactly what state each service is in." Here is a concrete procedure.

### The core commands
| Command | Answers |
|---------|---------|
| `docker compose -p llm_monitor ps` | Which containers are up/exited, and their status |
| `docker compose -p llm_monitor logs -f <svc>` | Live stream of a service's output (`-f` = follow) |
| `docker logs ollama_pull_model` | Output of the one-shot puller — did the pull finish? |
| `docker compose -p llm_monitor exec ollama ollama list` | Ask Ollama *inside the container* which models it actually has |
| `docker stats` | Live CPU/RAM per container — is the LLM actually computing? |

### A troubleshooting flow for *your* "is it working?" question
1. **Is everything up?** `docker compose -p llm_monitor ps`. Look for `langchain_service` and `ollama_service` as "running" (not "exited"). If a container exited, its logs tell you why.
2. **Did the model finish pulling?** `docker logs ollama_pull_model` → look for `{"status":"success"}`. If you don't see it yet, the model isn't ready — *that's why a chat hangs.*
3. **Does Ollama have the model loaded?** `docker compose -p llm_monitor exec ollama ollama list` → `qwen2.5:1.5b` should appear.
4. **Is it actually thinking, or hung?** Run `docker stats` while you curl. If `ollama_service` CPU jumps to 100%+, **it's working — just slow.** If nothing moves, the request never reached it.
5. **What did Flask see?** `docker compose -p llm_monitor logs -f langchain_service` while you curl → you'll see the request arrive and any Python exception.

That five-step loop *is* troubleshooting. The principle: **localize the failure by asking each layer, in order, "did the request reach you and what did you do with it?"** This is identical to how you'd debug a signal across boards in embedded — probe each stage from source to sink.

---

## 7. docker-compose: the orchestration layer

`docker-compose.yaml` is a declarative description of your whole multi-container system: which services exist, how they're built, how they network, what persists. `docker compose up` reads it and makes reality match it.

### Anatomy, mapped to your file
| Key | Meaning | In your file |
|-----|---------|--------------|
| `build` / `image` | build from a Dockerfile, or pull a prebuilt image | langchain builds; ollama/curl pull |
| `ports: "5001:5000"` | publish container port to host (**host:container**) | reach langchain at `localhost:5001` |
| `environment` | env vars injected at runtime | `OLLAMA_BASE_URL=http://ollama:11434` |
| `volumes` | mount persistent storage | `ollama_data:/root/.ollama` |
| `depends_on` | start-order (liveness only, unless you add conditions) | langchain & puller depend on ollama |
| `entrypoint` | override the container's start command | the puller's curl-loop |

### Two subtleties in your compose worth understanding
1. **Service name = hostname.** `OLLAMA_BASE_URL=http://ollama:11434` works because compose registers each service name as DNS on the private network. `langchain_service` resolves `ollama` to the right container IP. (Note it uses the **container** port 11434, not a host-published port — internal traffic stays internal. This is the rule from your earlier networking lecture, now in practice.)
2. **The one-shot job pattern.** `ollama-pull-model` isn't a long-running server — it runs a command and exits. That's a legitimate pattern (an "init job"). The gap is that nothing waits for it to *complete successfully* before allowing chats (Module 5).

---

## 8. How your `.sh` scripts drive all of this (your explicit question)

You asked how the startup scripts interact with the Docker components. A script is just a sequence of the same `docker` commands you could type by hand — automated and ordered. Let's annotate `test_start_up.sh` line by line in terms of the nouns above:

```bash
set -euo pipefail
#   ^ strict mode: stop on any error / undefined var / failed pipe stage

docker compose -p llm_monitor down -v --remove-orphans
#   ^ stop+remove CONTAINERS, remove NETWORK, and (because of -v) DELETE the
#     ollama_data VOLUME → this is what forces the model re-download every run

docker compose -p llm_monitor build --no-cache langchain_service
#   ^ rebuild the langchain IMAGE, ignoring the build CACHE → re-runs pip install (~30s)

docker compose -p llm_monitor up -d langchain_service ollama ollama-pull-model
#   ^ create the NETWORK + VOLUME, start the three CONTAINERS in background (-d)

docker image prune -f
#   ^ delete dangling IMAGES (old untagged layers) → frees disk, good

# (prints how to follow logs)
```

So the script's flow is: **destroy (containers+network+volume) → rebuild image (no cache) → recreate everything → clean dangling images.** Now you can *see* that two of these steps (the `-v` and the `--no-cache`) are the source of your slowness, because you understand what each noun is. That is what "understanding the system" buys you: the script stops being magic.

> `-p llm_monitor` pins the **project name**. Compose prefixes all resources with it (`llm_monitor_default`, `llm_monitor_ollama_data`). Pinning it means every run targets the *same* set of resources instead of accidentally creating parallel stacks — a real anti-clutter measure.

---

## 9. Edge cases & gotchas to file away

- **`down -v` is data destruction.** Once you add Postgres/pgvector, `-v` will wipe your database too. Build the habit now: `-v` only on purpose.
- **The ollama image lacks `curl`.** A known quirk: you can't put a `curl`-based healthcheck *inside* the ollama container. Your design dodges this neatly by using a *separate* `curlimages/curl` container to probe it — a clever workaround. (For a real healthcheck you'd use Ollama's own `ollama` CLI or `wget`.)
- **`debug=True` in Flask** runs the dev server with an auto-reloader — fine for local dev, never for production (it's slow and an RCE vector). Note it's a dev-only choice.
- **First inference is always slowest.** Ollama lazy-loads the model into RAM on first request; subsequent calls are faster. Don't judge performance by the cold call.
- **`slim-buster` is EOL.** Your base image is built on Debian Buster (end-of-life) and Python 3.9 (near EOL) — security and compatibility risk; a future upgrade target.
- **Apple Silicon + LLMs:** an M1 Air has no CUDA GPU and limited RAM; a 1.5B model is about the right size, but expect seconds-to-tens-of-seconds per response. That's hardware, not a bug.

---

## 10. Mental sandbox & next steps

1. **Prove the volume concept.** Run your system *without* `-v` in teardown twice. Time the second startup. Watch the model *not* re-download (`docker logs ollama_pull_model` shows it already present). Feeling that speed difference will cement volumes forever.
2. **Watch readiness happen.** `docker compose logs -f ollama` in one terminal, `docker stats` in another, then curl `/test`. Narrate aloud what each shows. You'll see "live but not ready," then "working but slow," directly.
3. **Map the four nouns in your head without looking.** For your system, list every image, container, volume, and network and what each holds. If you can do that cold, you understand the system.
4. **Draw the request path.** From your `curl` to `localhost:5001` all the way to Ollama and back — label every hop with host vs. container port and whether it crosses the Docker network. Compare to §6's troubleshooting order.

---

### Appendix — your `ConceptsINeedToReview.md` gaps, mapped to this lecture

| Your stated gap | Where it's answered |
|-----------------|---------------------|
| Docker Volumes | §2, §4 (and the `-v` pain in §0/§8) |
| Tear down / build up without cluttering | §4 teardown spectrum, §8 script walkthrough, `-p` + `image prune` |
| How `.sh` scripts interact with containers | §8 line-by-line |
| "Wait until docker fully started… use logs to see state" | §5 readiness vs liveness, §6 log procedure |
| How Docker cache interacts with volumes | §3 vs §4 — they *don't*; the table makes it explicit |
| "I can't troubleshoot because I don't understand the system" | §6 troubleshooting flow + the whole noun model in §2 |

> **Closing note.** You weren't "randomly doing commands" as much as you feared — your scripts are structurally sound and you even hand-rolled a readiness wait in the pull job. What was missing was the *model* of what each command touches. With the four nouns and the readiness concept, you can now look at any line and predict its effect — which is the definition of being able to troubleshoot. The companion **AI_Suggestions** document turns these insights into concrete, step-by-step fixes for you to implement.

*No source files were modified. Only this lecture was added to `Documentation/concepts_documentation/`.*
