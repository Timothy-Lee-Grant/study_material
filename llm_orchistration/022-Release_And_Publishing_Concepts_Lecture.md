2026_07_26_10_00-Release_And_Publishing_Concepts_Lecture

# Release & Publishing Concepts — Secrets, Registries, and What "1.0" Actually Means

You asked three questions: (1) does having real API keys in `.env` put you at risk if you publish a public Docker image via GHCR, (2) what are the actual options for releasing this project professionally, with trade-offs and steps, and (3) do you need to rewrite git history to get a "1.0.0" package published given you already pushed that tag. These read as three separate questions, but they collapse into one underlying idea once you see it: **a git repository, a container image, and a git tag are three different artifacts that live in three different places, get created at three different times, and can be individually rebuilt/republished/moved without touching the other two.** Once that separation is clear, all three of your questions have clean, low-risk answers. This lecture builds that mental model, then applies it.

---

## Part 1 — Does the `.env` secret put you at risk when you publish a public image?

**Short answer: no, verified, not "probably."** Here's how to know that for certain rather than trust it on faith — the verification habit matters more than the specific answer, because you'll ask this question again about a different project someday.

### The core distinction: build time vs. run time

A Docker image is a frozen filesystem snapshot, built once from a `Dockerfile`, then pushed to a registry as an immutable artifact. A running *container* is that snapshot plus whatever environment variables you hand it *at the moment you start it* (`docker run -e ...` or Compose's `environment:` block). These are genuinely different moments with different actors:

```
BUILD TIME (once, by CI, produces the public artifact)
  docker build -f langchain_service/dockerfile ./langchain_service
    → COPY requirements.txt, COPY . .   (whatever's in the build context)
    → pushed to ghcr.io/... as a public, immutable image

RUN TIME (every time, on each pull-and-run consumer's own machine)
  docker compose up
    → reads THEIR .env
    → injects THEIR keys as env vars into a container made from the PUBLIC image
```

The image only contains what got `COPY`'d into it during the build. Your `.env` values never participate in that build unless something explicitly copies `.env` in — a real, common mistake (more below), just not one this repo makes. Every consumer of the public image supplies their *own* secrets at their *own* run time; the image itself is secret-agnostic by construction. This is exactly the mock/live seam this project already uses for models, generalized to images: the artifact doesn't know or care what real values it'll be handed later.

### What I actually checked, and how you'd check it yourself

Trusting "the image shouldn't contain secrets, based on how Dockerfiles usually work" isn't good enough — that's a claim about a class of Dockerfiles, not verification of *this* one, and it's exactly the kind of unverified assumption that caused Story C in this project's own history (the `PGVector` kwargs mismatch, closed only by reading the actual installed source). Same discipline here:

1. **Is `.env` even reachable by the build?** Docker's build *context* is scoped to whatever directory you point `docker build` at — for this repo, `context: ./langchain_service` and `context: ./server` (see `docker-compose.yaml`). `.env` lives at the repo root, outside both directories. It is structurally impossible for `COPY . .` inside either Dockerfile to pick it up — not because of a rule being followed correctly, but because it's not in the folder being copied from at all. This is the strongest kind of "safe" — safe by geometry, not safe by discipline someone has to remember to maintain.

2. **Even if it somehow were reachable, is it excluded?** `langchain_service/.dockerfile` also lists `.env` in its `.dockerignore` — belt-and-suspenders, redundant given point 1, but correct.

3. **Has `.env` ever been committed to git, even before `.gitignore` caught it?** `.gitignore` only stops *future* commits — it does nothing retroactively. If a key were committed once, years ago, and later gitignored, it would still sit in the repo's history forever, downloadable by anyone with `git clone`, regardless of GHCR. Checked directly:

   ```bash
   git log --all --full-history -- .env
   # (no output = the file has never existed in any commit, on any branch, ever)
   ```

   Confirmed empty for this repo. Also grepped the full history of every `.yaml`/`.yml`/`.env`-named file ever committed for key-shaped strings (`sk-...`, `gsk_...`, a populated `AZURE_OPENAI_API_KEY=`) — nothing. `docker-compose.yaml` only ever contains `${VAR:-default}` *references*, never literal secret values.

4. **Do the "defaults" in those `${VAR:-default}` references leak anything real?** No — they're either empty (`${AZURE_OPENAI_API_KEY:-}`, fails loudly if actually needed) or deliberately non-secret local placeholders (`POSTGRES_PASSWORD:-secret_pass`, `LANGFUSE_PUBLIC_KEY=pk-lf-local-llm-monitor`). That last one is worth understanding, not just accepting: Langfuse's keys here authenticate against a Langfuse instance *you are also self-hosting on the same machine* — there is nothing on the other end of that credential for anyone to reach, on any network, ever. A hardcoded credential is only a real secret if it grants access to something that exists independently of the code that contains it. This one doesn't. Contrast that with `OPENAI_COMPAT_API_KEY` (Groq) or `AZURE_OPENAI_API_KEY` — those *do* grant access to something real (your account, your spend), which is exactly why the code never hardcodes a default for them and fails loudly instead.

### The mistake this *would* be, so you can recognize it in someone else's project

```dockerfile
# DON'T DO THIS
COPY .env .env
ENV $(cat .env | xargs)
```
or committing a `.env` "just for now" and gitignoring it later, or a CI step that echoes secrets into build logs (GitHub Actions logs are sometimes public/shareable even on private repos, and definitely if the repo goes public later). Any of these bakes a specific, static value into a specific, immutable, potentially-public layer — permanently, until that key is rotated. The fix if this ever happens to you: rotate the key at the provider immediately (a new build with the old value scrubbed does *not* retroactively invalidate a key that already leaked — someone could have pulled the old image or cloned the old commit in the window before you noticed).

### The one-line audit you can run on *any* image before trusting it

```bash
docker run --rm <image> env              # what env vars does a bare container start with?
docker history --no-trunc <image>        # what did each build layer actually DO?
```
Neither of these requires reading a single line of source — a genuinely useful, portable habit for auditing images you didn't build yourself, too.

**Conclusion: publishing `dotnet_server` and `langchain_service` as public GHCR images carries no secret-exposure risk today, verified rather than assumed.** Nothing about *this* answer changes if you later add more provider integrations — just re-run the same checks against the new Dockerfile/compose changes rather than assuming the old answer still holds.

---

## Part 2 — What does "releasing" this project actually mean? The real spectrum

"Release it" isn't one thing — it's a spectrum of how much friction you remove for someone else to *experience* your project, and each rung costs more to build and maintain than the last. Ordered cheapest → most expensive:

### Option 1 — Tag + GitHub Release notes, source only

**What it is:** an annotated git tag, and a curated "Release" page on GitHub (GitHub's own feature, distinct from a tag — a tag is a git object, a Release is a GitHub UI wrapper around one that can carry a title, markdown notes, and attached files). No built artifact published anywhere; a visitor still runs `./build.sh` themselves.

| | |
|---|---|
| **Advantages** | Zero infrastructure, zero ongoing cost, zero maintenance burden. Release notes are close to *curation* here, not writing from scratch — this project's own `Documentation/AI_Implementation_Plans/` logs are the raw material. Matches "read the code" as the actual pitch for a portfolio project. |
| **Disadvantages** | A recruiter/interviewer has to clone, have Docker installed, and wait through a real multi-service build (`dotnet build`, `pip install`, image builds) before seeing anything — real friction for someone giving your project 90 seconds of attention. |
| **When it's right** | Always — this is the floor, not an alternative to the other options. Every release should have this regardless of what else it has. |

**Steps:**
1. Decide the version number (see Part 3 — you already have `v1.0.0` pushed; resolve that first).
2. `gh release create v1.0.0 --title "..." --notes-file <curated-notes.md>` (or the GitHub UI) — draft notes from the `AI_Implementation_Plans/001-004` logs and the Stage 5 verification entries already in this repo.
3. Done. This step is required infrastructure for Options 2 and 4 below too (they both still want a tagged release as the anchor point), so it's never wasted work.

### Option 2 — Publish pre-built images to a registry (GHCR) — the thing you already did once, for Tool_Box

**What it is:** CI builds `dotnet_server` and `langchain_service` on tag push and pushes them to `ghcr.io/timothy-lee-grant/llm_monitor-*`, exactly the `docker_image_release.yml` pattern already proven working for Tool_Box in this same repo's history. A consumer runs `docker compose pull && docker compose up` — no local build step, no dotnet/Python toolchain required on their machine at all.

| | |
|---|---|
| **Advantages** | The single biggest friction reduction available: someone can go from `git clone` to a running system in the time it takes to `docker pull`, not the time it takes to compile. Directly, concretely resume-relevant — "built and maintain a CI/CD image-publishing pipeline" is a real, provable claim once this exists, not aspirational. You already own 90% of the hard-won knowledge this needs (multi-arch QEMU/buildx, GHCR visibility defaulting to private, lowercase image-name requirements) — this is *reuse*, not new risk. |
| **Disadvantages** | Two more images to version and keep building (vs. Tool_Box's one). `docker-compose.yaml` needs a variant that says `image: ghcr.io/...:TAG` instead of `build: context: ...` for these services, or the build-from-source path stops being the thing that's actually tested by a fresh clone. Ongoing discipline: every real release now means a real multi-arch build + a version bump, not just a commit. |
| **When it's right** | Once you're confident the pipeline is genuinely stable — this is exactly the "1.0" moment, not before. Publishing broken images under a version tag is worse than not publishing at all (SemVer's entire value proposition is that a version number is a *promise* about what's inside it — see Part 3). |

**Steps** (this is the meaty one — a real implementation plan, not a one-liner):
1. Write `dotnet_server_image_release.yml` and `langchain_service_image_release.yml` (or one workflow with a matrix), modeled directly on `Tool_Box/.github/workflows/docker_image_release.yml`: `actions/checkout` → `docker/setup-qemu-action` → `docker/setup-buildx-action` → `docker/login-action` (GHCR) → lowercase-image-name step → `docker/metadata-action` for tag computation → `docker/build-push-action` with `platforms: linux/amd64,linux/arm64` **from the first commit, not added after discovering the hard way a second time.**
2. Trigger on `push: tags: ["v*.*.*"]`, matching Tool_Box's convention — one tag scheme across both repos, one mental model.
3. First publish will land as a **private** GHCR package by default (exactly the Tool_Box gotcha) — flip visibility to public in the package's own Settings once it exists, before telling anyone to pull it.
4. Add a `docker-compose.release.yml` (an *override* file, not a replacement — `docker compose -f docker-compose.yaml -f docker-compose.release.yml up`) that swaps `build:` for `image: ghcr.io/timothy-lee-grant/llm_monitor-langchain_service:${TAG}` and similarly for the gateway. Keeps the source-build path (what CI itself uses, what you use for active development) completely separate from the "just run the released version" path — the same "tests boot the exact app production runs" principle Tool_Box's own `ToolBoxHttpApp.Build` extraction already models.
5. Update the README's quickstart to offer *both* paths explicitly: `git clone && ./build.sh` (build from source, what a contributor/reviewer of the code wants) vs. `docker compose -f docker-compose.yaml -f docker-compose.release.yml up` (pull and run, what someone just trying the demo wants).

### Option 3 — A single "run me" script or Makefile target

Not really a separate infrastructure tier — a polish layer on top of Option 1 or 2 that collapses "read the quickstart, run three commands" into one command a recruiter can copy-paste without thinking. Cheap to add once Option 1 or 2 exists; not worth building in isolation.

### Option 4 — Full cloud deployment (Azure) — a live, hosted, click-a-link demo

**What it is:** the AKS/ACA + Key Vault + managed identity + GitHub Actions CD path already sketched as future work in `persona.md` and flagged as a *separate* plan in `004-Release-1.0.md`'s own Stage 2 discussion.

| | |
|---|---|
| **Advantages** | Maximum impact for a recruiter — a URL beats a clone-and-build instruction every time, and it's the most direct, unambiguous demonstration of the Azure skills this whole pivot (Groq deferral included) was staged around. |
| **Disadvantages** | Real, ongoing cost for something running 24/7. No auth or rate-limiting exists yet (README's own "Roadmap" section says so plainly) — a public endpoint in front of a paid model API without either is a real abuse-cost risk, not a hypothetical one. Something running unattended *will* eventually break, and nobody's watching it page anyone. This is precisely why Groq was chosen over Azure for the *current* release — spending the Azure trial credit's time-boxed window on a fragile v1 deployment forfeits the thing that made deferring it worthwhile in the first place. |
| **When it's right** | As its own deliberate, scoped plan — exactly what `004-Release-1.0.md` already decided. Bolting it onto this release under time pressure would produce a worse outcome on both fronts (a rushed, under-secured deployment *and* a wasted trial-credit window) than doing it properly, later, on purpose. |

No new steps here — this is a pointer, not a plan: when you're ready, it's `005` (or whatever the next open `AI_Implementation_Plans` slot is), staged the same five-part way plans 001–004 were, starting from Stage 1 design goals, not from "let's just deploy it."

### Option 5 — Package manager distribution (NuGet, PyPI, etc.)

Explicitly **not applicable** here, for the same reason Tool_Box's own Release-1.0 plan deferred its NuGet option: this is an *application* (a set of services you run), not a *library* other code imports and builds against. Nobody `pip install`s a docker-compose stack. Worth naming only so the option is consciously rejected, not silently never considered — the same "don't half-build a package nobody pulls" discipline already established elsewhere in this project's documentation.

### Recommendation

Given this project's own stated goals — a Microsoft SWE2-focused resume artifact, a YouTube walkthrough, and `004-Release-1.0.md`'s already-decided "self-hosted, zero-paid-account" scope — the right sequence is:

1. **Do Option 1 now.** It's required infrastructure for everything else and costs nothing.
2. **Do Option 2 as the actual "1.0" deliverable.** It's the highest-leverage investment available: you already paid the learning cost building it for Tool_Box, it pairs directly with the YouTube demo (viewers can `pull` along with you instead of waiting through a build on camera), and "I built and maintain a multi-arch image-publishing CI pipeline" is a stronger, more specific resume line than "it's on GitHub."
3. **Defer Option 4 deliberately**, exactly as already decided — not because it's not valuable, but because doing it *properly* (with auth, with rate-limiting, with a real budget plan) is worth more than doing it *now*, and this release was explicitly scoped around not needing it.

---

## Part 3 — Tags, "releases," and whether you need to rewrite history

### The concept: a tag is a label, not a copy of history

A git commit is an immutable, content-addressed object — its SHA is a hash of its contents plus its parent's SHA, which is *why* changing a commit changes every SHA after it (that's what "rewriting history" actually means, and why it's disruptive: anyone who already has the old SHAs now has a diverging history). A **tag**, by contrast, is just a named pointer *at* one specific commit — a sticky note, not a container. Moving a sticky note, or throwing it away and writing a new one, changes zero commits. Nothing about the commit graph is altered either way.

```
commits:  A---B---C---D---E   (each SHA depends on everything before it — "history")
                    ↑
              v1.0.0 tag       ← just a name pointing at commit C.
                                 Deleting/moving this tag: touches NOTHING about A-E.
                                 Rebasing/amending commit C: changes C's SHA, and D's, and E's — THAT is "rewriting history."
```

CLAUDE.md's "never change git history" rule is about the second thing — rebase, `commit --amend` on a pushed commit, `filter-branch`, force-pushing a *branch* — operations that alter commit SHAs other people may have already built on. It is not about tags, and moving a tag requires no such operation.

### Why the workflow didn't (and won't) retroactively fire

GitHub Actions triggers react to **events** — a push happening, right now, matching a pattern in `on:`. A tag that already existed on the remote *before* a workflow file was added, or before that workflow was last modified, generated no push event *after* the workflow started watching for one — so there's nothing for it to have reacted to. This isn't a bug or a gap to work around; it's the whole model. (Verified in this repo directly: `v1.0.0` is pushed to `origin`, points at commit `280e0f3`, HEAD is now two commits ahead at `d0a4168`, and `.github/workflows/` currently has only `ci.yml` — no publish-on-tag workflow exists yet for this repo's own images at all. There is genuinely nothing for a tag-push trigger to have fired *from* yet.)

### Three real ways forward, ranked

1. **Bump the version — recommended, and exactly what you already did once for Tool_Box.**
   ```bash
   git tag -a v1.0.1 -m "Release 1.0.1"
   git push origin v1.0.1
   ```
   Zero risk, zero history touched, matches the pattern you already have muscle memory for. This is also the *only* option that's actually correct under SemVer's own rules: a version tag is a promise to consumers that "1.0.0" always means the same bytes. If `1.0.0`'s *published image* quietly became something different after the fact, that promise breaks for anyone who already pulled it — a subtle, real-world class of bug (a CI runner or a teammate with a cached `1.0.0` silently diverging from a freshly-pulled `1.0.0`).

2. **Delete and recreate the same tag.**
   ```bash
   git push origin :refs/tags/v1.0.0     # delete the remote tag
   git tag -f v1.0.0 <commit>            # move the local tag
   git push origin v1.0.0                # repush
   ```
   Technically safe — no commit SHAs change — but it breaks the promise described above for anyone (or any cache, any CI runner) that already resolved `v1.0.0` to the old commit. Since this tag has existed publicly for a short window and nothing has plausibly consumed it as a *published artifact* yet (no image was ever built from it), the actual risk here is close to zero right now — but it's worth knowing this option gets progressively worse the longer a tag has been public, which is exactly why option 1 is the standing default professional practice, not just "the safe choice this one time."

3. **`workflow_dispatch` — a manual trigger, independent of tags entirely.**
   ```yaml
   on:
     push:
       tags: ["v*.*.*"]
     workflow_dispatch:      # adds a "Run workflow" button in the Actions UI
   ```
   Useful for testing a publish workflow without touching any tag at all, or for a genuinely one-off manual re-run. Doesn't solve "I want the artifact labeled 1.0.0" on its own — you'd still want to combine it with option 1 or 2 for the actual version label.

**Recommendation: option 1.** Build the Option 2 publish workflow above, verify it once against a throwaway tag if you want extra confidence, then cut `v1.0.1` (or whatever the next real, deliberate version is) as the tag that workflow actually runs against. Treat `v1.0.0` as a label that existed briefly before the publishing pipeline did — accurate, not embarrassing, and exactly the kind of thing a real "Versioning and release mechanics" checklist item (this repo already has language like that in `004-Release-1.0.md`) exists to catch before it becomes a bigger problem.

---

## Common mistakes worth recognizing (in this project or anyone else's)

- **Forgetting multi-arch on the first publish.** Already paid this cost once, for Tool_Box — the fix (`docker/setup-qemu-action` + an explicit `platforms:` key) is now something to write into *every* new publish workflow from the start, not rediscover per-repo.
- **Assuming GHCR packages are public because the repo is.** They're independent visibility settings — a workflow can succeed completely and still leave consumers with a 401.
- **Conflating "the code is on GitHub" with "there's a release."** A public repo with no tags, no Releases page, and no built artifacts is browsable, not released — fine as a stage, not the finish line.
- **Treating a version tag as mutable.** The moment you publish an artifact under a tag, that tag stops being "just a label you can casually move" — see Part 3.
- **Baking secrets into an image instead of injecting them at runtime.** The mistake this repo doesn't make (Part 1) — but a genuinely common one worth being able to spot in a code review, including your own future code in a different project.

## Interview relevance

Each part of this lecture maps directly onto a real interview question, now with a real, specific, verified answer instead of a general one:

- *"How do you handle secrets in a containerized application?"* → build-time/run-time separation, `.dockerignore` as a real control (not just a convention), and the verification habit (checking `git log --full-history`, not just trusting `.gitignore`) rather than reciting "we use environment variables."
- *"Walk me through your release/versioning process."* → a real, staged answer: source tag → curated release notes → multi-arch CI-published images → SemVer discipline about what a version number promises.
- *"Have you deployed something to a cloud provider?"* → an honest, sequenced answer that reads as judgment rather than a gap: not yet for *this* project, deliberately staged after the parts that needed to be provably stable first, with the reasoning (trial-credit timing, auth/rate-limiting not existing yet) ready to state out loud — which is a stronger answer than a rushed, under-secured deployment would have produced anyway.
