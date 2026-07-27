2026_06_30_08_17-LangChain_And_LangGraph_Complete_Lecture

# Lecture: LangChain & LangGraph, Complete — Every Component You're Using and Will Use

> A concepts lecture for Timothy Grant. Goal: teach the full LangChain and LangGraph toolkit your project relies on — the components, how they compose (LCEL), how messages/prompts/parsers/tools work, how RAG fits, and how LangGraph turns linear chains into stateful, controllable agents — so you can build the rest of LLM_Monitor with confidence.
> **Method (per `persona.md`):** macro → components → composition → control flow → *your* project mapping → edge cases, with embedded analogies and diagrams. This pairs with the database lecture (same day) and the earlier "Build the Full System" lecture; this one goes deep on the *framework itself*.

---

## 0. The big picture: what LangChain and LangGraph each are

- **LangChain** is a library of **composable building blocks** for LLM apps — chat models, prompt templates, output parsers, document loaders, splitters, embeddings, vector stores, retrievers, and tools — plus a way to **pipe them together** (LCEL). Think: the *parts bin* and a way to wire parts in a line.
- **LangGraph** is an orchestration layer that arranges those parts into a **stateful graph** that can branch, loop, remember, and pause. Think: the *control system* that runs the parts in a non-linear, stateful flow.

```
 LangChain  =  the components  (model, prompt, parser, retriever, tools, ...)
                     +  LCEL (a | b | c)   ← linear composition
 LangGraph  =  a state machine that wires those components into nodes/edges
                     with branching, loops, memory   ← non-linear orchestration
```

**Rule of thumb:** use a **LCEL chain** when the flow is a straight line (prompt → model → parse). Reach for **LangGraph** when you need branching ("if policy violated, stop"), loops (the tool-calling agent), or memory across turns — i.e., your `test_langchain_implementation` pipeline.

**Embedded analogy.** LangChain components are your peripherals and drivers; LCEL is wiring two pins together directly; LangGraph is the RTOS/state machine that schedules everything and holds shared state between stages.

---

## 1. The Runnable + LCEL: the glue under everything

### The Why
You need one consistent way to call any component — a model, a prompt, a parser, a whole chain — and to connect them. LangChain's answer is the **Runnable** interface and **LCEL** (LangChain Expression Language).

### The Theory
- Almost everything in LangChain is a **Runnable**: it has `.invoke(input)` (run once), `.stream(input)` (token-by-token), and `.batch([...])` (many at once).
- The **pipe operator `|`** composes Runnables left-to-right: the output of one becomes the input of the next. (Your comment got this exactly right — it's like Unix pipes.)
```python
chain = prompt | model | parser     # prompt's output → model's input → parser's input
chain.invoke({"topic": "cats"})     # runs the whole line
```
- Because the *whole chain* is itself a Runnable, you can compose chains of chains, and you get `stream`/`batch`/async for free everywhere.

### Edge cases / why it matters
- `invoke` returns the final output; `stream` yields partial tokens (for responsive UIs); `batch` parallelizes. Same chain, three execution modes.
- The input to a chain is whatever the **first** component expects (usually a dict of prompt variables). Mismatched input shape is the #1 LCEL error — connect this to the prompt-variable lesson (Module 3).

---

## 2. Messages: the vocabulary chat models speak

### The Why
Chat models don't take a raw string; they take a **list of messages**, each with a role. Understanding message types is prerequisite to prompts, tools, and memory.

### The Theory — the message roles
| Message | Role | Purpose |
|---------|------|---------|
| `SystemMessage` | system | instructions/persona ("You are a policy classifier") |
| `HumanMessage` | user | the user's input |
| `AIMessage` | assistant | the model's reply (may contain `tool_calls`) |
| `ToolMessage` | tool | the *result* of a tool call, fed back to the model |

A conversation is an ordered **list** of these. The model reads the whole list and produces the next `AIMessage`. Memory (Module 8) is literally "keep appending to this list and persist it."

### In your code
`ChatPromptTemplate.from_messages([("system", ...), ("user", ...)])` is a template that *produces* a message list when invoked. The `("system", "...")` tuples are shorthand for `SystemMessage`/`HumanMessage`.

---

## 3. Chat models, prompt templates, output parsers (the LCEL trio)

### 3a. Chat model
`ChatOllama(model="qwen2.5:1.5b", base_url=..., temperature=0)` — a Runnable that sends messages to the LLM and returns an `AIMessage`.
- **Crucial (from the prior lecture):** this object is a thin **client**; the weights live in Ollama. Holding it is cheap; build it once (singleton).
- `temperature` controls randomness: `0` = deterministic/factual (good for classifiers), higher = creative. Use low temp for your policy/injection checks, higher for friendly responses.
- Provider-swap is uniform: `ChatOpenAI`, `AzureChatOpenAI`, `ChatOllama` are interchangeable Runnables — your `Init()`-by-provider idea is idiomatic.

### 3b. Prompt template
`ChatPromptTemplate.from_messages([...])` with `{placeholders}` filled at invoke time. (Full treatment — placeholders vs Python vars vs the invoke dict, and the missing-variable trap — is in the 06-30 Python/Prompts lecture; reread that alongside this.) Key reminders:
- Use `.from_messages([...])`, not the bare constructor.
- Every `{name}` must be supplied in `.invoke({"name": ...})`.
- `MessagesPlaceholder("history")` is the slot where you inject prior conversation (Module 8).

### 3c. Output parser
A Runnable that turns the model's `AIMessage` into the shape you want.
- `StrOutputParser()` → extracts the plain text string (what `TestingMethod` uses).
- **Structured output** (Module 6) → a typed object, for classifiers/tools.

```
{vars} ──▶ PromptTemplate ──▶ messages ──▶ ChatModel ──▶ AIMessage ──▶ Parser ──▶ clean output
```

---

## 4. The RAG components (loaders → splitters → embeddings → vector store → retriever)

These are the five components your `lang_practice.py` comment listed as "to investigate." Together they implement RAG.

### 4a. Document Loader
Reads source content into LangChain `Document` objects (`.page_content` + `.metadata`). Loaders exist for text, PDF, web pages, directories, databases, etc. *This is the "loader I had no idea about"* — it's just "read my files into Document objects."
```python
from langchain_community.document_loaders import TextLoader
docs = TextLoader("policies.txt").load()      # -> List[Document]
```

### 4b. Text Splitter
LLMs and embedding models have input limits, and small chunks retrieve more precisely. A splitter cuts documents into overlapping chunks.
```python
from langchain_text_splitters import RecursiveCharacterTextSplitter
splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
chunks = splitter.split_documents(docs)
```
- **chunk_size** — characters/tokens per chunk; **chunk_overlap** — shared text between adjacent chunks so a concept split across a boundary isn't lost.
- `RecursiveCharacterTextSplitter` tries to split on natural boundaries (paragraphs, then sentences) — the sensible default.

### 4c. Embeddings
Turns text into a vector (the bridge to pgvector). `OllamaEmbeddings(model="nomic-embed-text")`. Two methods: `embed_documents([...])` (ingest), `embed_query(text)` (search). Same model must embed both sides. (Full treatment in the database + full-system lectures.)

### 4d. Vector Store
The component that stores chunk vectors and searches them — `PGVector` over your pgvector DB.
```python
store = PGVector(embeddings=embeddings, connection=PG_CONN, collection_name="policies")
store.add_documents(chunks)        # embed + INSERT (ingestion)
```

### 4e. Retriever
The query-time interface: "give me the top-k most relevant chunks for this text." A Runnable, so it drops into chains.
```python
retriever = store.as_retriever(search_kwargs={"k": 4})
docs = retriever.invoke(user_message)    # -> List[Document]  (format .page_content into the prompt!)
```

### The two RAG pipelines (assembled)
```
INGEST:  load ─▶ split ─▶ embed ─▶ store        (offline / on update, idempotent)
QUERY:   embed query ─▶ retrieve top-k ─▶ stuff into prompt ─▶ model ─▶ answer   (per request)
```
**The classic bug:** retrieval always returns *something*; gate on a similarity threshold so off-topic input isn't matched to a random chunk.

---

## 5. Tools and the agent loop

### The Why
A model only emits text. **Tools** let it take actions (call an API, query data, compute). The model decides *when* to use one; your code executes it and feeds the result back.

### 5a. Defining a tool
The `@tool` decorator turns a function into a Tool: **name** from the function, **arg schema** from type hints, **description from the docstring** (the model reads this to decide). Docstrings are not optional.
```python
from langchain_core.tools import tool

@tool
def find_weather(city: str) -> str:
    """Get the current weather for a given city."""   # the model reads this
    return "12°C, cloudy"
```

### 5b. Native tool calling (NOT string parsing)
Bind tools to the model; when it wants one, it returns a **structured `tool_calls`** object — name + validated args — not a string you parse.
```python
model_with_tools = model.bind_tools([find_weather, tell_time])
ai = model_with_tools.invoke(messages)
ai.tool_calls    # -> [{"name": "find_weather", "args": {"city": "Paris"}, "id": "..."}]
```
This is the correct replacement for the hand-rolled `res[0] != '{'` parsing. Map name→function with a **dispatch dict** `{"find_weather": find_weather}` and execute.

### 5c. The agent loop (ReAct)
```
reason ─▶ model emits tool_calls ─▶ execute tool ─▶ append ToolMessage ─▶ re-invoke
   └───────────────── repeat until the model returns a final answer (no tool_calls) ──┘
```
**Always bound the loop** (`max_steps`) — unbounded = cost/availability risk. Small local models have weak tool-calling; expect flakiness on `qwen2.5:1.5b`. LangGraph's `create_react_agent` runs this loop for you (Module 9).

---

## 6. Structured output — the reliability bridge

### The Why
Your guards/classifiers need a *machine-readable* answer, not prose. `if result == "Policy Violated"` is fragile (the model might phrase it 100 ways).

### The Theory
`model.with_structured_output(Schema)` forces the model to return data matching a schema (a Pydantic model), validated.
```python
from pydantic import BaseModel
class PolicyResult(BaseModel):
    violated: bool
    reason: str

classifier = model.with_structured_output(PolicyResult)
result = classifier.invoke(messages)     # result.violated is a real bool
if result.violated: ...                  # deterministic — no string matching
```
This is the bridge between the probabilistic model and your deterministic `if`s — use it for every policy/injection/routing decision. It's also what underlies tool calling (Module 5).

---

## 7. LangGraph — stateful, controllable orchestration

Now the framework that ties your whole pipeline together. Your `lang_graph_practice.py` had the right shape; here's the complete model.

### 7a. Why LangGraph over an LCEL chain
LCEL is linear — it can't branch, loop, or remember across calls. Your orchestrator must: branch (block on violation), loop (tools), and remember (conversation). LangGraph models this as a **graph of nodes with shared state** — a finite state machine (native to your embedded brain).

### 7b. State — the shared object flowing through the graph
You **define** the state schema (this is your missing `MyState`):
```python
from typing import TypedDict
class MyState(TypedDict):
    user_msg: str
    userId: str
    violated: bool
    chunks: str
    answer: str
```
Every node reads and writes this. (For lists that should *append* rather than overwrite — like a growing message history — you annotate the field with a **reducer**, e.g., `Annotated[list, add_messages]`, so updates accumulate instead of replace. This is how the agent message list grows.)

### 7c. Nodes — functions that return state updates
A node takes the state and returns a **dict of updates** (not a bare value — the bug you caught):
```python
def policy_check(state: MyState) -> dict:
    violated = classifier.invoke(state["user_msg"]).violated
    return {"violated": violated}       # merged into state["violated"]
```

### 7d. Edges — wiring, including branches and loops
```python
from langgraph.graph import StateGraph, START, END
g = StateGraph(MyState)
g.add_node("policy_check", policy_check)
g.add_node("retrieve", retrieve)
g.add_node("agent", agent)

g.add_edge(START, "policy_check")                       # entry point
g.add_conditional_edges("policy_check",                 # branch
    lambda s: "blocked" if s["violated"] else "ok",
    {"blocked": END, "ok": "retrieve"})
g.add_edge("retrieve", "agent")
g.add_edge("agent", END)
app = g.compile()
```
- **`START`/`END`** are the graph's entry/exit (you were missing the `START` edge).
- **Conditional edges** branch on a function of state — your guards route to `END`.
- **Loops** are just edges pointing back (the agent↔tools cycle).

### 7e. Running it
```python
result = app.invoke({"user_msg": msg, "userId": uid})   # call from your Flask handler, not at import
answer = result["answer"]
```
`app.stream(...)` streams node-by-node progress — perfect for telemetry (emit a span per node) and responsive UIs.

### 7f. Memory / checkpointing (multi-turn, persistent)
LangGraph can **checkpoint** state per conversation thread, giving you memory without hand-rolling it:
```python
from langgraph.checkpoint.postgres import PostgresSaver   # persists to YOUR Postgres
app = g.compile(checkpointer=PostgresSaver(...))
app.invoke({...}, config={"configurable": {"thread_id": userId}})  # resumes that user's state
```
This is the clean resolution of your statefulness `# NOTE`: state keyed by `thread_id`, persisted in the same Postgres you set up in the database lecture — stateless service, external state store.

### 7g. Prebuilt agents & human-in-the-loop
- `create_react_agent(model, tools)` — a ready-made tool-calling agent graph (skip hand-wiring the loop).
- LangGraph supports **interrupts** — pausing the graph for human approval before a risky tool runs (the human-in-the-loop control from your security lecture).
- **Subgraphs** — a whole graph can be a node in a bigger graph (compose your guard pipeline as a subgraph).

---

## 8. Memory & conversation history (where it all comes together)

The model is stateless per call — it only knows what's in the message list you send. "Memory" = persisting and replaying that list.
- **Within a request:** the agent loop appends `ToolMessage`s to a growing list (the reducer in 7b).
- **Across requests (multi-turn):** load the user's prior messages from Postgres (keyed by `userId`/`thread_id`), inject via `MessagesPlaceholder("history")`, append the new turn, persist. LangGraph's checkpointer automates this.
- **Context-window management:** don't replay 500 messages — window (last N) or summarize old turns. This is both a quality and a **cost** lever (fewer tokens).

---

## 9. Your project, mapped to the toolkit

| Pipeline step (`test_langchain_implementation`) | Components | Where it lives |
|------------------------------------------------|------------|----------------|
| Load conversation history | checkpointer / Postgres + `MessagesPlaceholder` | LangGraph state (7f) |
| Policy check | retriever + `with_structured_output` classifier | a LangGraph node returning `{violated}` |
| Prompt-injection check | same pattern + spotlighting | a node (early conditional edge) |
| Retrieve augmented data (RAG) | loader/splitter/embeddings/store/retriever | a node + ingestion at startup |
| Tool use | `@tool` + `bind_tools` / `create_react_agent` | an agent node with a bounded loop |
| Friendly response | prompt + model + `StrOutputParser` | the final node |
| Telemetry at each step | `app.stream` + your logging | spans per node (8 of the system) |

Build order (from the full-system lecture): one working LCEL chain → RAG node → tools node → assemble into LangGraph → add checkpointing/memory → guards → telemetry. Prove each before adding the next.

---

## 10. Future / advanced topics to grow into

- **LangSmith** — tracing + evaluation UI for LangChain/LangGraph (your eval and observability gaps; the easiest on-ramp before full OpenTelemetry).
- **Streaming & async** — `astream`/`ainvoke` for concurrency and responsive token streaming (ties to your async gap).
- **Structured RAG upgrades** — re-ranking, hybrid (keyword+vector) search, multi-query — the "production RAG" Microsoft asks about.
- **MCP integration** — expose/consume tools over the Model Context Protocol from a LangGraph tools node (covered in the full-system lecture).
- **Evaluation harness** — golden dataset + LLM-as-judge over graph trajectories, run in CI (the highest-differentiation thing you can build).

---

## 11. Mental sandbox & next steps

1. **Build the trio from memory.** `prompt | model | StrOutputParser()`, invoke with a variable. Then swap `StrOutputParser` for `with_structured_output(SomeModel)` and watch prose become a typed object.
2. **Wire one RAG query.** Load one text file → split → embed → store → retrieve → format `page_content` → put in a prompt. The whole of Module 4 in ~15 lines.
3. **Convert your tool loop to `bind_tools`.** Delete the string parsing; use `tool_calls` + a dispatch dict. Notice how much disappears.
4. **Make the graph run.** Define `MyState`, three nodes returning dicts, `START` edge, conditional edge, `compile`, `invoke` from `__main__`. Then add a `checkpointer` and pass a `thread_id` twice — watch it remember.
5. **Map your pipeline (Module 9) onto nodes** on paper before coding. The graph diagram *is* your orchestrator's design.

---

### Appendix — component → one-line job

| Component | One-line job |
|-----------|--------------|
| Runnable / LCEL `|` | uniform `invoke/stream/batch` + pipe composition |
| Messages | the role-tagged list a chat model reads |
| Chat Model | client that turns messages → `AIMessage` (weights live in Ollama) |
| Prompt Template | fills `{placeholders}` to produce messages |
| Output Parser | `AIMessage` → string or typed object |
| Document Loader | source files → `Document` objects |
| Text Splitter | big docs → overlapping chunks |
| Embeddings | text → vector |
| Vector Store (PGVector) | store + similarity-search vectors |
| Retriever | "top-k relevant chunks for this query" |
| Tool (`@tool`) | a function the model can call (docstring = its description) |
| `bind_tools` / structured output | get validated `tool_calls`/objects, not prose |
| LangGraph `StateGraph` | nodes + edges + shared state = controllable agent |
| State (`TypedDict`) | the object flowing through the graph |
| Checkpointer | persist per-thread state = memory |
| `create_react_agent` | prebuilt bounded tool-calling loop |

> **Closing note.** LangChain is a parts bin with one connector (`|`); LangGraph is the state machine that arranges those parts into something that can decide, loop, and remember. Everything you're attempting — RAG, tools, guards, the whole orchestrator — is a specific arrangement of the components in the appendix, wired by LCEL for straight lines and by LangGraph for everything stateful. Learn each part in isolation (Module 11's drills), then assemble in the build order. You already picked the right parts; this is how they click together.

*No source files were modified. Only this lecture was added to `Documentation/concepts_documentation/`.*
