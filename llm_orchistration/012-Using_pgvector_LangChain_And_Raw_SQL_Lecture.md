2026_07_03_21_22-Using_pgvector_LangChain_And_Raw_SQL_Lecture

# Lecture: Working With pgvector — What Actually Happens to the Rows, via LangChain and via Raw SQL

> A concepts lecture for Timothy Grant, generated from your `app/rag/Ingestion.py` (and its comments) plus the `pgvector-service` in `docker-compose.yaml`.
> **Method (per `persona.md`):** high-level → components → interactions → control flow → implementation → edge cases → performance. Uses **personified analogies** (named characters with roles and motivations), per your stated preference. Includes the sections you like: what problem is solved, why this design, common mistakes, interview relevance, production usage.
> **Your core question, answered here:** *"How do my Python operations impact the rows and columns of the pgvector table?"* — plus how to do it through LangChain **and** by talking to Postgres directly. By the end you should be able to open `psql`, see the exact rows LangChain created, and reproduce every operation by hand.

---

## 0. The cast of characters (meet the team)

Before any mechanics, let's give faces to the players. Every concept below is one of these characters doing their job.

- **Postgractica, the Librarian** 📚 — the Postgres/pgvector server *process*. She is the *only one* allowed to touch the shelves. She speaks exactly one language — **SQL** — and does nothing unless someone asks her in it. She lives inside the `pgvector_service` container. Her archive (the actual books) is kept in a locked storeroom called the **`pgdata` volume**, so even if her office burns down (the container is removed), the books survive.
- **Nomic, the Translator** 🌐 — the embedding model (`nomic-embed-text`), who lives in a *different building* (the Ollama container). Nomic's only skill: take a passage of human text and hand back a **coordinate card** — a list of 768 numbers that pinpoints that text's *meaning* in a vast space. Nomic does this identically every time, for documents and for questions alike.
- **PGVector, the Concierge** 🎩 — the LangChain wrapper class. A smooth middle-man who stands between *you* and Postgractica. You hand him documents; he quietly walks them over to Nomic for translation, fills out all the SQL paperwork, and files them with Postgractica — so you never have to speak SQL. Convenient, but he hides what's really happening on the shelves.
- **Psql & Psycopg, the Direct Line** ☎️ — the ways *you* can talk to Postgractica yourself, in her own SQL language, cutting out the Concierge entirely. `psql` is a phone in her lobby (a CLI); `psycopg` is a phone line from your Python code.
- **The Collection** 🗂️ — a named *section* of the archive (e.g., `"company_policies"`). One row in a small directory table.
- **The Index Cards** 🃏 — the individual stored rows: each holds a coordinate card (the vector), the original text, and a sticky-note of metadata.

Keep this cast in mind; the rest of the lecture is just watching them work.

---

## 1. What problem does pgvector solve, and what *is* it? (macro)

**The problem.** Postgractica, like any classic Librarian, is brilliant at *exact* lookups: "find the book with ISBN 12345." But she's helpless at *meaning*: "find books *similar in idea* to this sentence." Human language has no ISBN for meaning — "dog," "puppy," and "canine" share no letters but share sense.

**The solution.** `pgvector` is an *extension* — a skill-upgrade — that teaches Postgractica two new tricks:
1. A new kind of thing she can store in a column: a **`vector`** (Nomic's coordinate cards).
2. A new way to *compare* those columns: **distance operators** that measure how close two coordinate cards are, i.e. how similar two meanings are.

Crucially: **pgvector *is* Postgres.** It's not a separate database — it's Postgractica with an extra skill. So *everything you know about ordinary databases still applies*: tables, rows, columns, `INSERT`/`SELECT`, transactions, indexes. A "vector database," in your case, is just "a normal table that happens to have a `vector` column and a distance operator." That reframing is the whole game — hold onto it.

**Why this design (vs. a dedicated vector DB like Pinecone/Qdrant):** keeping vectors *inside* Postgres means your policy vectors and your ordinary relational data (telemetry, chat history) live with one Librarian — one connection, one transaction, one backup, and you can `JOIN` a flagged message to the exact policy it matched. At your scale that simplicity wins.

---

## 2. The physical reality — what tables, rows, and columns actually exist

This is the part you said you couldn't see. Let's make it concrete. When the Concierge (`PGVector`) first sets up shop for a collection, he asks Postgractica to create **two tables**. (Exact names/columns vary slightly by `langchain-postgres` version — always confirm with `\d` — but the shape is always this.)

### Table 1 — the collection directory: `langchain_pg_collection`
A tiny table; one row per *named section*.

| column | meaning | example |
|--------|---------|---------|
| `uuid` | the section's internal ID | `a1b2...` |
| `name` | the human name you chose | `company_policies` |
| `cmetadata` | optional notes about the section | `{}` |

Your `collection_name="company_policies"` becomes **one row here.**

### Table 2 — the index cards: `langchain_pg_embedding`
The important one. **One row per chunk of text you store.** This is what `add_documents` actually writes.

| column | meaning | in your data |
|--------|---------|--------------|
| `id` / `custom_id` | the card's unique ID (often a UUID) | auto-generated |
| `collection_id` | which section it belongs to (FK → table 1) | the `company_policies` uuid |
| `embedding` | **Nomic's coordinate card** — `vector(768)` | `[0.021, -0.44, ...]` |
| `document` | the **original text** (`page_content`) | `"Employees are permitted to use local scripting tools..."` |
| `cmetadata` | the **metadata** as JSONB | `{"source": "security_policy_v2.md", "category": "it_safety"}` |

So when you wrote this in `Ingestion.py`:
```python
Document(page_content="Employees are permitted...", metadata={"source": "...", "category": "it_safety"})
```
…each field has a destination column:
```
 page_content ─────────────▶ document   (the text, stored verbatim)
 (via Nomic) ───────────────▶ embedding  (the 768-number vector of that text)
 metadata ──────────────────▶ cmetadata (as JSONB)
 (auto) ────────────────────▶ id, collection_id
```

**Picture the whole thing:**
```
 langchain_pg_collection                 langchain_pg_embedding
 ┌──────┬───────────────────┐            ┌──────┬──────────────┬───────────┬───────────────┬────────────────┐
 │ uuid │ name              │◀───────────│ id   │ collection_id│ embedding │ document      │ cmetadata      │
 ├──────┼───────────────────┤   FK       ├──────┼──────────────┼───────────┼───────────────┼────────────────┤
 │ a1b2 │ company_policies  │            │ 7f.. │ a1b2         │[0.02,...] │ "Employees..."│ {"source":...} │
 └──────┴───────────────────┘            │ 9c.. │ a1b2         │[-0.4,...] │ "Building..." │ {"source":...} │
                                         └──────┴──────────────┴───────────┴───────────────┴────────────────┘
```
**That's the answer to "where does my data go."** Two rows in `langchain_pg_embedding` (you have two `Document`s), each pointing back to the single `company_policies` row.

---

## 3. How each Python (LangChain) operation maps to rows & columns (control flow)

Now watch the Concierge work, step by step, tracing your actual code.

### 3a. Construction — `PGVector(...)`
```python
vector_store = PGVector(embeddings=embeddings, connection=connection_string, collection_name="company_policies")
```
What happens: the Concierge opens a phone line to Postgractica (using your `connection_string`), and — on first use — asks her to **create the two tables if they don't exist** and to insert the `company_policies` row into the directory. *No document rows yet.* He's just set up the filing system.

> ⚠️ **Grounded correction (from your code):** you wrote `ElephantVectorStore(embedding=..., connection_string=...)`. There is no `ElephantVectorStore` — the real class is **`PGVector`** (from `langchain_postgres`). Also `from langchain_core import Document` should be `from langchain_core.documents import Document`. These are import/name mistakes, not concept mistakes — but they'll stop the module from importing. (Full list in the code-review folder; noting here so the mental model is correct.)

### 3b. Ingestion — `add_documents(raw_docs)` (this is an **INSERT**, not UPDATE)
```python
vector_store.add_documents(raw_docs)   # your two policy Documents
```
For **each** document, the Concierge performs a three-step dance:
```
 1. TRANSLATE:  hand page_content to Nomic  →  get back a vector(768)
 2. PACKAGE:    bundle {id, collection_id, embedding, document, cmetadata}
 3. FILE:       ask Postgractica to run  INSERT INTO langchain_pg_embedding (...) VALUES (...)
```
After this call, `langchain_pg_embedding` has **two new rows**. That is the literal impact of `add_documents` on the table: N documents in → N rows inserted (each with its vector computed by Nomic).

> ⚠️ **Correcting your comment:** you wrote *"then do an UPDATE (I think)."* Adding *new* documents is an **INSERT** (create new rows), not an `UPDATE` (which *modifies existing* rows). `UPDATE` would be for changing a policy you already stored. Re-adding the same docs naively **inserts duplicates** — which is why your idempotency instinct matters (Module 7).

### 3c. Retrieval — `similarity_search(query, k)`
```python
results = vector_store.similarity_search(incomingMessage, k=2)
```
The Concierge again works in steps:
```
 1. TRANSLATE the QUESTION:  hand incomingMessage to Nomic  →  query vector(768)
 2. ASK Postgractica:        SELECT document, cmetadata
                             FROM langchain_pg_embedding
                             WHERE collection_id = <company_policies>
                             ORDER BY embedding <=> <query_vector>   -- closest meaning first
                             LIMIT 2;
 3. REBUILD:                 wrap each returned row back into a Document (page_content + metadata)
```
So retrieval **reads** rows (a `SELECT`), never writes. The magic is the `ORDER BY embedding <=> query_vector` — "sort the shelf by how close each card's meaning is to the question." `k=2` is the `LIMIT`. The result is a Python `List[Document]` (each with `.page_content` and `.metadata`) — remember to pull `.page_content` when you stuff them into a prompt.

**The whole round trip, personified:**
```
 You ──question──▶ Concierge ──"translate this"──▶ Nomic ──vector──▶ Concierge
                                                                        │ "find the 2 closest cards"
                                                                        ▼
                                                                   Postgractica (SELECT ... ORDER BY <=> LIMIT 2)
                                                                        │ rows
                                                                        ▼
 You ◀──List[Document]──  Concierge (rebuilds Documents)
```

---

## 4. Doing it *directly* — talking to Postgractica without the Concierge

You asked: *"how would I do this outside the LC ecosystem… talk with pgvector itself and do the commands to get the data?"* Excellent instinct — knowing the layer beneath the abstraction is what separates users from engineers. There are two direct lines.

### 4a. `psql` — the phone in the lobby (CLI, great for inspecting)
Exec into the container and talk to Postgractica yourself:
```bash
docker exec -it pgvector_service psql -U admin -d <your_db>
```
Now you're at a SQL prompt. Useful first commands:
```sql
\dt                                  -- list tables (you'll SEE langchain_pg_collection/embedding)
\d langchain_pg_embedding            -- show that table's columns & types (confirm the schema!)
SELECT name FROM langchain_pg_collection;                 -- your sections
SELECT id, left(document, 40), cmetadata                  -- peek at the actual rows LangChain wrote
FROM langchain_pg_embedding LIMIT 5;
```
This is the single most demystifying thing you can do: **look at the rows the Concierge created.** Suddenly `add_documents` isn't magic — it's just `INSERT`s you can see.

### 4b. Building a vector table from scratch, by hand (no LangChain at all)
This proves you understand every layer. In `psql`:
```sql
-- 1. Give Postgractica the pgvector skill (once per database; idempotent)
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Design your own table with a vector column
CREATE TABLE my_policies (
    id        bigserial PRIMARY KEY,
    content   text,
    embedding vector(768)          -- dimension MUST match Nomic's output
);

-- 3. Insert a row. (Normally you'd get the vector from Nomic; here a tiny fake for illustration)
INSERT INTO my_policies (content, embedding)
VALUES ('No sharing of secrets', '[0.01, 0.02, 0.03, ... 768 numbers ...]');

-- 4. Similarity search: find the 2 rows whose meaning is closest to a query vector
SELECT content, embedding <=> '[...query vector...]' AS distance
FROM my_policies
ORDER BY embedding <=> '[...query vector...]'
LIMIT 2;
```
That `<=>` is cosine distance (Module 5). This *is* what the Concierge does under the hood — you've just removed him from the room.

### 4c. `psycopg` — the direct line from Python (no Concierge)
Same idea, from code. This is how you'd run raw SQL in your own service when the LangChain abstraction is too limiting:
```python
import psycopg
# Nomic still does the embedding — you just skip PGVector for the SQL part
qvec = embeddings.embed_query("can I run local scripts?")     # -> list[float] length 768

with psycopg.connect(connection_string) as conn:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT content FROM my_policies ORDER BY embedding <=> %s::vector LIMIT %s",
            (qvec, 2),                                        # PARAMETERS — never string-concat!
        )
        rows = cur.fetchall()
```
Notice: **Nomic (embeddings) is still needed** even without LangChain — the embedding model and the database are *different characters*. LangChain only automated the plumbing *between* them; it never replaced either. Also note the **parameterized query** (`%s`, values passed separately) — the SQL-injection defense from the database lecture; the driver, not you, safely inserts the values.

### The trade-off (when to use which line)
| | Concierge (LangChain `PGVector`) | Direct line (`psql`/`psycopg`) |
|---|---|---|
| Effort | low — one method call | higher — you write SQL |
| Control | limited to what the wrapper exposes | total |
| Visibility | hides the rows | you see everything |
| Best for | standard RAG add/search | custom queries, debugging, joins, migrations, learning |
Professionals use **both**: the Concierge for routine RAG, the direct line to inspect, debug, and do anything bespoke.

---

## 5. How similarity is actually computed — distance operators & indexes (performance)

### The operators (how "closeness" is measured)
pgvector gives Postgractica three ways to compare coordinate cards:

| operator | meaning | when |
|----------|---------|------|
| `<=>` | **cosine distance** (angle between vectors) | the usual choice for text embeddings |
| `<->` | Euclidean (straight-line) distance | some models |
| `<#>` | negative inner product | some models |

Lower = closer = more similar. `similarity_search` uses one of these under the hood (cosine by default for most setups).

### Indexes (why it stays fast)
By default, a `SELECT ... ORDER BY embedding <=> q` makes Postgractica measure the distance to **every single card** — fine for your 2 rows, painful for 2 million. An **ANN index** (`HNSW` or `IVFFlat`) is a pre-built map that lets her jump to the likely-closest neighborhood without checking everything (roughly `O(log n)` instead of `O(n)`):
```sql
CREATE INDEX ON my_policies USING hnsw (embedding vector_cosine_ops);
```
You don't need one yet (tiny data), but know it exists — "how do you make vector search scale?" is a real interview question, and "ANN indexes like HNSW, trading a little recall for big speed" is the answer.

---

## 6. Blocking bad retrievals — the similarity threshold (your explicit question)

You wrote: *"we need to block erroneous retrievals, so I think we would need to set a minimum matching closeness."* Exactly right, and here's why it matters: **`similarity_search` always returns `k` rows, even for a totally unrelated question.** Ask your policy archive "what's your favorite color?" and it will still hand back the 2 "closest" policies — which are meaningless noise. If you then feed those to a classifier, you've polluted it.

The fix: use the **scored** variant and apply a cutoff.
```python
# returns (Document, distance) pairs; keep only those close enough
results = vector_store.similarity_search_with_score(incomingMessage, k=4)
good = [doc for doc, distance in results if distance < THRESHOLD]   # tune THRESHOLD empirically
```
(With raw SQL, you'd add a `WHERE embedding <=> q < THRESHOLD`.) The threshold is empirical — you tune it by looking at real distances. This is the single most common RAG-quality bug, and you spotted it yourself — good instinct.

---

## 7. INSERT vs UPDATE vs UPSERT, and idempotent ingestion

Tying your `RunIdempotentRagIngestion` name to the DML vocabulary (from the database lecture):
- **INSERT** — add new rows (what `add_documents` does).
- **UPDATE** — modify existing rows (a policy's text changed).
- **UPSERT** — "insert if new, update if it already exists" (`INSERT ... ON CONFLICT DO UPDATE`).

Your function is named *idempotent* — meaning running it twice shouldn't create duplicates — but as written, calling it twice will **INSERT the two policies again**, giving you 4 rows. To make it truly idempotent you need one of:
- give each document a **stable `id`** (e.g., derived from its source) and **upsert** on that id, so a re-run overwrites rather than duplicates; or
- **check first**: query whether the collection already has rows and skip if so; or
- clear-and-reload the collection on each ingest.
`add_documents(ids=[...])` (passing stable ids) is the cleanest — LangChain will upsert on those ids. This is the concrete mechanism behind the "idempotent" in your function name.

---

## 8. Common mistakes (several drawn straight from your code)

| Mistake | Why it's wrong | Fix |
|---------|----------------|-----|
| `ElephantVectorStore` | not a real class | use `PGVector` (from `langchain_postgres`) |
| `from langchain_core import Document` | wrong module | `from langchain_core.documents import Document` |
| "do an UPDATE" for new docs | UPDATE modifies existing rows | `INSERT` / `add_documents` (upsert for idempotency) |
| no similarity threshold | search always returns k, even for junk | `similarity_search_with_score` + cutoff |
| assuming re-running ingestion is safe | re-INSERTs → duplicate rows | stable ids + upsert, or check-first |
| dimension mismatch | `vector(N)` must equal Nomic's output size | match `N` to the embedding model; re-embed if you switch models |
| compose env `POSTGRES_PASSWORD={...}` (missing `$`) | it's a literal string, not the variable | `${POSTGRES_PASSWORD:-...}` — note your compose has this typo on password/db |
| thinking LangChain replaces the embedder | it doesn't — Nomic still translates | embeddings model is a separate character even in raw SQL |

*(The compose `$` typos and the import errors are in the code-review folder too; included here so your mental model is accurate.)*

---

## 9. Interview relevance & production usage

**Interview.** Expect: "How does semantic search work?" (embeddings + a distance operator over a vector column), "How do you scale it?" (ANN indexes — HNSW/IVFFlat — recall/latency trade-off), "How do you keep RAG from returning garbage?" (similarity threshold + chunking + re-ranking), and "vector DB vs. pgvector?" (one engine, joins with relational data, operational simplicity vs. a specialized store's scale/features). Being able to *draw the two tables and the SELECT* — as in Module 2–3 — puts you ahead of people who only know the wrapper.

**Production.** Real systems add: metadata **filtering** (a `WHERE cmetadata->>'category' = 'it_safety'` before the distance sort — multi-tenancy/permissions), **hybrid search** (keyword + vector), **re-ranking** the top-k, batched/idempotent ingestion driven by a queue, and **connection pooling** (your `psycopg[binary,pool]` dependency is exactly for this). And critically — the same secrets/parameterized-query hygiene as any database.

---

## 10. Mental sandbox & next steps

1. **See the rows.** Bring up the stack, `docker exec -it pgvector_service psql -U admin -d <db>`, then `\dt`, `\d langchain_pg_embedding`, and `SELECT left(document,40), cmetadata FROM langchain_pg_embedding;`. Watch your two policies sitting there as real rows. This alone will make the whole lecture click.
2. **Insert by hand.** In `psql`, `CREATE EXTENSION vector`, make a tiny table with a `vector(3)` column, insert two rows with 3-number vectors, and run an `ORDER BY embedding <=> '[...]' LIMIT 1`. Watch distance ordering work on numbers you can eyeball.
3. **Reproduce a search two ways.** Run `similarity_search` via LangChain, then run the equivalent `SELECT ... ORDER BY embedding <=> %s LIMIT k` via `psycopg`, and confirm you get the same rows. Now the Concierge holds no mysteries.
4. **Add the threshold.** Switch to `similarity_search_with_score`, print the scores for a *relevant* and an *irrelevant* question, and pick a cutoff that separates them.
5. **Make ingestion truly idempotent.** Give each policy a stable `id` and confirm running ingestion twice keeps the row count at 2, not 4.

---

### Appendix — your comment → concept → where answered

| Your comment in `Ingestion.py` | Concept | Section |
|--------------------------------|---------|---------|
| "investigate what this is doing / how this works" | PGVector construction → creates 2 tables | §2, §3a |
| "do an UPDATE (I think)" | add_documents = INSERT; idempotency = upsert | §3b, §7 |
| "block erroneous retrievals / minimum closeness" | similarity threshold (`_with_score`) | §6 |
| "how outside the LC ecosystem / talk to pgvector directly" | psql + raw SQL + psycopg | §4 |
| "haven't thought how to map variables to documents" | ingestion source strategy (later) | §7 note |

> **Closing note.** The Concierge (LangChain) is convenient, but you asked the exact question that makes an engineer: *what is he actually doing to the shelves?* The answer is unglamorous and empowering — he runs `INSERT`s and `SELECT ... ORDER BY <=>` against two ordinary tables, using Nomic to turn text into the numbers in the `embedding` column. Once you've seen those rows in `psql` with your own eyes and reproduced a search by hand, pgvector stops being a black box and becomes just Postgractica with one extra skill. Go run step 1 — it's the fastest path from "magic" to "mine."

*No source files were modified. Only this lecture was added to `Documentation/concepts_documentation/`.*
