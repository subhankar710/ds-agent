# Data Science Agent — Design Spec

- **Date:** 2026-04-30
- **Author:** Subhankar Patra
- **Status:** Draft — pending implementation plan
- **Working directory:** `/Users/subhankarpatra/Documents/ds-agent/`

This spec is the output of a brainstorming session and the input to a forthcoming implementation plan. It captures decisions, the chosen learning shape, and the production-grade concerns the project must address even as a learning project.

---

## 1. Problem Statement

### 1.1 Persona

A **non-technical product / operations analyst** at an e-commerce company. They have business questions about orders, customers, products, and reviews, but they do not write SQL fluently. Today, when they want a number, they ping the data team on Slack, wait hours-to-days, and often discover the answer raised three more questions.

Subhankar (data scientist) is also a stand-in user — the agent must produce output Subhankar can sanity-check from a DS perspective.

### 1.2 The pain (one sentence)

> *"I need answers from our data, but I am bottlenecked by the data team's queue, and most of my questions are simple enough that they should not need a human."*

### 1.3 Success criteria (observable)

1. The analyst can type a plain-English question and get a correct, evidence-backed answer in under ~30 seconds.
2. The agent shows the SQL it ran, so the analyst (and a reviewing data scientist) can sanity-check that the answer means what it claims.
3. For open-ended exploration, the analyst can say *"find me 3 surprising patterns in this dataset"* and get a structured report with evidence, not just vibes.
4. The agent refuses or escalates when uncertain — no confidently-wrong answers.

### 1.4 Two modes the agent supports

- **Mode 1 — Q&A** (point question → point answer; the "B" usecase from brainstorming).
- **Mode 2 — Auto-EDA** (open-ended exploration → multi-step plan → markdown report; the "D" usecase). Deferred to **Iteration A**; not in the Week 1 walking skeleton.

### 1.5 Example user journeys

**Journey A — Q&A**

> Analyst: "Which product category had the highest average review rating in Q3 2018?"
>
> Agent: "**health_beauty** had the highest average review score (4.42 across 2,341 reviews) in Q3 2018. Next two were **books_general_interest** (4.41) and **fashion_underwear_and_beachwear** (4.39)."
>
> Agent (collapsible): SQL it ran.

**Journey B — Auto-EDA**

> Analyst: "Explore the order_reviews table and surface 3 patterns I should care about."
>
> Agent: produces a markdown report with three findings, each backed by SQL evidence and (later) a chart.

### 1.6 Dataset

**Olist Brazilian E-commerce** (Kaggle): 9 related tables, ~100k orders, multi-table joins, time series, customer-review text fields. Chosen for multi-table SQL realism plus a natural place to introduce embeddings/RAG over reviews in **Iteration B**.

---

## 2. Approach — Walking Skeleton + Iterations

The project follows the **walking skeleton** pattern: build a thin slice that goes end-to-end through every layer first (Week 1), then deepen each layer in dedicated iteration sessions afterward.

- **Week 1:** end-to-end Mode 1 (Q&A) agent on Olist with guardrails, traces, and evals. Production-shaped (real package, tests, CI-able), not a notebook script.
- **Each iteration after that:** one focused brainstorming → design → implementation cycle that adds *one* capability or replaces *one* layer.

**Why this shape:** Subhankar wants to learn all the steps/processes within a week, then iteratively improve. Walking skeleton matches that exactly — the whole system is visible early, every later improvement plugs into something already working.

### 2.1 Workflow with notebooks (Approach 3 — Hybrid)

- The Python package is the source of truth.
- Notebooks split into:
  - **`notebooks/demos/`** — committed, output-stripped via `nbstripout`. These are tutorial-style notebooks that import from the package and walk through what each layer does.
  - **`notebooks/scratch/`** — gitignored. Personal experiments, throwaway prompts.
- Practical flow:
  1. Explore in scratch notebook.
  2. Codify into the package (`src/ds_agent/...`).
  3. Add a test that pins behavior.
  4. Update or add a demo notebook that imports from the package.
  5. Commit package + tests + (output-stripped) demo notebook.

---

## 3. Architecture

### 3.1 The agent loop

At the core, an agent is a loop wrapping an LLM call. Each turn:

1. Send Claude: the conversation so far + the user's question + the list of available tools.
2. Claude responds with one of:
   - a **final answer** → exit the loop and return, OR
   - a **tool call** (e.g., `run_sql("SELECT ...")`) → execute the tool, append the result back into the conversation, loop again.

Eventually Claude says "I have enough" and the loop returns.

Every agent framework (LangChain, LlamaIndex, AutoGen, OpenAI Assistants, LangGraph) is a wrapper around this. Building it from scratch once is the single most valuable foundational lesson in agentic AI.

### 3.2 Components (Week 1 MVP)

| Component | Module | Role |
|---|---|---|
| `LLMClient` | `llm.py` | Anthropic SDK wrapper; retries, token counting |
| `ToolRegistry` + `BaseTool` | `tools/base.py` | Map tool name → schema → callable |
| `run_sql` | `tools/sql.py` | Execute SQL on DuckDB; returns rows |
| `get_relevant_schema` | `tools/schema.py` | Return schemas for the most relevant Olist tables (keyword match in Week 1) |
| `Guardrail` | `guardrails.py` | SQL safety check (regex + DuckDB `EXPLAIN`); refusal handling |
| `AgentLoop` | `agent.py` | Orchestrator — runs the loop, manages messages, calls tools |
| `Tracer` | `tracing.py` | Per-turn logging to local SQLite |
| `Evaluator` | `evals.py` | Offline runner — runs agent on test set, scores answers |
| `CLI` | `cli.py` | Typer commands: `ask`, `eval`, `trace list/show/replay` |

### 3.3 Data flow — single Q&A turn

For *"Which product category had the highest average review rating in Q3 2018?"*:

```
User question
   │
   ▼
[AgentLoop turn 1] → Claude (system prompt + tools + question)
                       │  tool call
                       ▼
                  get_relevant_schema("review rating, product category")
                       │
                       ▼
                  SchemaRetriever returns: orders, order_reviews, products
   │
   ▼
[AgentLoop turn 2] → Claude (previous + schema result)
                       │  tool call
                       ▼
                  run_sql("SELECT pc.product_category_name, AVG(r.review_score) ...")
                       │
                       ▼
                  Guardrail validates → DuckDB executes → rows returned
   │
   ▼
[AgentLoop turn 3] → Claude (previous + SQL result)
                       │  final answer
                       ▼
                  "health_beauty had the highest avg rating (4.42) ..."
   │
   ▼
Tracer wrote 3 LLM calls + 2 tool calls + final answer to traces.sqlite
```

The **Evaluator runs outside this flow** — it is an offline command (`just eval`) that calls `AgentLoop` on each test case and scores the result.

### 3.4 Why each component exists (defended against Section 1)

| Component | Defended by which success criterion |
|---|---|
| `run_sql` | #2 — analyst trusts answers backed by SQL |
| `get_relevant_schema` | Real schemas have many tables; agent must pick the right ones |
| `Guardrail` | #4 — must refuse destructive SQL, must not confidently bullshit |
| `Tracer` | #2 — show the analyst (and the reviewer) what the agent did |
| `Evaluator` | #4 — without evals, "is this agent good?" is a vibe, not an answer |
| `AgentLoop` | Mode 2 (Auto-EDA) needs multi-step reasoning; the loop must exist day one |

---

## 4. Capability Ladder

### 4.1 Week 1 — Walking Skeleton (Mode 1 only)

Seven steps. Each is one focused session. Each ends with a concrete capability Subhankar can demonstrate.

| # | Step | Concept(s) introduced | What Subhankar can do after |
|---|------|----------------------|------------------------------|
| 1 | First Claude call + project scaffold | LLM API basics, system prompt, message structure, tokens, env config, package layout, virtualenv | Make a hello-world Claude call from a real Python package |
| 2 | Olist data + DuckDB | Local analytical SQL, schema reading, dataset hygiene | Query Olist tables from Python in <100ms |
| 3 | Tool use: `run_sql` | Tool schemas, function calling, the agent loop pattern | Have Claude write SQL, execute it, and use the result |
| 4 | Multi-turn agent loop | Turn-by-turn message accumulation, exit conditions | One question → schema lookup → SQL → answer, autonomous |
| 5 | Guardrails | Structured output for refusals, SQL safety check, graceful errors | Agent refuses destructive SQL, errors politely |
| 6 | Tracing | Per-turn logging to SQLite, replay-from-trace | Debug "why did the agent do that?" after the fact |
| 7 | Evaluation | Test-set design, automated scoring, regression detection | `just eval` scores the agent on 10 fixed questions |

After Step 7: `ds-agent ask "Which categories drove Q3 2018 revenue?"` returns the correct answer, the SQL it ran, and a trace ID.

**Notably NOT in Week 1:**
- Embeddings / vector DB — keyword schema lookup is enough for 9 tables. Iter B owns this.
- Auto-EDA / planner — Mode 2 deserves a dedicated session (Iter A).
- Web UI, caching, multi-agent — all later.

### 4.2 Iteration backlog (post-Week-1)

Pick one per session. Order is flexible.

| Code | Iteration | Concept it teaches |
|---|---|---|
| **A** | Auto-EDA mode | Planning (LLM decomposes a goal into steps), markdown reports — Mode 2 |
| **B** | RAG over reviews | Embeddings, vector store (Chroma or DuckDB-VSS), semantic search |
| **C** | LLM-as-judge evals | Holistic LLM grading; judge calibration; pitfalls |
| **D** | Pandas tool + charts | Sandboxed Python, chart artifacts as part of the answer |
| **E** | Streamlit UI | Web interface; UX for SQL + answer + trace together |
| **F** | Caching + cost control | Anthropic prompt caching, response caching, budget tracking |
| **G** | Memory across sessions | Persisting conversation history, summarization strategies |
| **H** | Multi-agent split | Planner + executor + critic; orchestration tradeoffs |
| **I** | Open-source port (Ollama) | Provider abstraction; what is portable across LLMs |
| **K** | Kedro refactor of pipelines | Refactor data ingestion and eval runner into Kedro pipelines; learn DAG-vs-loop distinction firsthand |
| **L** | LangGraph rebuild | Reimplement the agent in LangGraph; compare to hand-built loop |
| **M** | MCP server wrap | Wrap `run_sql` and `get_relevant_schema` as a Model Context Protocol server |
| **N** | A2A protocol | Agent-to-Agent communication standard; pairs naturally with **H** |
| **J1** | Dockerize + FastAPI | Containerize as a real service; portable deployable artifact |
| **J2** | Deploy to AWS | ECS/Lambda; CloudWatch traces; optionally compare Bedrock as LLM provider |
| **J3** | Deploy to Azure | Container Apps + Azure OpenAI; compare clouds against AWS work |

**Recommended cloud sequencing:** J1 → J2 (AWS) → J3 (Azure). Flippable if Subhankar's context (work cloud) demands it.

---

## 5. Stack

### 5.1 Core libraries (Week 1)

| Library | Role | What it teaches |
|---|---|---|
| `anthropic` | Official Anthropic Python SDK | Real shape of an LLM API: messages, system prompts, tokens, streaming, tool definitions |
| `duckdb` | Embedded analytical SQL engine | Schema reading, EXPLAIN plans, parameterized queries — transferable to Postgres / BigQuery |
| `pydantic` | Data validation | Standard tool for structured output from LLMs |
| `typer` | CLI framework using type hints | Production-grade CLI patterns |
| `python-dotenv` | Loads `.env` file | Standard secret-management pattern |
| `rich` | Pretty terminal output | Polished CLI demos, formatted traces |
| `pytest` | Test runner | Non-negotiable for production code |
| `ruff` | Linter + formatter | Modern, fast Python code-quality tool |

### 5.2 Dev tooling

| Tool | Role |
|---|---|
| `conda` | Python environment + package manager. Chosen because Subhankar is already fluent with it (data-science default). Pattern: `environment.yml` for Python version + conda-installable deps, `pip install -e .` inside the env for the `pyproject.toml`-defined `ds_agent` package. |
| `pre-commit` | Git hooks framework |
| `nbstripout` | Strips notebook outputs at commit time |
| `git` + GitHub | Version control + remote |
| `pyproject.toml` | Single source of truth for package, deps, ruff, pytest config |
| `.env.example` | Committed sample env file; real `.env` gitignored |
| `justfile` | Tiny command runner (`just ask`, `just eval`, `just test`, `just lint`) |

### 5.3 Explicitly excluded in Week 1 (with reasons)

| Excluded | Why deferred |
|---|---|
| LangChain / LlamaIndex / DSPy / CrewAI / AutoGen | Hide the agent loop. Building it once teaches the underlying mechanics. Frameworks become Iter L (LangGraph) and possibly later comparisons. |
| Real database (Postgres / Snowflake) | DuckDB on local CSVs is enough for Olist; SQL is SQL — no new concepts gained from a heavier engine in Week 1 |
| Vector DB (Chroma / Qdrant / pgvector) | No semantic retrieval in Week 1; Iter B introduces the vector DB on its own merits |
| Web framework (FastAPI / Streamlit) | CLI is enough; Iter E / Iter J1 own this |
| Anthropic prompt caching | Cost optimization; meaningful only at higher volume — Iter F |
| Hosted observability (Langfuse / Phoenix / Langsmith) | Local SQLite traces teach the *concept*; hosted comparison comes later |
| Kedro | Plain Python in Week 1; Iter K is the dedicated Kedro session |

---

## 6. Repo Layout

Principle: each file has one clear purpose; you should be able to guess what is in it from its name. When a file grows past ~300 lines or starts mixing responsibilities, split it.

```
ds-agent/
├── .env.example                  # Sample env vars (no real secrets) — committed
├── .gitignore                    # .env, data/, __pycache__/, notebooks/scratch/, traces/, evals_results/, *.duckdb (conda env lives outside the repo, so no .venv/ entry needed)
├── .pre-commit-config.yaml       # ruff format, ruff check, nbstripout
├── environment.yml               # Conda env spec — Python version + conda deps
├── pyproject.toml                # Package metadata, pip-installable deps, ruff & pytest config
├── README.md                     # How to set up + how to run
├── justfile                      # `just ask`, `just eval`, `just test`, `just lint`
│
├── src/
│   └── ds_agent/                 # The actual Python package
│       ├── __init__.py
│       ├── __main__.py           # `python -m ds_agent` entry point
│       ├── cli.py                # Typer commands: ask, eval, trace
│       ├── config.py             # Settings from env (API key, model name, paths)
│       ├── llm.py                # Anthropic client wrapper (retries, token counting)
│       ├── prompts.py            # System prompts as named constants
│       ├── schemas.py            # Pydantic models (tool args, structured outputs)
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── base.py           # ToolRegistry, base interface
│       │   ├── schema.py         # get_relevant_schema tool
│       │   └── sql.py            # run_sql tool (calls into DuckDB)
│       ├── guardrails.py         # SQL safety check (regex + DuckDB EXPLAIN)
│       ├── agent.py              # The agent loop — heart of the system
│       ├── tracing.py            # SQLite trace logger + replay helpers
│       └── evals.py              # Test questions, runner, scorers (single file in Week 1)
│
├── tests/                        # pytest unit tests (mirror src/)
│   ├── conftest.py               # Shared fixtures (mock LLM, in-memory DuckDB)
│   ├── test_tools.py
│   ├── test_guardrails.py
│   ├── test_agent_loop.py        # Uses a mocked LLM client — no real API calls
│   └── test_tracing.py
│
├── notebooks/
│   ├── demos/                    # Committed, output-stripped
│   │   ├── 01_first_claude_call.ipynb
│   │   ├── 02_duckdb_olist.ipynb
│   │   ├── 03_first_tool_use.ipynb
│   │   ├── 04_full_agent_loop.ipynb
│   │   └── 05_evals_and_traces.ipynb
│   └── scratch/                  # Gitignored — Subhankar's personal experiments
│       └── .gitkeep
│
├── data/                         # Gitignored — Olist CSVs land here after download
│   └── .gitkeep
│
├── traces/                       # Gitignored contents — local SQLite trace store lives here
│   └── .gitkeep
│
├── evals_results/                # Gitignored — per-run eval result JSONs land here
│   └── .gitkeep
│
├── scripts/                      # Standalone utility scripts (NOT part of the package)
│   ├── download_data.py          # Fetches Olist (Kaggle API or direct URL)
│   └── load_to_duckdb.py         # CSVs → ds_agent.duckdb
│
└── docs/
    ├── superpowers/
    │   └── specs/
    │       └── 2026-04-30-data-science-agent-design.md   # this file
    └── ARCHITECTURE.md            # one-page architecture overview (written at end of Week 1)
```

**Patterns explicitly avoided:**

- No `utils.py` or `helpers.py` (these become dumping grounds; helpers go in the module where they belong, or get a specific name).
- No notebook-only logic (anything durable lives in the package; notebooks import from the package).
- No `agent/` subpackage in Week 1 — single `agent.py` is enough until the loop grows past ~300 lines.

---

## 7. Evaluation

### 7.1 Why evals exist

LLM agents are non-deterministic — same input, different output run-to-run. Unit tests cannot verify "the agent gave a good answer" because there is no single right output. Evals plug that gap by scoring outputs against expected properties.

### 7.2 Test set

10 hand-crafted questions on Olist, defined as `EvalCase` Pydantic models in `evals.py`:

```python
class EvalCase(BaseModel):
    id: str                              # "easy_revenue_q3_2018"
    question: str
    expected_answer_contains: list[str]  # substrings expected in the final answer
    expected_sql_contains: list[str]     # substrings/regex expected in the generated SQL
    expected_tools: list[str]            # tools that should appear in the trace
    difficulty: Literal["easy", "medium", "hard"]
    category: Literal["single_table", "join", "time_series", "aggregation"]
```

### 7.3 Scorers (each returns 0–1 per case)

| Scorer | What it checks | Implementation |
|---|---|---|
| `answer_contains` | Final answer mentions expected entities | substring match |
| `sql_contains` | Generated SQL has the right shape | regex / substring |
| `tools_called` | Agent called the right tools (read from trace) | set comparison |
| `no_errors` | Agent finished without crashing or refusing wrongly | bool |

### 7.4 Roll-up metrics

- Accuracy (weighted average of scorers)
- Cost (total tokens × per-token price)
- Latency (avg seconds per question)
- Turn efficiency (avg agent-loop turns per question)

### 7.5 Command and output

`just eval` (or `python -m ds_agent eval`) runs the agent on all 10 cases, prints a `rich` table with per-case scores + roll-up, writes results to `evals_results/<timestamp>.json` (top-level, gitignored) for regression tracking. Top-level rather than under `src/` because results are *data*, not code.

### 7.6 Why evals are separate from `pytest`

1. Evals cost real API money; pytest should be free.
2. Evals are non-deterministic; pytest assertions hate that.
3. Evals are a *check on quality*; pytest is a *check on correctness of pure code*.

Pytest still covers tools, guardrails, and the loop logic with a mocked LLM client.

### 7.7 Deepenings (later iterations)

- **Iter C** — LLM-as-judge replaces substring matching for holistic answer grading; calibration dataset to measure judge agreement with humans.
- Later — eval-driven development (write the eval first, implement the capability after).

---

## 8. Observability

### 8.1 Storage

Local SQLite at `traces/traces.sqlite`, two tables:

```
runs                              events
─────                             ──────
run_id (UUID, PK)                 event_id (PK)
user_question                     run_id (FK → runs)
final_answer                      seq (turn / step number)
status (ok / error / refused)     kind (llm_call / tool_call / tool_result / final_answer)
total_tokens                      payload (JSON — full input/output for that step)
total_cost_usd                    latency_ms
total_latency_ms                  created_at
created_at
```

### 8.2 Decorator pattern

Every LLM call and tool call goes through a wrapping function (decorator) that automatically logs to the tracer. We do not sprinkle `print` or `logger` statements through agent code; tracing is centralized at the boundaries.

### 8.3 Replay commands

| Command | What it does |
|---|---|
| `ds-agent trace list` | Recent runs (id, question, status, latency, cost) |
| `ds-agent trace show <run_id>` | Full pretty-printed trace — every turn, every tool call, every payload |
| `ds-agent trace replay <run_id>` | Re-runs the agent on the same question; side-by-side diff with the original (useful for "I changed the prompt, does it still work?") |

### 8.4 Why local SQLite (not a hosted tool)

- Zero external dependencies, zero account setup, runs offline.
- SQL-queryable — Subhankar can analyze traces with the same SQL skills the agent uses.
- Easy to inspect from notebooks (`pd.read_sql("SELECT * FROM runs", conn)`).
- Hosted observability (Langfuse / Phoenix / Langsmith) is its own valuable lesson — belongs in a later iteration where local-vs-hosted can be compared directly.

---

## 9. How Evaluation and Observability Interlock

- **Evals depend on traces.** Scorers like `tools_called` read from the trace to verify the agent did the right thing structurally.
- **Traces help debug eval failures.** When an eval fails, the next step is `ds-agent trace show <run_id>`.
- **Both stay durable across iterations.** New tools, planners, RAG, multi-agent — all extend this framework with minor additions, not rewrites.

---

## 10. Open Decisions

- **Cloud order** locked in as J1 → J2 (AWS) → J3 (Azure); flippable if work context demands.
- **Environment manager:** `conda` chosen (Subhankar's existing tool). `environment.yml` is the env spec; `pip install -e .` inside the conda env installs the project package.
- **Detailed test-question list:** the 10 specific Olist questions will be drafted during Step 7 of Week 1; the spec only fixes the *framework*.
- **GitHub remote:** project will be a single repo (`ds-agent`); pushing it to GitHub is part of Step 1.

---

## 11. Explicit Non-Goals (Week 1)

- Multi-user / multi-tenant.
- Authentication / authorization.
- A web UI.
- Hosted observability platforms.
- Real cloud deployment.
- Agentic frameworks (LangChain, LangGraph, etc.).
- Vector DBs / embeddings.
- Multi-agent.
- Memory across sessions.
- Auto-EDA mode (Mode 2).

These all live in the iteration backlog (Section 4.2).

---

## 12. Glossary

| Term | One-line definition |
|---|---|
| **LLM** | Large Language Model — the neural network behind Claude/ChatGPT |
| **API call** | Calling Claude over HTTP from your own code (instead of via a chat UI) |
| **System prompt** | Persistent instructions sent to the LLM every turn |
| **Prompt engineering** | The craft of writing instructions to an LLM so it does what you want reliably |
| **Tool use / function calling** | Letting the LLM ask your code to run a specific function and feeding the result back |
| **Tool schema** | JSON description of a tool (name, args, what it does) that the LLM reads |
| **Agent** | An LLM that takes actions in a loop until a task is done |
| **Agent loop** | The loop that wraps an LLM call with tool execution and message accumulation |
| **Structured output** | Forcing the LLM to return JSON in a specific schema |
| **Guardrails** | Safety/validation filters around an LLM (e.g., block destructive SQL) |
| **Tracing / trace** | Recorded log of every LLM call, tool call, and result inside one agent run |
| **Eval** | Automated test that scores agent quality (vs. unit tests, which check code correctness) |
| **RAG** | Retrieval-Augmented Generation — let the LLM look things up before answering |
| **Embedding** | Numeric vector representing the meaning of a piece of text |
| **Vector DB** | Database optimized for finding closest embeddings to a query embedding |
| **DuckDB** | Embedded analytical SQL engine (like SQLite, built for analytics) |
| **Pydantic** | Python library for data shapes as classes; auto-generates JSON schemas |
| **Typer** | CLI framework for Python using type hints |
| **Ruff** | Fast Python linter + formatter |
| **uv** | Modern fast Python package + virtualenv manager |
| **pre-commit** | Framework to run checks (format, lint) before each git commit |
| **nbstripout** | Tool that strips notebook outputs at commit time |
| **DAG** | Directed Acyclic Graph — graph of nodes with one-way data flow, no cycles |
| **Walking skeleton** | Software-engineering pattern: build a thin end-to-end slice first, then deepen each layer |
| **MCP** | Model Context Protocol — Anthropic standard for exposing tools/data to LLMs |
| **A2A** | Agent-to-Agent — Google standard for inter-agent communication |
| **LangGraph** | LangChain framework for stateful, graph-based agent applications |
| **Kedro** | Data-science pipeline framework for static DAGs |
| **Decorator** | A function that wraps another function to add behavior |
