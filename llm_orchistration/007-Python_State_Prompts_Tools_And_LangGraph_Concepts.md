2026_06_30_07_40-Python_State_Prompts_Tools_And_LangGraph_Concepts

# Lecture: The Concepts Behind Your RAG / Tools / LangGraph Attempt — Models in Memory, Python State, Prompt Templates, Tool Calling & Graph State

> A concepts lecture for Timothy Grant, generated from your in-code comments and mistakes across `lang_practice.py`, `lang_graph_practice.py`, and `lang_tools.py` (June 30 iteration).
> **Method (per `persona.md`):** macro → components → control flow → theory → *your* code → edge cases, with embedded analogies and diagrams.
> You said implementing these AI components "revealed so many conceptual gaps." That's exactly what should happen — and your comments are the best map of them I've had yet. This lecture targets the **deep** ones (the ones that, once fixed, make many surface bugs obvious). The companion code review lists every concrete bug; this teaches the *why*.

---

## 0. The five concepts this lecture fixes

Ordered by how much each unblocks. Get #1 and #2 and half your confusion dissolves.

| # | The gap your code reveals | Module |
|---|---------------------------|--------|
| 1 | **You think `ChatOllama` loads the model weights into your Flask process's RAM** | M1 |
| 2 | **Python module state / `global` / `Init()` / the "is this like C# DI?" question** | M2 |
| 3 | **ChatPromptTemplate: `{placeholders}` vs Python variables vs the `invoke()` dict** | M3 |
| 4 | **Tools: `@tool`, native tool-calling vs your hand-rolled string parsing, string→function mapping** | M4 |
| 5 | **LangGraph: what `State` is, what a node returns, entry points, conditional edges** | M5 |

---

## 1. Module M1 — The biggest misconception: where the model actually lives

Your comment in `TestRagSystem`:
> *"the model is just weights loaded into RAM, I would be able to reuse this section in memory... What happens if we run out of memory, and then attempt to reuse that model as a variable? Does it just get reloaded into memory?"*

This question is built on a false premise, and clearing it up changes how you think about the whole service.

### The Why / the correction
`ChatOllama(model="llama3.2")` does **not** load llama3.2's weights into your Flask process. It creates a **thin HTTP client** — a small object holding a URL and some settings. The actual multi-gigabyte model weights live in a **completely different process on a different container**: the `ollama` service. When you call `chain.invoke(...)`, your Flask process sends an HTTP request to `http://ollama:11434`, Ollama runs the model, and sends back text.

```
  YOUR FLASK PROCESS                         OLLAMA CONTAINER
 ┌───────────────────┐    HTTP POST          ┌─────────────────────────┐
 │ ChatOllama object │ ───/api/chat────────▶ │  llama3.2 weights in RAM │
 │ (a few KB: a URL  │ ◀──── text response ──│  (multi-GB, loaded HERE) │
 │  + config)        │                       └─────────────────────────┘
 └───────────────────┘
```

### What this means for your worries
- **"Will I run out of memory holding the model?"** No — your Flask process holds a tiny client object, not weights. The memory pressure is in the *Ollama* container, and Ollama manages loading/unloading models itself (it lazy-loads on first use, may unload idle ones).
- **"Does the variable reload the model if memory is freed?"** The variable is just a client; it never held the model to begin with. Re-using it just sends another HTTP request.
- **Concurrency:** because the client is stateless and cheap, multiple requests can share one `ChatOllama` object safely — they each just fire HTTP calls. The *bottleneck* is Ollama processing them (and on your M1 Air, it largely serializes them).

### Embedded analogy
`ChatOllama` is like a **handle to a peripheral over a bus**, not the peripheral itself. Holding the handle costs nothing; the work happens in the device. You wouldn't worry that holding an I2C device address in a variable consumes the sensor's silicon — same here.

### The one nuance where memory *does* matter to you
`OpenAIEmbeddings`/`OllamaEmbeddings` are also just clients. But the **vector store** (PGVector) holds a DB connection, and the **documents you load** do sit in your process briefly during ingestion. So your process memory scales with *how much text you load at once*, not with model size. That's the real thing to manage (batch your ingestion), and it's small compared to model weights.

> **Takeaway:** In this architecture your Flask process orchestrates; it does not compute the LLM. Memory/CPU for inference lives in Ollama. This single correction dissolves most of your `Init`/memory anxiety.

---

## 2. Module M2 — Python module state, `global`, `Init()`, and your C# DI question

Your code and comments here are a perfect teaching case. You wrote:
```python
global lModel
global store

def Init():
    lModel = ChatOllama(...)      # <-- creates a LOCAL variable, discarded when Init returns
    store  = PGVector(...)
```
and asked:
> *"do I need to worry about the same kind of thing I do in C# where I register services with DI... so I can have the scoped object?"*

### The bug first (so the concept lands)
1. `global lModel` written at **module top level** does *nothing* — `global` only has meaning *inside a function*, to say "assign to the module-level name, not a new local."
2. Inside `Init()`, because there's **no `global lModel` line**, `lModel = ...` creates a **local** variable that vanishes when `Init()` returns. The module-level `lModel` stays undefined.
3. So later, `TestRagSystem` reads `lModel`/`store` → `NameError`.

### The Theory — how Python "singletons" actually work
- A **module is imported once** per process and cached. Anything you assign at module level (or via a correctly-written global) persists for the process's life. **That module-level object IS your singleton** — no DI container needed.
- To set it from inside a function, you must declare `global` *inside that function*:
  ```python
  lModel = None        # module level
  store  = None
  def Init():
      global lModel, store     # <-- THIS is what was missing
      lModel = ChatOllama(...)
      store  = PGVector(...)
  ```
- Cleaner still (and what senior Python does): avoid mutable globals; put shared objects in a small class or a module that builds them once, or use Flask's application context. But for your stage, the corrected `global` pattern is fine and instructive.

### Answering your C# DI question directly
Great instinct to connect this to DI. The mapping:

| C# / ASP.NET Core | Python / your Flask service |
|-------------------|------------------------------|
| `services.AddSingleton<T>()` | a module-level object created once in `Init()` |
| `services.AddScoped<T>()` (per request) | create the object *inside the request handler* |
| constructor injection | just `import` the module-level object, or pass it in |
| the DI container resolves lifetimes | *you* decide: module-level = singleton, in-handler = per-request |

**Which lifetime for what?**
- The **LLM client** and **embeddings client** are stateless and expensive-ish to set up → **singleton** (build in `Init()`, reuse). ✔ your instinct.
- The **vector store / DB connection** → singleton connection *pool* is standard (PGVector manages this).
- **Per-user conversation state** → per-request / per-conversation, loaded from the DB (your statefulness NOTE). Don't make this global.

### The concurrency caveat (the part DI normally hides from you)
Flask with `debug=True` and multiple workers can handle requests concurrently. A shared singleton client must be **thread-safe** to share. The LangChain HTTP clients generally are (they're stateless per call), but a shared mutable object (like a running conversation buffer) is **not** — that's exactly why per-user state must not be a global. This is the async/race-condition theme from your earlier lectures, now concrete.

> **Takeaway:** module-level object = singleton; declare `global` *inside* the function that sets it; choose singleton vs per-request by whether the object holds per-user state. That *is* "DI lifetimes," done by hand.

---

## 3. Module M3 — ChatPromptTemplate: three different ways "variables" enter a prompt

Your `TestRagSystem` prompt has three separate bugs that all come from one confusion: **what is a template placeholder vs. a Python variable vs. an `invoke()` argument?**

```python
createdPrompt = ChatPromptTemplate(                       # (a) should be .from_messages([...])
    ("system", "..."),
    ("system", "here is some extra information ... {chunks}")   # (b) {chunks} is a TEMPLATE placeholder
    ("user", userMessage)                                  # (c) userMessage is a PYTHON variable; also missing comma above
)
chain = createdPrompt | lModel | StrOutputParser()
response = chain.invoke({"message": userMessage})          # (d) supplies "message", but the template needs "chunks"
```

### The Theory — the three channels
1. **A literal Python variable** (`userMessage`): interpolated *when the template is constructed*. `("user", userMessage)` bakes the user's text in immediately. Fine, but then it's fixed.
2. **A template placeholder** (`{chunks}`): a *hole* in the prompt that stays empty until **invoke time**. The template *remembers* it needs `chunks`.
3. **The `invoke()` dict**: fills every placeholder. `chain.invoke({"chunks": ...})` must provide a key for **every** `{placeholder}` in the template — or you get a missing-variable error.

So your bug chain: the template declares `{chunks}` (channel 2) but `invoke` supplies `{"message": ...}` (wrong key) → `chunks` is never filled → error. And `userMessage` went in via channel 1, so it didn't need to be in invoke at all.

### The corrected mental model
```python
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are cheerful."),
    ("system", "Extra info from our docs:\n{chunks}"),   # placeholder
    ("user", "{user_message}"),                          # placeholder (better than baking it in)
])
chain = prompt | lModel | StrOutputParser()
response = chain.invoke({"chunks": chunks_text, "user_message": userMessage})  # supply ALL placeholders
```
**Rule:** every `{name}` in the template must appear as a key in the `invoke()` dict. Prefer placeholders over baking Python variables in — it keeps the template reusable and the data flow explicit.

### The hidden fourth bug — `chunks` is not a string
`retriever.invoke(userMessage)` returns a **list of `Document` objects**, not text. A `Document` has `.page_content` (the text) and `.metadata`. You can't drop a list of objects into a `{chunks}` string slot and expect sense. You must **format** them first:
```python
chunks_text = "\n\n".join(doc.page_content for doc in retriever.invoke(userMessage))
```
This `Document` type is a core LangChain object you'll meet everywhere in RAG — knowing it has `.page_content` + `.metadata` is half of debugging retrieval.

> **Takeaway:** placeholders are holes filled at invoke time; invoke must supply *every* hole by name; retriever output is `Document` objects you must join into text first.

---

## 4. Module M4 — Tools: the decorator, native tool-calling, and string→function mapping

Your `TestToolUseSystem` is the most honest code in the project — you flagged nearly every gap yourself, including connecting it to your DSA weakness. Let's resolve all of it.

### Gap A — `@tool` is misused, and your tools aren't tools yet
```python
@tool
tool_list = [FindWeather, TellTime]     # ❌ @tool decorates a FUNCTION, not a list; also 'tool' isn't imported
```
and in `lang_tools.py` the functions have **no docstrings and no decorator**.

**The Theory.** `@tool` (from `langchain_core.tools`) wraps a *function* into a `Tool` object. It derives the tool's **name** from the function name, its **argument schema** from the type hints, and — critically — its **description from the docstring**. The LLM reads that description to decide *whether and how* to call the tool. No docstring → the model is blind to what the tool does.
```python
from langchain_core.tools import tool

@tool
def find_weather(city: str) -> str:
    """Get the current weather for a given city."""   # <-- the LLM reads THIS
    return "12°C, cloudy"
```
So: decorate each function, give it a typed signature and a real docstring. `tool_list = [find_weather, tell_time]` is then a list of *Tool objects*.

### Gap B — you're hand-rolling what the framework does natively
Your loop asks the LLM to print a tool name as a string, then tries to parse the first character (`res[0] != '{'`), extract the name, and map it to a function. You wrote: *"I really think this is incorrect."* You're right — and the correct way is much simpler.

**The Theory — native tool calling.** Modern chat models support **structured tool calling**. You bind tools to the model; when the model decides to use one, it returns a **structured `tool_calls` object** (name + validated arguments), *not* a string you parse:
```python
model_with_tools = lModel.bind_tools(tool_list)
ai_msg = model_with_tools.invoke(messages)
ai_msg.tool_calls   # -> [{"name": "find_weather", "args": {"city": "Paris"}, "id": "..."}]
```
No `res[0] != '{'`, no character parsing. The framework guarantees the shape (this is the **structured output** concept from earlier lectures, applied to tools). You then execute the named tool with the given args and feed the result back as a `ToolMessage`, looping until the model returns a final answer with no more `tool_calls`.

> Note: small local models (qwen2.5:1.5b, llama3.2) have *limited* tool-calling ability. Don't be surprised if tool calling is flaky on tiny models — that's a model-capability limit, not your bug. LangGraph's `create_react_agent` can manage this loop for you.

### Gap C — mapping a string name to a function (and your DSA insight)
You wrote: *"I need to know how to map a string value to the variable... I really think this is incorrect... I have a problem with string manipulation for leetcode interviews."* Two things:
1. **The idiomatic answer is a dispatch dict** (a registry):
   ```python
   TOOLS = {"find_weather": find_weather, "tell_time": tell_time}
   result = TOOLS[call["name"]].invoke(call["args"])    # string -> function, O(1), no parsing
   ```
   This is the standard "map a string to behavior" pattern — a hash lookup, not string surgery. (Python also has `getattr(module, name)`, but a dict registry is safer and explicit.)
2. **Your self-diagnosis is correct and valuable.** The instinct to parse strings character-by-character *is* a sign the DSA/idioms muscle needs reps — and it's the same gap that shows up in interviews. The fix in code is the dispatch dict; the fix for interviews is the DSA cadence your skill-gap docs keep flagging. Good catch linking them.

### Gap D — `ChatPromptTemplate` is not a list; you can't `.append` to it
```python
createdPrompt.append(("tool", tool_result))   # ❌ a template isn't a Python list
```
In the native pattern you accumulate a **list of messages** (`messages.append(ToolMessage(...))`) and re-invoke the model on the growing message list — not on the template.

> **Takeaway:** decorate tools (docstrings = the model's instructions), use `bind_tools` to get structured `tool_calls` instead of parsing strings, and map name→function with a dispatch dict. Let LangGraph/`create_react_agent` run the loop.

---

## 5. Module M5 — LangGraph: State, nodes, edges, entry points

Your `lang_graph_practice.py` has the right *shape* but several missing concepts. You wrote: *"I have no idea where MyState comes from"* and *"I don't know how to invoke it, when to use it, how to hook everything up."* Let's build the model.

### Concept 1 — `State` is a schema you define (the thing flowing through the graph)
`StateGraph(MyState)` needs `MyState` because **the graph passes one shared state object from node to node**, and it needs to know its shape. You define it, usually as a `TypedDict`:
```python
from typing import TypedDict
class MyState(TypedDict):
    user_msg: str
    userId: str
    violated: bool
    chunks: str
    answer: str
```
This is the "context struct passed between stages" from the embedded analogy. Every node reads from it and writes to it.

### Concept 2 — a node returns a **dict of state updates**, not a bare value
Your `policy_check_fn` returns `True`, but your conditional edge reads `s["violated"]`. You even noticed the mismatch. The rule: **a node returns a partial dict that gets merged into the state.**
```python
def policy_check_fn(state: MyState) -> dict:
    violated = run_policy_classifier(state["user_msg"])   # your RAG+LLM check
    return {"violated": violated}        # <-- writes state["violated"]; NOT a bare bool
```
Now `lambda s: "END" if s["violated"] else "retrieve"` works, because `violated` is actually in the state. (This also means `retrieve_fn`/`agent_fn` must take `state` and return update dicts, not be empty `pass` stubs.)

### Concept 3 — a graph needs an entry point and connecting edges
Adding nodes isn't enough; you must say where execution *starts* and how nodes connect:
```python
from langgraph.graph import StateGraph, START, END
g = StateGraph(MyState)
g.add_node("policy_check", policy_check_fn)
g.add_node("retrieve", retrieve_fn)
g.add_node("agent", agent_fn)

g.add_edge(START, "policy_check")          # <-- entry point (was missing)
g.add_conditional_edges("policy_check",
    lambda s: "blocked" if s["violated"] else "ok",
    {"blocked": END, "ok": "retrieve"})
g.add_edge("retrieve", "agent")            # <-- connect the rest (was missing)
g.add_edge("agent", END)

app = g.compile()
```

### Concept 4 — don't invoke at import time
Your module runs `app.invoke({...})` at the top level, with `msg`/`uid` undefined. That executes (and crashes) the moment the file is imported. Wrap runnable code:
```python
if __name__ == "__main__":
    result = app.invoke({"user_msg": "hi", "userId": "u1"})
```
Real usage: your Flask `/api/chat` handler calls `app.invoke({"user_msg": chatMessage, "userId": userId})` per request, and reads `result["answer"]`.

### How it all hooks up (your "when/how do I use it" question)
```
Flask /api/chat  ──▶  graph.invoke({user_msg, userId})
                         │
                    START ─▶ policy_check ─(violated?)─▶ END (refusal)
                                   │ ok
                                   ▼
                              retrieve (RAG) ─▶ agent (tools loop) ─▶ END
                         │
                    result["answer"]  ──▶  Flask returns JSON to .NET
```
LangGraph *replaces* the manual while-loop you wrote in `TestToolUseSystem`: the graph is the controllable, inspectable version of "keep going until done," with state you can log (telemetry!) at every node.

> **Takeaway:** define `State` (a TypedDict), make every node take `state` and return an update dict, set a START edge and connect all nodes, and only `invoke` inside a handler or `__main__`. The graph is your orchestrator's backbone.

---

## 6. Cross-cutting: why the service won't even import right now

A meta-lesson worth internalizing: these files currently can't run, and that's *information*, not failure. The import chain `main.py → lang_practice.py` breaks immediately because of syntax/name errors (`@tool` on a list, `search_kwargs{...}` missing `=`, missing commas, undefined `OLLAMA_BASE_URL`/`PG_CONN`/`splitter`/`loader`, and `langchain_postgres` not installed). In Python, **one broken module breaks every module that imports it.** So the discipline from earlier reviews applies harder here: get *one* file to import and run, prove it, then add the next. The code review lists each blocker in order.

---

## 7. Mental sandbox & next steps

1. **Re-explain M1 in one sentence.** "When I call `chain.invoke`, the model weights are in ____, and my Flask process holds ____." If you can fill those blanks, the memory anxiety is gone for good.
2. **Fix the global pattern (M2).** Make `Init()` actually populate module-level `lModel`/`store` with `global`, then prove `TestRagSystem` can see them. Then ask: which of these should be per-request instead? (Answer: none yet — but conversation history will be.)
3. **Trace prompt variables (M3).** For your RAG prompt, list every `{placeholder}` and confirm your `invoke()` dict has a key for each. Format `chunks` from `Document.page_content`.
4. **Replace the parse loop with `bind_tools` (M4).** Write the dispatch dict `{name: fn}`. Notice you deleted all the string-parsing — that's the framework doing it correctly.
5. **Make the graph runnable (M5).** Define `MyState`, convert the three stub functions to `(state) -> dict`, add the `START` edge, and `invoke` it from `__main__` with a hardcoded message.

---

### Appendix — your comment → concept → status

| Your comment | Concept | Module | Status |
|--------------|---------|--------|--------|
| "model is weights in RAM... reloaded?" | clients vs. weights; Ollama holds the model | M1 | 🔴 → corrected |
| "make these global / put in a class / like C# DI scoped?" | module singletons, `global`, lifetimes | M2 | 🟡 right instinct, broken impl |
| "{chunks}... invoke({'message':...})" | template placeholders vs invoke keys; Document objects | M3 | 🔴 → corrected |
| "@tool... map string to function... leetcode weakness" | `@tool`, `bind_tools`, dispatch dict, DSA link | M4 | 🟡 excellent self-diagnosis |
| "no idea where MyState comes from / how to hook up" | State TypedDict, node returns dict, edges, entry | M5 | 🔴 → corrected |
| "no idea what loader is / how data gets into the DB" | RAG ingestion (covered in prior full-system lecture) | — | see 06_29 lecture §3 |

> **Closing note.** The volume of gaps this surfaced isn't a setback — it's the predictable result of reaching for five advanced concepts (RAG, embeddings, vector DB, tools, graph orchestration) at once. Every one of your confused comments was pointing at a *real, nameable* concept, and you even diagnosed your own DSA gap unprompted. That is exactly how strong engineers learn. Fix M1 and M2 first (they unblock the most), make one file import and run, and build up one node at a time.

*No source files were modified. Only this lecture was added to `Documentation/concepts_documentation/`.*
