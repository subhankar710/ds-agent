# Lesson Plan — Week 1, Step 3: Tool use (`run_sql`)

> **For agentic workers:** lesson-shaped plan. Each substep names a mode (**Tutor** = Claude codes + narrates; **Coach** = Subhankar codes, Claude reviews). Steps use checkbox (`- [ ]`) syntax.

- **Date:** 2026-05-01
- **Step in Week 1:** 3 of 7
- **Estimated time:** ~3 hours (~30 min Tutor for SDK + tool ABC + ~90 min Coach for SQL tool and agent loop + ~15 min Tutor for CLI wiring + reflection)
- **Prerequisites:** see [Section 0](#0-prerequisites)

> **Commit policy:** every "Suggested commit" block lists exact `git add` / `git commit` commands. **Subhankar runs these — Claude does not.**

---

## 0. Prerequisites

- [ ] Lesson 2 merged to `main`. Status log entry confirms it.
- [ ] `pytest -v` shows **13 passed**.
- [ ] `ds-agent db tables` works (proves the data layer is intact).
- [ ] Fresh feature branch:
  ```bash
  git switch main && git pull
  git switch -c feat/lesson-3-tool-use
  git push -u origin feat/lesson-3-tool-use
  ```

---

## 1. Concept — what this lesson teaches

This lesson is **the conceptual centerpiece of the entire project.** Everything before today made an LLM *talk*. Today the LLM gets to *act* — to ask our code to do things on its behalf and use the result.

### 1.1 What "tool use" actually is, mechanically

**Tool use** (also called "function calling" in some SDKs) is one extra parameter on the API call. We pass `tools=[...]` — a list of JSON-schema descriptions of functions Claude is allowed to call. Each tool has:

- a **name** (`"run_sql"`)
- a **description** (so Claude knows when to use it)
- an **input_schema** (JSON schema describing the arguments it takes)

Claude's response then has a **`stop_reason`** field. Two values matter today:

| `stop_reason` | What it means |
|---|---|
| `"end_turn"` | Claude finished — its `content` blocks contain the final answer (text). |
| `"tool_use"` | Claude wants to call a tool. Its `content` includes a `tool_use` block with the tool name, an id, and the input it wants to pass. |

When we see `"tool_use"`, our code:

1. Looks up the named tool in our registry.
2. Calls it with the input Claude provided.
3. Sends Claude a follow-up message with role `"user"` and a `tool_result` block (referencing the `tool_use_id`) carrying the function's return value as a string.
4. Receives the next response — which is usually `"end_turn"` (Claude composes the final answer from the tool result).

That's the whole protocol. Three messages total in the simplest case: user → assistant (tool_use) → user (tool_result) → assistant (final answer).

### 1.2 Why this is *the* foundational pattern of agentic AI

Every agent framework on the planet — LangChain agents, LlamaIndex agents, OpenAI Assistants, CrewAI, AutoGen, LangGraph, MCP servers — wraps this loop. They differ in ergonomics, planning strategies, and orchestration. They all reduce to: **LLM ↔ tool ↔ LLM ↔ tool ↔ ... ↔ final answer**.

By writing this loop by hand once, every framework you ever read will make sense.

### 1.3 The minimal "loop"

Today's loop is intentionally simple:

```
WHILE response.stop_reason == "tool_use":
    execute tool
    append tool_result to messages
    call LLM again
RETURN response.text
```

We add a max-iterations safety so a buggy tool can't trap the agent in an infinite loop. We do **not** add planning, retries, or multi-tool orchestration today. Lesson 4 hardens this.

### 1.4 Tool design — names, descriptions, and "schema as documentation"

The most underrated insight in agentic AI: **the tool description is the prompt.** Claude reads the `description` field to decide whether to call the tool and how. So `description="Execute SQL"` is a worse prompt than:

> *"Run a read-only SQL query against the Olist Brazilian e-commerce database. Use this when you need to compute aggregates, filter rows, or join across the 9 olist tables. Return rows are a JSON list of objects."*

Same code, different agent behavior. Tool description quality is one of the highest-leverage choices in agent design.

### 1.5 What's intentionally missing today

| Missing | Coming when |
|---|---|
| `get_relevant_schema` tool (Claude has to know what tables exist somehow) | **Lesson 4** — we'll dump all 9 schemas into the system prompt today as a stopgap |
| Tool error handling beyond "ValueError → Claude sees error string" | Lesson 5 (guardrails) |
| SQL safety check (block DELETE/DROP/etc.) | Lesson 5 |
| Tracing every LLM + tool call to SQLite | Lesson 6 |
| Evals that grade real answers | Lesson 7 |
| Multi-tool coordination, planning | Lesson 4 / Iter A |

The walking skeleton stays thin. Each later step deepens one layer.

---

## 2. Goal (the done definition)

By the end of Lesson 3:

1. `ds-agent ask "Which product category had the highest average review rating in Q3 2018?"` runs Claude with the `run_sql` tool, Claude writes SQL, our code executes it, Claude composes the answer. Real end-to-end agentic flow.
2. The output shows both **the SQL Claude wrote** (transparency) and **the final answer**.
3. `pytest -v` shows ~18 passed (13 from Lessons 1+2 + ~5 new for tools + agent).
4. The agent has a **max-iterations** safety. A buggy tool can't trap it.

**Quantitative done test:**

```bash
pytest -v                                                      # ~18 passed
ds-agent ask "How many orders are in olist_orders_dataset?"    # answer like "99,441 orders"
ds-agent ask "say hi without using any tool"                   # plain text answer, no tool call
```

---

## 3. File map

```
ds-agent/
├── src/ds_agent/
│   ├── llm.py                             # MODIFY — add chat() method for tool-aware calls
│   ├── tools/                             # NEW package
│   │   ├── __init__.py                    # NEW
│   │   ├── base.py                        # NEW — Tool ABC + ToolRegistry
│   │   └── sql.py                         # NEW — RunSqlTool
│   ├── agent.py                           # NEW — AgentLoop (the orchestrator)
│   ├── prompts.py                         # NEW — system prompt as a named constant
│   └── cli.py                             # MODIFY — `ask` uses the agent now
└── tests/
    ├── test_tools_sql.py                  # NEW
    ├── test_agent.py                      # NEW
    └── test_llm.py                        # MODIFY — add a chat() test
```

Files we will NOT touch: `config.py`, `db.py`, `test_config.py`, `test_db.py`, `conftest.py` (mostly — one new fixture).

---

## 4. Substep (a) — Extend `llm.py` with `chat()` [Tutor]

> **Why Tutor:** mechanical SDK extension. The substantive part is the agent loop in (d), not this glue.

### 4.1 The shape

We keep `complete()` as-is (Lesson 1 still uses it). We **add** a new method `chat()` for tool-aware calls:

```python
def chat(
    self,
    messages: list[dict],
    tools: list[dict] | None = None,
    system: str | None = None,
    max_tokens: int = 1024,
):
    """Lower-level: full message history + optional tools. Returns the SDK's Message object."""
```

Why a separate method instead of generalizing `complete()`:
- `complete()` returns `str`; `chat()` returns the full `Message` (so the caller can read `stop_reason`, iterate over `content` blocks). Different return shape ⇒ different method.
- Keeps Lesson 1's tests untouched. Pure addition.

### 4.2 What Claude writes

I'll make two edits to `llm.py`:
1. Add the `chat()` method after `complete()`.
2. (Optional) refactor `complete()` to call `chat()` internally — DRY but not required today.

I'll keep them separate today. DRY refactor is a later cleanup.

### 4.3 What Subhankar adds to `test_llm.py`

One new test, using the `monkeypatch.setattr(client, "_client", fake)` pattern you already know:

- `test_chat_returns_sdk_message_object_with_tool_use` — verifies that when the fake SDK returns a tool_use response, `client.chat(...)` returns it unchanged (we don't transform it; the agent loop reads `content` and `stop_reason` directly).

Specifically: build a fake response with `stop_reason="tool_use"` and a content list containing a tool_use-shaped MagicMock. Pass `tools=[{"name": "run_sql", ...}]`, assert the SDK was called with `tools=[...]` in kwargs and the return value is the fake response itself.

### 4.4 Suggested commit

```bash
git add src/ds_agent/llm.py tests/test_llm.py
git commit -m "feat(llm): chat() method for tool-aware calls"
git push
```

---

## 5. Substep (b) — `tools/base.py` Tool ABC + ToolRegistry [Tutor]

> **Why Tutor:** small interface contract; ~50 lines. Worth seeing the Pythonic ABC + dict-based registry pattern once.

### 5.1 The contract

```python
from abc import ABC, abstractmethod

class Tool(ABC):
    name: str
    description: str
    input_schema: dict

    @abstractmethod
    def run(self, **kwargs) -> str:
        """Execute the tool. Return a string (Claude needs to read it)."""
```

Three class attributes (set on subclasses) + one method.

A registry to look tools up by name:

```python
class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None: ...
    def get(self, name: str) -> Tool: ...           # raises KeyError if missing
    def schemas(self) -> list[dict]: ...            # for sending to the LLM
    def __contains__(self, name: str) -> bool: ...  # `if "run_sql" in registry:`
```

`schemas()` returns the list of `{"name", "description", "input_schema"}` dicts that the Anthropic API expects in the `tools=` parameter.

### 5.2 Tests Claude adds to `tests/test_tools_base.py`

Two:
- `test_registry_register_and_get` — register a fake tool, get it back by name.
- `test_registry_schemas_returns_anthropic_format` — register two tools, verify `schemas()` returns the right list-of-dicts shape.

### 5.3 Suggested commit

```bash
git add src/ds_agent/tools/__init__.py src/ds_agent/tools/base.py tests/test_tools_base.py
git commit -m "feat(tools): Tool ABC + ToolRegistry"
git push
```

---

## 6. Substep (c) — `tools/sql.py` RunSqlTool [Coach]

> **Why Coach:** concrete tool implementation. The choice of "what to return as a string" matters — it's what Claude reads.

### 6.1 The spec

A class `RunSqlTool` that subclasses `Tool` from substep (b). Constructor takes a `Database` instance (dependency injection — same pattern as `LLMClient`):

```python
class RunSqlTool(Tool):
    name = "run_sql"
    description = (
        "Run a read-only SQL query against the Olist Brazilian e-commerce database. "
        "Use this when you need to compute aggregates, filter rows, or join across the 9 olist tables. "
        "The result is a JSON-formatted list of rows. Limit your query to <= 100 rows; "
        "for aggregates that's fine, for raw scans add LIMIT 100."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "sql": {"type": "string", "description": "The SQL query to run."}
        },
        "required": ["sql"],
    }

    def __init__(self, db: Database) -> None: ...
    def run(self, sql: str) -> str: ...
```

**Behavior of `run`:**

1. Validate input — empty / whitespace-only sql → return `"ERROR: empty SQL query"` (a string, NOT raise; we want the LLM to see the error and self-correct).
2. Execute via `self._db.query(sql)`.
3. Truncate to first 100 rows defensively.
4. Serialize as JSON: `json.dumps(rows, default=str)` — the `default=str` handles datetime/Decimal types DuckDB returns.
5. On any DuckDB error: catch and return `f"ERROR: {e}"` as a string.

**Why return errors as strings instead of raising:** the LLM is the one reading them. If `run_sql` raises, the agent loop crashes. If it returns `"ERROR: ambiguous column 'order_id'"`, Claude sees the error and rewrites the SQL with a table prefix. **Self-correcting** behavior — one of the most powerful patterns in agentic systems.

### 6.2 The 4 tests for `tests/test_tools_sql.py`

Use the `in_memory_db` fixture from `conftest.py`. Build a fresh `RunSqlTool(in_memory_db)` per test.

1. **`test_run_sql_returns_json_string_of_rows`** — set up a small table, run `tool.run(sql="SELECT ...")`, assert the return is a string (parseable as JSON, with the expected rows).
2. **`test_run_sql_truncates_to_100_rows`** — insert 150 rows, query all, assert result has at most 100 entries.
3. **`test_run_sql_returns_error_string_on_bad_sql`** — `tool.run(sql="SELECT bogus FROM nope")` returns a string starting `"ERROR:"` (does NOT raise).
4. **`test_run_sql_returns_error_on_empty_input`** — `tool.run(sql="")` returns `"ERROR: empty SQL query"`.

### 6.3 Hints

- `json.dumps(rows, default=str)` — `default=str` is the trick that lets datetimes serialize.
- Truncation: `rows[:100]` after `query()` — simple slice. No LIMIT injection (cleaner; doesn't fight Claude's SQL).
- Wrap the DB call in try/except: `except Exception as e: return f"ERROR: {e}"`.

### 6.4 Order

1. Write `tests/test_tools_sql.py`.
2. Run `pytest tests/test_tools_sql.py -v` → 4 failures (module not found).
3. Write `src/ds_agent/tools/sql.py`.
4. Run `pytest -v` → 13 + 2 (base) + 4 (sql) = ~19 passed.

### 6.5 Suggested commit

```bash
git add src/ds_agent/tools/sql.py tests/test_tools_sql.py
git commit -m "feat(tools): RunSqlTool wrapping Database.query"
git push
```

---

## 7. Substep (d) — `agent.py` AgentLoop [Coach]

> **Why Coach:** the orchestrator — the heart of every agentic system. You should write it from scratch once.

### 7.1 The spec

A class `AgentLoop`:

```python
class AgentLoop:
    def __init__(
        self,
        llm: LLMClient,
        registry: ToolRegistry,
        system_prompt: str,
        max_iterations: int = 5,
    ) -> None: ...

    def run(self, user_question: str) -> AgentResult:
        """Execute the loop. Return both the final text and the trace of tool calls."""
```

`AgentResult` is a small dataclass:

```python
@dataclass
class AgentResult:
    answer: str
    tool_calls: list[ToolCall]   # for transparency in the CLI
    iterations: int
```

`ToolCall` is also a dataclass:

```python
@dataclass
class ToolCall:
    name: str
    input: dict
    output: str
```

### 7.2 Behavior of `run()`

```
messages = [{"role": "user", "content": user_question}]
tool_calls = []

for i in range(self.max_iterations):
    response = self.llm.chat(
        messages=messages,
        tools=self.registry.schemas(),
        system=self.system_prompt,
    )

    # append the assistant message (so Claude sees its own prior reasoning next turn)
    messages.append({"role": "assistant", "content": response.content})

    if response.stop_reason == "end_turn":
        # extract text from final response
        answer = "".join(b.text for b in response.content if b.type == "text")
        return AgentResult(answer=answer, tool_calls=tool_calls, iterations=i + 1)

    if response.stop_reason == "tool_use":
        # execute every tool_use block in the assistant content
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            tool = self.registry.get(block.name)
            output = tool.run(**block.input)
            tool_calls.append(ToolCall(name=block.name, input=block.input, output=output))
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": output,
            })
        # send all tool results back as one user message
        messages.append({"role": "user", "content": tool_results})
        continue

    # any other stop_reason — bail
    raise RuntimeError(f"unexpected stop_reason: {response.stop_reason}")

raise RuntimeError(f"max iterations ({self.max_iterations}) exceeded")
```

The structure: alternate `assistant` (Claude's response) and `user` (tool_result block list). Standard tool-use protocol.

### 7.3 The system prompt

Create a new module `src/ds_agent/prompts.py` with one constant:

```python
SQL_AGENT_SYSTEM_PROMPT = """You are a Data Science Agent. You answer business questions about the Olist Brazilian e-commerce dataset by running SQL queries.

Available tables (schema dumped here for Lesson 3 — Lesson 4 introduces a schema-retrieval tool):

<TABLE SCHEMAS HERE — see substep (e) for how this gets populated>

When the user asks a question:
1. Think briefly about which tables you need.
2. Call run_sql with a SQL query against the Olist tables.
3. If the query errors, read the error and fix the SQL.
4. Once you have the rows, compose a concise final answer that includes the key numbers AND mentions the SQL you ran.

Keep SQL read-only — SELECT, WITH, JOIN, GROUP BY, ORDER BY, LIMIT only. Do not write DDL or DML."""
```

We'll fill in `<TABLE SCHEMAS HERE>` at agent construction time by introspecting the DB.

### 7.4 The 3 tests for `tests/test_agent.py`

The trick for testing the agent loop: **mock the LLM client** so it returns *scripted responses*. We control what Claude "says" turn-by-turn. The pattern:

```python
def test_xyz(in_memory_db, monkeypatch):
    # Build scripted responses
    fake_text_block = MagicMock(type="text", text="The answer is 42.")
    fake_response_final = MagicMock(stop_reason="end_turn", content=[fake_text_block])
    # ...

    fake_llm = MagicMock(spec=LLMClient)
    fake_llm.chat.side_effect = [fake_response_tool_use, fake_response_final]
    # `side_effect=[...]` makes each call return the next item

    registry = ToolRegistry()
    registry.register(RunSqlTool(in_memory_db))

    loop = AgentLoop(llm=fake_llm, registry=registry, system_prompt="...")
    result = loop.run("How many orders?")

    assert "42" in result.answer
    assert fake_llm.chat.call_count == 2
```

The 3 tests:

1. **`test_agent_returns_text_directly_when_no_tool_used`** — script ONE response with `stop_reason="end_turn"` and a text block. Assert `result.answer` is the text and `result.tool_calls == []`.

2. **`test_agent_executes_tool_then_returns_answer`** — script TWO responses: first `stop_reason="tool_use"` with a tool_use block calling `run_sql`, second `stop_reason="end_turn"` with the final text. Assert tool ran exactly once, answer is the second response's text, `result.tool_calls` has one entry with the tool's actual output.

3. **`test_agent_raises_on_max_iterations_exceeded`** — script `max_iterations + 1` tool_use responses. Assert `RuntimeError` is raised.

### 7.5 Hints

- For mocking content blocks, use `MagicMock(type="text", text="...")` and `MagicMock(type="tool_use", id="toolu_x", name="run_sql", input={"sql": "..."})`. The agent loop reads `.type`, `.text`, `.id`, `.name`, `.input` — set those.
- For `MagicMock(spec=LLMClient)`: required so `fake_llm.chat(...)` is a recognized method.
- For `side_effect=[...]`: each call to the mock pops the next response from the list. After the list is exhausted, `StopIteration` is raised.
- The `messages.append({"role": "assistant", "content": response.content})` line passes the SDK's content list straight back. Claude SDK's `Message.content` is a list of typed objects, but the API accepts them back as-is.

### 7.6 Suggested commit

```bash
git add src/ds_agent/agent.py src/ds_agent/prompts.py tests/test_agent.py
git commit -m "feat(agent): minimal AgentLoop with tool-use protocol"
git push
```

---

## 8. Substep (e) — Wire CLI `ask` to use the agent [Tutor]

> **Why Tutor:** integration glue + system-prompt schema population.

### 8.1 What changes in `cli.py`

The existing `ask` command currently calls `LLMClient.complete()` directly. We replace that with an agent run:

```python
@app.command()
def ask(
    question: str = typer.Argument(..., help="Plain-English question for the agent."),
) -> None:
    """Ask the data agent. Routes through the agent loop with tools."""
    settings = get_settings()
    llm = LLMClient(settings)

    db = Database(settings.duckdb_path, read_only=True)
    registry = ToolRegistry()
    registry.register(RunSqlTool(db))

    system_prompt = build_system_prompt(db)        # we'll write this helper

    loop = AgentLoop(llm=llm, registry=registry, system_prompt=system_prompt)
    try:
        result = loop.run(question)
    except (LLMClientError, RuntimeError) as e:
        console.print(f"[red]Agent error:[/red] {e}")
        raise typer.Exit(code=1)
    finally:
        db.close()

    # transparency — show what tools were called
    for tc in result.tool_calls:
        console.print(f"[dim]→ {tc.name}({tc.input})[/dim]")
        console.print(f"[dim]  result preview: {tc.output[:200]}{'...' if len(tc.output) > 200 else ''}[/dim]")

    console.print(f"[bold green]Answer:[/bold green] {result.answer}")
    console.print(f"[dim](iterations: {result.iterations})[/dim]")
```

`build_system_prompt(db)` lives in `prompts.py` — it dumps every table's schema into the system prompt:

```python
def build_system_prompt(db: Database) -> str:
    lines = [SQL_AGENT_SYSTEM_PROMPT_HEAD]
    for table in db.list_tables():
        cols = db.describe_table(table)
        col_descs = ", ".join(f"{c['name']} {c['type']}" for c in cols)
        lines.append(f"- {table}({col_descs})")
    lines.append(SQL_AGENT_SYSTEM_PROMPT_TAIL)
    return "\n".join(lines)
```

(So `prompts.py` exports `SQL_AGENT_SYSTEM_PROMPT_HEAD`, `SQL_AGENT_SYSTEM_PROMPT_TAIL`, and `build_system_prompt`.)

### 8.2 Subhankar runs

```bash
ds-agent ask "How many orders are in olist_orders_dataset?"
ds-agent ask "Which product category has the highest average review rating in Q3 2018?"
ds-agent ask "say hi without using any tool"
```

### 8.3 Suggested commit + PR

```bash
git add src/ds_agent/cli.py src/ds_agent/prompts.py
git commit -m "feat(cli): ask now routes through the agent loop"
git push

gh pr create --title "Lesson 3: Tool use (run_sql)" \
             --body "Implements substeps (a)-(e) per docs/superpowers/plans/2026-05-01-week-1-step-3-tool-use.md.

Capabilities:
- LLMClient.chat() — tool-aware calls
- Tool ABC + ToolRegistry
- RunSqlTool wrapping Database.query
- AgentLoop with max-iterations safety
- ds-agent ask now runs the full agent loop end-to-end"
```

---

## 9. Final verification

```bash
pytest -v                                                               # ~18-19 passed
ds-agent ask "How many orders are in olist_orders_dataset?"             # numeric answer
ds-agent ask "List the top 3 product categories by total revenue"       # multi-row reasoning
ds-agent ask "say hi"                                                   # no tool used
ds-agent db tables                                                      # Lesson 2 still works
```

---

## 10. Reflection prompts

1. **The system-prompt schema dump is a stopgap.** Claude sees all 9 schemas every turn — that's a lot of tokens (~$0.005-0.01/call, mostly cached). Lesson 4 introduces `get_relevant_schema` to cut this. Why not just fix it now? (Hint: walking-skeleton principle.)
2. **Why do tool errors return strings instead of raising?** Imagine Claude wrote SQL that joined on a non-existent column. Two possible behaviors: (a) the agent crashes; (b) Claude sees the error message in a `tool_result`, rewrites the SQL, retries. Why is (b) the right default for production agents?
3. **`max_iterations=5`.** What's the failure mode if we set it to 1? To 100? What's a reasonable default for a SQL agent vs. for a multi-step research agent?
4. **The `chat()` method is lower-level than `complete()`.** Now that it exists, do we still need `complete()`? Why or why not?

---

## 11. Connects to Lesson 4

Lesson 4 hardens this loop and adds a second tool:

- **`get_relevant_schema(query)`** — instead of dumping all 9 schemas in the system prompt, the agent calls this tool early to learn what tables exist. The schema dump shrinks to "use the `get_relevant_schema` tool first." More tokens spent on tools, fewer on always-on context.
- **Better exit conditions** — handle `stop_reason="max_tokens"`, surface tool errors with proper `is_error: true` flag.
- **Tool registry as the configuration boundary** — adding tools becomes "register with the registry," nothing else changes.

The interface from Lesson 3 (`Tool`, `ToolRegistry`, `AgentLoop`) is what Lesson 4 *extends*, not rewrites.

---

## 12. Mode summary

| Substep | Mode | Why | Time |
|---|---|---|---|
| (a) `chat()` on LLMClient | Tutor | Mechanical SDK extension | 15 min |
| (b) Tool ABC + ToolRegistry | Tutor | Small interface contract | 15 min |
| (c) `RunSqlTool` + tests | **Coach** | Concrete tool, real design choices | 45 min |
| (d) `AgentLoop` + tests | **Coach** | The orchestrator, the substantive piece | 60-75 min |
| (e) Wire CLI ask | Tutor | Integration glue | 15 min |

Total: ~2.5-3 hours.

---

## 13. Status update

When Lesson 3 is merged, append to spec Status Log:

```
- 2026-MM-DD EOD — Lesson 3 complete and merged to main. Next: write Lesson 4 plan (multi-tool + get_relevant_schema + harden the loop).
```
