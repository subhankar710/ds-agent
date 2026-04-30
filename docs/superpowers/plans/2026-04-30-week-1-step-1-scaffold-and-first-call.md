# Lesson Plan — Week 1, Step 1: Project scaffold & first Claude call

> **For agentic workers:** This plan is a **learning-first lesson**, not a ship-fast checklist. Each substep names a mode (**Tutor** = Claude codes + narrates; **Coach** = Subhankar codes, Claude reviews) before any code is written. Steps use checkbox (`- [ ]`) syntax for tracking.

- **Date:** 2026-04-30
- **Step in Week 1:** 1 of 7
- **Estimated time:** ~2 hours (30 min Tutor + 60–90 min Coach + reflection)
- **Prerequisites:** see [Section 0](#0-prerequisites) below

> **Commit policy for this plan:** every "Suggested commit" block lists exact `git add` / `git commit` commands. **Subhankar runs these — Claude does not.** Run them whenever it feels like a good checkpoint; the suggested moments are guidance, not mandate.

---

## 0. Prerequisites

Before starting this lesson, verify the following are installed and ready. **Subhankar runs every check; Claude reviews output.**

- [ ] **Anaconda or Miniconda installed** (for conda environment management).
  - Check: `conda --version` should print something like `conda 24.x.x`.
  - If not installed: download Miniconda from https://docs.conda.io/en/latest/miniconda.html.

- [ ] **Git installed** and configured with name/email.
  - Check: `git --version` and `git config --global user.email`.

- [ ] **A code editor** (VS Code, PyCharm, Cursor — anything Subhankar prefers).

- [ ] **Anthropic API key obtained.**
  - Sign in at https://console.anthropic.com/.
  - Go to **Settings → API Keys → Create Key**.
  - Copy the key (starts with `sk-ant-api03-...`). It's shown **once** — save it somewhere safe before closing the dialog.
  - Add at least $5 of credits (Settings → Billing) — for Week 1 we'll use cents, but the API rejects calls if billing isn't set up.

- [ ] **Working directory exists:** `/Users/subhankarpatra/Documents/ds-agent/` (already created when the spec was written).

When all five are checked, proceed.

---

## 1. Concept — what this lesson teaches

This is the most pedagogically dense lesson in Week 1, because *every later lesson assumes you understand what's happening here*. The core ideas:

### 1.1 What an LLM API call actually is

An LLM API call is just an HTTPS POST request. You send Claude a JSON body with three main pieces:

- **`model`** — which Claude variant (e.g., `claude-sonnet-4-6`)
- **`system`** — persistent instructions ("you are a helpful data analyst")
- **`messages`** — the conversation so far, as a list of `{"role": "user"|"assistant", "content": "..."}` objects

Claude responds with text + token counts + stop reason. **That's the whole interface.** Every "agent framework" you'll ever see is built on top of this.

### 1.2 Why a Python *package* (not just a script)

Subhankar will write *modules* (`config.py`, `llm.py`, etc.) inside a package called `ds_agent`. Why?

- A package can be **installed** (`pip install -e .`) so its modules can be imported anywhere — including from notebooks, tests, and other scripts.
- A package can declare a **CLI entrypoint** (we'll wire `ds-agent` as a real command).
- Tests run against the *installed* package — catching packaging bugs early.
- **`src/` layout** in particular forces you to install before importing, which is the production-standard pattern.

### 1.3 Why secrets management (`.env` + `python-dotenv`) matters

The Anthropic API key is a credential. If you commit it, anyone who reads the repo can spend your money. Industry-standard pattern:

- **`.env`** holds the actual key (never committed).
- **`.env.example`** holds dummy values, showing what env vars exist (committed).
- Code never references the key directly — it reads `os.environ["ANTHROPIC_API_KEY"]`.
- `python-dotenv` loads `.env` into the environment at startup so dev and prod look the same to your code.

### 1.4 Why **Pydantic Settings** for config

In production Python apps you don't read env vars with `os.getenv` scattered across the code. You define a single **typed Settings class** that:

- Validates types at startup (typo'd env var = clear error, not a runtime crash)
- Documents every config knob in one place
- Provides defaults
- Plays nicely with editor autocomplete

Pydantic ships a sub-package called `pydantic-settings` for exactly this.

### 1.5 Why a thin **wrapper around the SDK** (not direct SDK calls everywhere)

We'll write `LLMClient` — a small class that wraps `anthropic.Anthropic`. We could just use the SDK directly. We don't, because:

- **Single chokepoint** — every LLM call goes through one place. When we add tracing in Step 6, we add one decorator and the entire app is traced. Without a wrapper, you'd have to find every `client.messages.create(...)` call.
- **Testability** — tests inject a fake `LLMClient`. Without a wrapper, every test would need to monkey-patch the SDK.
- **Provider abstraction (future)** — when we port to Ollama (Iter I), we swap the wrapper's internals; no other code changes.

This is **the most important production pattern in this lesson.** Every senior engineer doing this work has a wrapper.

### 1.6 Why **mocked tests** (not real API calls in tests)

`pytest` should be free, fast, and deterministic:

- **Free** — real API calls cost money; running the test suite shouldn't.
- **Fast** — real API calls take 1–5 seconds; mocked ones take milliseconds.
- **Deterministic** — same input → same output every time; LLM outputs aren't.

The test for `LLMClient` injects a fake Anthropic client and asserts the wrapper transforms inputs/outputs correctly. We *don't* test "is Claude smart" in pytest — that's what evals (Step 7) are for.

---

## 2. Goal (the done definition)

By the end of Lesson 1, Subhankar can:

1. Activate a conda env named `ds-agent` containing Python 3.12 and all Week 1 deps.
2. Run `ds-agent ask "say hello in pirate"` from the terminal and see Claude's reply printed in pretty terminal output.
3. Run `pytest` from the project root and see all unit tests pass — without making any real API calls.
4. Show that committing the project does **not** include the `.env` file (proving the secret stays local).

**Quantitative done test (you can run these and they all succeed):**

```bash
conda activate ds-agent
pytest -v                                 # all tests pass
ds-agent ask "what is your model name?"   # prints a real response from Claude
git status --ignored                      # shows .env in the "ignored" list, not "untracked"
```

---

## 3. File map for this lesson

By the end of the lesson, the project tree will look like this (only files relevant to Step 1 — full layout from the spec arrives over later steps):

```
ds-agent/
├── .env                              # NEW — gitignored, holds API key
├── .env.example                      # NEW — committed sample
├── .gitignore                        # NEW
├── environment.yml                   # NEW — conda env spec
├── pyproject.toml                    # NEW — package metadata + pip deps
├── README.md                         # NEW — minimal "how to set up"
├── src/
│   └── ds_agent/
│       ├── __init__.py               # NEW — empty package marker
│       ├── __main__.py               # NEW — `python -m ds_agent` entry
│       ├── cli.py                    # NEW — Typer CLI
│       ├── config.py                 # NEW — Pydantic Settings
│       └── llm.py                    # NEW — Anthropic wrapper
└── tests/
    ├── __init__.py                   # NEW — empty
    ├── conftest.py                   # NEW — shared fixtures
    ├── test_config.py                # NEW
    └── test_llm.py                   # NEW
```

Files we will *not* touch in this lesson (deferred to Steps 2–7): `tools/`, `agent.py`, `guardrails.py`, `tracing.py`, `evals.py`, `notebooks/`, `data/`, `scripts/`, `traces/`, `evals_results/`, `justfile`, `.pre-commit-config.yaml`. Mentioning them so the absence isn't a surprise.

---

## 4. Substep (a) — Conda env, `environment.yml`, `.env` setup [Tutor mode]

> **Why Tutor:** This is mechanical config. High value to see done correctly once and understand the *shape*. Low value for Subhankar to derive from scratch.

### 4.1 What Claude does and why — narrated

**Claude's actions in this substep, with reasoning before each:**

#### 4.1.1 Create the top-level files

The first thing we do in any project is establish the *boundary* — what's part of the project, what's local-only, what's documented. Three files do this:

- `environment.yml` — the conda env spec (Python version + conda packages)
- `.gitignore` — what git must never see
- `.env.example` — the schema of secrets, committed for documentation
- `.env` — the actual secrets, **never** committed

We deliberately create `.gitignore` *before* `.env`. This is a habit: never let a secret file exist in a git-tracked directory before it's gitignored, because if you `git add` by accident, recovery is annoying.

- [ ] **Step (a.1) — Claude writes `.gitignore`**

```gitignore
# Secrets — never commit
.env

# Data files (downloaded separately)
data/
*.duckdb
*.duckdb.wal

# Python build artifacts
__pycache__/
*.pyc
*.pyo
*.egg-info/
dist/
build/

# Testing / tooling caches
.pytest_cache/
.ruff_cache/
.coverage

# Notebooks — scratch only; demos are committed
notebooks/scratch/

# Local trace + eval result stores (filled at runtime)
traces/
evals_results/

# OS / editor
.DS_Store
.vscode/
.idea/
```

**Why each block:**
- `.env` is the most important line — secret leakage is the #1 way junior projects get burned.
- `*.duckdb` because DuckDB writes the database file to disk; we don't want it in git.
- `__pycache__` is Python's bytecode cache — not source.
- `.pytest_cache`, `.ruff_cache` are tool caches — local to the developer.
- `traces/` and `evals_results/` are *runtime* output, not source.
- We do **not** ignore the conda env folder because conda envs live outside the repo (under `~/anaconda3/envs/ds-agent/`).

- [ ] **Step (a.2) — Claude writes `environment.yml`**

```yaml
name: ds-agent
channels:
  - conda-forge
dependencies:
  - python=3.12
  - pip
  # The rest of our Python deps install via pip from pyproject.toml
  # to keep dependency resolution simple. We use conda only for
  # the Python version and pip itself.
  - pip:
      - -e .[dev]
```

**Why this shape:**
- `python=3.12` — current LTS-equivalent Python, supports all our deps.
- `conda-forge` channel is the community-maintained channel; broader package coverage than `defaults`.
- We use **conda only for Python + pip**, then `pip install -e .[dev]` pulls everything else from `pyproject.toml`. Mixing conda and pip for the same package is a common source of pain — keeping the surfaces clean.
- `-e .` is "install this directory as an editable package" — code edits are reflected without reinstalling.
- `[dev]` is an "extras" group we'll define in `pyproject.toml`; it pulls in pytest, ruff, etc. only for dev environments.

- [ ] **Step (a.3) — Claude writes `.env.example`**

```dotenv
# Copy this file to `.env` and fill in real values.
# `.env` is gitignored; never commit secrets.

# Anthropic API key (required) — get one at https://console.anthropic.com
ANTHROPIC_API_KEY=sk-ant-api03-replace-me

# Default Claude model. You can override per-call later.
ANTHROPIC_MODEL=claude-sonnet-4-6

# Where the DuckDB database file lives (created in Step 2)
DUCKDB_PATH=./data/ds_agent.duckdb
```

**Why each variable:**
- `ANTHROPIC_API_KEY` — required, no default (we want a clear error if missing).
- `ANTHROPIC_MODEL` — choosing a default lets us swap models without code changes. We're using **Sonnet 4.6** by default — it's the right tradeoff of capability/cost for agentic SQL work in 2026.
- `DUCKDB_PATH` — set now even though Step 2 introduces DuckDB; centralizes path config.

### 4.2 What Subhankar does — local-machine actions

These steps Claude can't run for you; you run them, then paste the output back so Claude can verify.

- [ ] **Step (a.4) — Subhankar creates `.env` with the real API key**

In the project root, **manually copy** `.env.example` to `.env` and edit the API key line:

```bash
cp .env.example .env
# then open .env in your editor and replace `sk-ant-api03-replace-me`
# with your real key from console.anthropic.com
```

**Verify the key isn't trackable:**

```bash
git check-ignore -v .env
```

**Expected output:** something like `.gitignore:2:.env	.env` — confirming `.env` is ignored.

- [ ] **Step (a.5) — Subhankar creates the conda env**

```bash
cd /Users/subhankarpatra/Documents/ds-agent
conda env create -f environment.yml
```

**Note:** this command will **fail at the `pip install -e .[dev]` line** because we haven't written `pyproject.toml` yet. That's expected. We'll come back and run it after substep (b).

For now, just create the env *without* the pip section. Temporarily edit `environment.yml` to comment out the `pip:` block:

```yaml
name: ds-agent
channels:
  - conda-forge
dependencies:
  - python=3.12
  - pip
  # - pip:
  #     - -e .[dev]
```

Re-run `conda env create -f environment.yml`. This creates the env with just Python and pip. Then activate:

```bash
conda activate ds-agent
python --version    # should print Python 3.12.x
which pip           # should point inside the conda env
```

We'll uncomment the `pip:` block after substep (b).

### 4.3 Suggested commit (after substep (a))

```bash
git init                            # if not already a git repo
git add .gitignore .env.example environment.yml
git status                          # confirm .env is NOT in the staged files
git commit -m "chore: scaffold project — gitignore, env example, conda env spec"
```

---

## 5. Substep (b) — `pyproject.toml` + project layout [Tutor mode]

> **Why Tutor:** Industry-standard scaffolding. Subhankar will see this pattern in every modern Python project; one careful pass through it builds the mental model for life.

### 5.1 Concept — what `pyproject.toml` does

`pyproject.toml` is the **single source of truth** for a modern Python project. It replaces the older `setup.py`, `setup.cfg`, `requirements.txt`, `MANIFEST.in` patchwork. It declares:

- Package metadata (name, version, description)
- Runtime dependencies (`anthropic`, `duckdb`, etc.)
- Optional/extras dependencies (`dev` group with pytest, ruff)
- The CLI entrypoint (so `ds-agent` becomes a real shell command)
- Tool configurations (ruff, pytest)

When you `pip install -e .`, pip reads `pyproject.toml` to figure out what to do.

### 5.2 What Claude does

- [ ] **Step (b.1) — Claude creates the `src/ds_agent/` and `tests/` directory structure**

Empty placeholder files:

```
src/ds_agent/__init__.py     (empty file)
src/ds_agent/__main__.py     (empty file — content arrives in step (e))
tests/__init__.py            (empty file)
```

These empty `__init__.py` files mark directories as Python packages.

- [ ] **Step (b.2) — Claude writes `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "ds-agent"
version = "0.0.1"
description = "A learning-first Data Science Agent: NL questions over Olist via Claude + DuckDB."
readme = "README.md"
requires-python = ">=3.12"
authors = [
  { name = "Subhankar Patra", email = "subhankar710@gmail.com" }
]

# Runtime dependencies — what the package needs to actually run.
dependencies = [
  "anthropic>=0.40.0",          # Anthropic Python SDK
  "pydantic>=2.7",              # Data shapes + validation
  "pydantic-settings>=2.4",     # Typed settings from env vars
  "python-dotenv>=1.0",         # Loads .env at startup
  "typer>=0.12",                # CLI framework
  "rich>=13.7",                 # Pretty terminal output
  "duckdb>=1.0",                # Embedded analytical SQL (Step 2)
]

# Dev-only dependencies — only installed with `pip install -e .[dev]`.
[project.optional-dependencies]
dev = [
  "pytest>=8.0",
  "pytest-mock>=3.12",          # Convenient mocker fixture
  "ruff>=0.6",                  # Lint + format
]

# CLI entrypoint — installs a `ds-agent` command in the env's bin/.
[project.scripts]
ds-agent = "ds_agent.cli:app"

# Tells setuptools where the package source lives.
[tool.setuptools.packages.find]
where = ["src"]

# Ruff config — modern Python linter + formatter, single tool.
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = [
  "E", "W",   # pycodestyle (errors, warnings)
  "F",        # pyflakes (unused imports, undefined names)
  "I",        # isort (import order)
  "B",        # bugbear (likely bugs)
  "UP",       # pyupgrade (modern Python idioms)
]

# Pytest config — where tests live, how to run them.
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra -q"              # show short summary of failed/skipped, quiet otherwise
```

**Why every block, in order of importance:**

- `[project] dependencies` — pinned to **minimum versions, not exact versions.** This lets pip resolve the latest compatible version. Exact-pinning is for `requirements.txt` lockfiles, which we'll add later if needed.
- `[project.scripts] ds-agent = "ds_agent.cli:app"` — this magic line means: when someone installs the package, create a shell command `ds-agent` that calls `ds_agent.cli.app()`. Typer's `app` is callable.
- `[tool.setuptools.packages.find] where = ["src"]` — tells setuptools the package lives in `src/`, not at the project root. **This is what makes the "src layout" work.**
- `[tool.ruff]` and `[tool.ruff.lint] select` — picks the lint rule families we want.
- `[tool.pytest.ini_options]` — tells pytest where tests live so we don't pass `tests/` on every command.

- [ ] **Step (b.3) — Claude writes a minimal `README.md`**

```markdown
# ds-agent

A learning-first Data Science Agent — answers natural-language questions over the Olist dataset using Claude + DuckDB.

## Setup (one-time)

1. Install [Miniconda](https://docs.conda.io/en/latest/miniconda.html).
2. Get an Anthropic API key from https://console.anthropic.com.
3. Clone this repo, then:

   ```bash
   cp .env.example .env
   # edit .env, replace ANTHROPIC_API_KEY with your real key

   conda env create -f environment.yml
   conda activate ds-agent
   ```

## Run

```bash
ds-agent ask "what is your model name?"
```

## Test

```bash
pytest
```

## Project layout

See `docs/superpowers/specs/2026-04-30-data-science-agent-design.md` for the design spec.
```

### 5.3 What Subhankar does — install the package

- [ ] **Step (b.4) — Uncomment the pip block in `environment.yml`**

Edit `environment.yml`, removing the `# ` from the pip lines:

```yaml
name: ds-agent
channels:
  - conda-forge
dependencies:
  - python=3.12
  - pip
  - pip:
      - -e .[dev]
```

- [ ] **Step (b.5) — Update the env to install the package**

```bash
conda activate ds-agent
conda env update -f environment.yml --prune
```

`--prune` removes packages no longer in the spec. Expect this to take 30–90 seconds.

- [ ] **Step (b.6) — Verify the install**

```bash
which ds-agent          # should point inside the conda env's bin/
ds-agent --help         # will show "Missing command" for now — that's fine; means the entrypoint is wired
python -c "import ds_agent; print(ds_agent.__file__)"  # confirms package is importable
pytest                  # 0 tests, but should run cleanly with no errors
```

If any of these fail, paste the error to Claude before proceeding.

### 5.4 Suggested commit (after substep (b))

```bash
git add pyproject.toml environment.yml README.md src/ tests/
git status              # verify .env is NOT staged
git commit -m "feat: scaffold ds_agent Python package with pyproject + src layout"
```

---

## 6. Substep (c) — `config.py` (Pydantic Settings) [Coach mode]

> **Why Coach:** This is real Python code with a real production pattern (typed settings). Writing it from scratch builds the muscle.

### 6.1 The spec — what Subhankar will build

A module `src/ds_agent/config.py` that defines a `Settings` class with these typed fields:

| Field | Type | Default | Notes |
|---|---|---|---|
| `anthropic_api_key` | `str` | (no default — required) | Read from env `ANTHROPIC_API_KEY` |
| `anthropic_model` | `str` | `"claude-sonnet-4-6"` | Read from env `ANTHROPIC_MODEL` |
| `duckdb_path` | `str` | `"./data/ds_agent.duckdb"` | Read from env `DUCKDB_PATH` |

It also exports a function `get_settings()` that returns a singleton `Settings` instance. Singleton means: calling `get_settings()` multiple times returns the same object, not a new one each time (avoids re-reading env vars repeatedly).

### 6.2 The test — write this FIRST, before `config.py`

The test defines what "done" means. **Write the test first, run it, watch it fail (because the code doesn't exist yet), then implement.** This is **TDD** (Test-Driven Development) — the production-grade way to write code: the test is your spec, executable.

- [ ] **Step (c.1) — Subhankar writes `tests/test_config.py`**

Create the file. Subhankar writes the test based on the spec above. Use these signposts:

```python
# tests/test_config.py
"""Tests for ds_agent.config — typed settings loading."""

import pytest
from ds_agent.config import Settings, get_settings


def test_settings_loads_from_env(monkeypatch):
    """Given env vars are set, Settings() picks them up."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-12345")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    monkeypatch.setenv("DUCKDB_PATH", "/tmp/test.duckdb")

    settings = Settings()

    assert settings.anthropic_api_key == "sk-ant-test-12345"
    assert settings.anthropic_model == "claude-sonnet-4-6"
    assert settings.duckdb_path == "/tmp/test.duckdb"


def test_settings_uses_defaults_when_env_missing(monkeypatch):
    """Given only the required env var, defaults fill the rest."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-12345")
    monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
    monkeypatch.delenv("DUCKDB_PATH", raising=False)

    settings = Settings()

    assert settings.anthropic_model == "claude-sonnet-4-6"
    assert settings.duckdb_path == "./data/ds_agent.duckdb"


def test_settings_raises_when_api_key_missing(monkeypatch):
    """Given no API key in env, Settings() must raise — this is a deliberate guardrail."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(Exception):  # we'll narrow this once the implementation exists
        Settings(_env_file=None)  # _env_file=None disables .env auto-loading for this test


def test_get_settings_returns_singleton(monkeypatch):
    """get_settings() should cache — calling twice returns the same instance."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-12345")
    a = get_settings()
    b = get_settings()
    assert a is b
```

**Concepts in this test file (worth pausing on):**

- **`monkeypatch`** — pytest's built-in fixture for safely setting/unsetting env vars (and other globals) for the duration of one test, then restoring them.
- **`pytest.raises(...)`** — asserts the block raises an exception of the given type.
- **`a is b`** vs `a == b` — `is` checks identity (same object in memory); we use it because singleton means *same* object, not *equal* objects.
- **Why the missing-API-key test passes `_env_file=None`** — pydantic-settings normally reads `.env` automatically. In a test we want to disable that so we're testing the env var, not whatever's in `.env`.

- [ ] **Step (c.2) — Subhankar runs the tests, watches them fail**

```bash
pytest tests/test_config.py -v
```

**Expected:** all 4 tests fail with `ModuleNotFoundError: No module named 'ds_agent.config'` or similar. **This is the goal of this step** — failing tests confirm the test runner is finding the tests and the code doesn't exist yet.

### 6.3 The implementation — write `config.py` to make tests pass

Now Subhankar writes `src/ds_agent/config.py`. **Hints, not solutions:**

**Hints:**

1. The right base class is `pydantic_settings.BaseSettings`. Import it.
2. Configure it to read `.env` automatically. The pydantic-settings way is:
   ```python
   from pydantic_settings import BaseSettings, SettingsConfigDict

   class Settings(BaseSettings):
       model_config = SettingsConfigDict(env_file=".env", extra="ignore")
       ...
   ```
   `extra="ignore"` means env vars not declared in `Settings` are ignored (rather than raising).
3. Pydantic Settings reads env vars **case-insensitively** by default and matches them to field names. So a field named `anthropic_api_key` automatically reads env var `ANTHROPIC_API_KEY`. Magic.
4. To make `anthropic_api_key` required (no default), just declare it with no default value.
5. For the singleton, use `functools.lru_cache(maxsize=1)`:
   ```python
   from functools import lru_cache

   @lru_cache(maxsize=1)
   def get_settings() -> Settings:
       return Settings()
   ```
6. Type hints on every field. This is the whole point.

**Stuck-mode tiers** (use only after a real attempt):

<details>
<summary>Tier 1 hint — the field signatures</summary>

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str
    anthropic_model: str = "claude-sonnet-4-6"
    duckdb_path: str = "./data/ds_agent.duckdb"
```
</details>

<details>
<summary>Tier 2 hint — full module with imports</summary>

```python
"""ds_agent.config — typed settings loaded from environment / .env."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str
    anthropic_model: str = "claude-sonnet-4-6"
    duckdb_path: str = "./data/ds_agent.duckdb"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance. First call reads env / .env."""
    return Settings()
```
</details>

- [ ] **Step (c.3) — Subhankar writes `src/ds_agent/config.py`**

- [ ] **Step (c.4) — Subhankar runs the tests, watches them pass**

```bash
pytest tests/test_config.py -v
```

**Expected:** all 4 tests pass. If any fail, paste output to Claude.

### 6.4 Reflection prompts for substep (c)

Before moving on, Subhankar should be able to answer these in plain language:

1. Why do we use `pydantic-settings` instead of just calling `os.getenv("ANTHROPIC_API_KEY")` everywhere?
2. What does `@lru_cache(maxsize=1)` actually do here, and why does this give us a singleton?
3. If a typo in the `.env` file gives the API key the wrong name, what happens with our current code? (Hint: think about whether it's caught at startup or only when an LLM call fails.)

If any answer is fuzzy, that's a sign to ask Claude before continuing.

### 6.5 Suggested commit (after substep (c))

```bash
git add src/ds_agent/config.py tests/test_config.py
git commit -m "feat(config): typed settings via pydantic-settings + tests"
```

---

## 7. Substep (d) — `llm.py` (Anthropic SDK wrapper) [Coach mode]

> **Why Coach:** This is the single most important piece of code in the whole project. Subhankar must write it themselves to internalize what an LLM call looks like.

### 7.1 The spec

A module `src/ds_agent/llm.py` that defines a class `LLMClient` with this contract:

```python
class LLMClient:
    def __init__(self, settings: Settings): ...

    def complete(
        self,
        user_message: str,
        system: str | None = None,
        max_tokens: int = 1024,
    ) -> str:
        """Send a single user message to Claude. Return the response text."""
```

**Behavior requirements:**

1. Construct an `anthropic.Anthropic` client using `settings.anthropic_api_key`.
2. `complete()` calls `client.messages.create(...)` with:
   - `model = settings.anthropic_model`
   - `max_tokens = max_tokens`
   - `system = system` (or omitted if `None`)
   - `messages = [{"role": "user", "content": user_message}]`
3. Returns the text from the first content block of the response (`response.content[0].text`).
4. If `user_message` is empty, raise `ValueError` *before* hitting the API (saves money, fails fast).
5. We do **not** add retries / streaming / token counting yet — those land in later steps.

**Custom exception:** define `LLMClientError(Exception)` and raise it (wrapping the original) when the underlying Anthropic SDK raises. This gives our code a single exception type to catch later.

### 7.2 The tests — write FIRST

Two tests:
- `test_complete_returns_text_when_mocked` — happy path with a mocked Anthropic client.
- `test_complete_rejects_empty_user_message` — fails fast on empty input.

We'll add a *third* test in substep (f) that runs the full flow against the mock, but for now these two are enough.

- [ ] **Step (d.1) — Subhankar writes `tests/test_llm.py`**

Use these signposts:

```python
# tests/test_llm.py
"""Tests for ds_agent.llm — LLMClient wrapper."""

from unittest.mock import MagicMock

import pytest

from ds_agent.config import Settings
from ds_agent.llm import LLMClient, LLMClientError


@pytest.fixture
def settings():
    """A Settings instance with a fake API key — never hits a real API."""
    return Settings(anthropic_api_key="sk-ant-test-fake", _env_file=None)


def test_complete_returns_text_when_mocked(settings, monkeypatch):
    """Given a mocked Anthropic client, complete() returns the response text."""
    fake_response = MagicMock()
    fake_response.content = [MagicMock(text="ahoy matey")]

    fake_anthropic_client = MagicMock()
    fake_anthropic_client.messages.create.return_value = fake_response

    client = LLMClient(settings)
    monkeypatch.setattr(client, "_client", fake_anthropic_client)

    result = client.complete("say hello in pirate")

    assert result == "ahoy matey"
    # Verify we called the SDK with the right shape:
    fake_anthropic_client.messages.create.assert_called_once()
    call_kwargs = fake_anthropic_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-sonnet-4-6"
    assert call_kwargs["messages"] == [{"role": "user", "content": "say hello in pirate"}]


def test_complete_rejects_empty_user_message(settings):
    """Empty user message must fail fast with ValueError, never hit the API."""
    client = LLMClient(settings)
    with pytest.raises(ValueError):
        client.complete("")
    with pytest.raises(ValueError):
        client.complete("   ")
```

**Concepts in this test file:**

- **`MagicMock`** — Python's standard library mock object. Auto-implements any attribute / method access. Used to fake the Anthropic SDK without installing or running anything.
- **`monkeypatch.setattr(client, "_client", fake_anthropic_client)`** — replaces the `_client` attribute on our instance with the fake. This requires our implementation to *store* the Anthropic client as an attribute named `_client`, which is the convention we'll follow.
- **`assert_called_once()`** + **`call_args.kwargs`** — verifying *how* we called the SDK, not just *what* came back. Catches bugs like "we forgot to pass the system prompt."

- [ ] **Step (d.2) — Run tests, watch them fail**

```bash
pytest tests/test_llm.py -v
```

Expected: 2 failures with `ModuleNotFoundError: No module named 'ds_agent.llm'`.

### 7.3 The implementation — write `llm.py`

**Hints:**

1. Imports you'll need:
   ```python
   from anthropic import Anthropic
   from .config import Settings
   ```
2. `LLMClient.__init__` stores the settings and constructs `self._client = Anthropic(api_key=settings.anthropic_api_key)`.
3. `complete()`:
   - Validate the input (empty/whitespace-only → `ValueError`).
   - Build a `kwargs` dict for `messages.create`. Include `system` only if it's not `None` — passing `system=None` to the SDK will error.
   - Wrap the SDK call in `try/except`; on error, `raise LLMClientError("...") from e`.
   - Return `response.content[0].text`.
4. Define `class LLMClientError(Exception): pass` at module top.

**Stuck-mode tiers:**

<details>
<summary>Tier 1 — function skeleton</summary>

```python
def complete(self, user_message: str, system: str | None = None, max_tokens: int = 1024) -> str:
    if not user_message.strip():
        raise ValueError("user_message must not be empty")

    kwargs = {
        "model": self._settings.anthropic_model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": user_message}],
    }
    if system is not None:
        kwargs["system"] = system

    try:
        response = self._client.messages.create(**kwargs)
    except Exception as e:
        raise LLMClientError(f"Anthropic API call failed: {e}") from e

    return response.content[0].text
```
</details>

<details>
<summary>Tier 2 — full module</summary>

```python
"""ds_agent.llm — thin wrapper around the Anthropic SDK."""
from __future__ import annotations

from anthropic import Anthropic

from .config import Settings


class LLMClientError(Exception):
    """Raised when the underlying Anthropic SDK errors."""


class LLMClient:
    """Single chokepoint for every Claude API call.

    Why a wrapper: tracing, testing, future provider swaps all benefit from
    one place to instrument LLM calls.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = Anthropic(api_key=settings.anthropic_api_key)

    def complete(
        self,
        user_message: str,
        system: str | None = None,
        max_tokens: int = 1024,
    ) -> str:
        if not user_message.strip():
            raise ValueError("user_message must not be empty")

        kwargs: dict = {
            "model": self._settings.anthropic_model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": user_message}],
        }
        if system is not None:
            kwargs["system"] = system

        try:
            response = self._client.messages.create(**kwargs)
        except Exception as e:
            raise LLMClientError(f"Anthropic API call failed: {e}") from e

        return response.content[0].text
```
</details>

- [ ] **Step (d.3) — Subhankar writes `src/ds_agent/llm.py`**

- [ ] **Step (d.4) — Run tests, watch them pass**

```bash
pytest tests/test_llm.py -v
```

Expected: 2 passes. If failures, paste output to Claude.

### 7.4 Reflection prompts for substep (d)

1. Why do we put the Anthropic client construction in `__init__` rather than recreating it inside `complete()`?
2. Why does `complete()` reject empty input *before* calling the SDK, rather than letting the SDK reject it?
3. The test patches `client._client` (the underscore-prefix attribute) instead of patching the `Anthropic` class globally. What's the tradeoff between these two ways of mocking?

### 7.5 Suggested commit (after substep (d))

```bash
git add src/ds_agent/llm.py tests/test_llm.py
git commit -m "feat(llm): LLMClient wrapper around Anthropic SDK + mocked tests"
```

---

## 8. Substep (e) — `cli.py` Typer wiring [Tutor mode]

> **Why Tutor:** Boring CLI glue. One demo of the pattern is enough.

### 8.1 What Claude does

- [ ] **Step (e.1) — Claude writes `src/ds_agent/cli.py`**

```python
"""ds_agent.cli — Typer-based command-line interface."""
from __future__ import annotations

import typer
from rich.console import Console

from .config import get_settings
from .llm import LLMClient, LLMClientError

app = typer.Typer(
    name="ds-agent",
    help="Data Science Agent — natural-language Q&A over the Olist dataset.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def ask(
    question: str = typer.Argument(..., help="Plain-English question for the agent."),
) -> None:
    """Send a one-shot question to Claude (Step 1 — no tools yet)."""
    settings = get_settings()
    client = LLMClient(settings)

    try:
        answer = client.complete(question)
    except LLMClientError as e:
        console.print(f"[red]LLM error:[/red] {e}")
        raise typer.Exit(code=1)

    console.print(f"[bold green]Answer:[/bold green] {answer}")
```

**Why each piece:**

- **`typer.Typer(...)`** — creates the CLI app. `no_args_is_help=True` shows help when you run `ds-agent` with no args.
- **`@app.command()`** — registers `ask` as a subcommand. Typer infers types and help text from the function signature + docstring.
- **`typer.Argument(...)`** — positional argument; the `...` means required.
- **`Console`** from `rich` — pretty terminal output (colors, formatting). The `[red]` and `[bold green]` are Rich markup.
- **`raise typer.Exit(code=1)`** — exits with status 1 on error, which Unix tools interpret as "this command failed."
- **No tool use, no agent loop yet** — those arrive in Steps 3 and 4. This is just "user message → LLM → answer."

- [ ] **Step (e.2) — Claude writes `src/ds_agent/__main__.py`**

```python
"""Entrypoint for `python -m ds_agent`."""
from .cli import app

if __name__ == "__main__":
    app()
```

This makes `python -m ds_agent ask "..."` work in addition to the installed `ds-agent` command. Useful for environments where the script entrypoint isn't picked up.

### 8.2 What Subhankar does — first real Claude call

- [ ] **Step (e.3) — Run the CLI for the first time**

```bash
conda activate ds-agent
ds-agent --help                      # should show the `ask` command
ds-agent ask "what model are you?"   # FIRST REAL API CALL
```

**Expected:** a few seconds of latency, then a colored "Answer: ..." line printed. **This is your first agentic-AI-project moment.** Save the response text mentally — when we add tracing in Step 6, this exact call will become inspectable.

If you get an authentication error: check `.env` has the right key, conda env is activated, no quotes around the key value.

### 8.3 Reflection prompt for substep (e)

After the first call works:
1. Approximately how many seconds did the call take? Where do you think most of that time was spent — your machine, the network, or Anthropic's servers?
2. Look at the Anthropic console (https://console.anthropic.com/usage). How much did this call cost? Try to find the input + output token counts.

These reflections matter because Step 7 (evals) and Iter F (cost control) build on cost/latency awareness.

### 8.4 Suggested commit (after substep (e))

```bash
git add src/ds_agent/cli.py src/ds_agent/__main__.py
git commit -m "feat(cli): typer CLI with one 'ask' command"
```

---

## 9. Substep (f) — `conftest.py` + an integration-shaped test [Coach mode]

> **Why Coach:** Writing testable LLM code is its own skill. Sharing fixtures across tests is also a real production pattern.

### 9.1 The spec

Create `tests/conftest.py` with two reusable fixtures:

1. **`fake_settings`** — a `Settings` instance with a fake API key, no `.env` loading.
2. **`mock_llm_client`** — a `MagicMock`-based fake `LLMClient` that returns pre-set responses.

Then add **one** integration-shaped test in `test_llm.py`:

3. **`test_complete_passes_system_prompt_when_provided`** — verifies that when `complete(system="...")` is called, the SDK call gets `system="..."` in its kwargs.

### 9.2 Why `conftest.py` is the right home for fixtures

`conftest.py` is auto-discovered by pytest. Fixtures defined there are available to every test in the same directory (and subdirectories) **without imports**. This is the standard place to share fixtures across multiple test files.

We're putting `fake_settings` and `mock_llm_client` here because every future test (`test_tools.py`, `test_agent_loop.py`, etc.) will want them — extracting them now saves duplication later.

### 9.3 Hints

For `fake_settings`:

```python
@pytest.fixture
def fake_settings() -> Settings:
    return Settings(anthropic_api_key="sk-ant-test-fake", _env_file=None)
```

For `mock_llm_client`, return a `MagicMock(spec=LLMClient)` so it presents the same interface as the real one but lets you set `.complete.return_value`. `spec=` makes the mock reject calls to methods that don't exist on the real class — catches typos.

For the system-prompt test: use the same mocking pattern as in `test_complete_returns_text_when_mocked`, but pass `system="be terse"` to `complete()` and assert it shows up in the SDK call kwargs.

### 9.4 Steps

- [ ] **Step (f.1) — Subhankar writes `tests/conftest.py`**

<details>
<summary>Tier-1 hint — the file</summary>

```python
"""Shared pytest fixtures for the ds_agent test suite."""
from unittest.mock import MagicMock

import pytest

from ds_agent.config import Settings
from ds_agent.llm import LLMClient


@pytest.fixture
def fake_settings() -> Settings:
    """Settings with a fake API key, never reads .env."""
    return Settings(anthropic_api_key="sk-ant-test-fake", _env_file=None)


@pytest.fixture
def mock_llm_client() -> MagicMock:
    """A MagicMock pretending to be LLMClient. Set .complete.return_value as needed."""
    mock = MagicMock(spec=LLMClient)
    mock.complete.return_value = "default mock response"
    return mock
```
</details>

- [ ] **Step (f.2) — Subhankar adds the third test to `test_llm.py`**

<details>
<summary>Tier-1 hint — the test</summary>

```python
def test_complete_passes_system_prompt_when_provided(fake_settings, monkeypatch):
    """When complete(system='...') is called, system shows up in SDK kwargs."""
    fake_response = MagicMock()
    fake_response.content = [MagicMock(text="ok")]

    fake_anthropic_client = MagicMock()
    fake_anthropic_client.messages.create.return_value = fake_response

    client = LLMClient(fake_settings)
    monkeypatch.setattr(client, "_client", fake_anthropic_client)

    client.complete("hello", system="be terse")

    call_kwargs = fake_anthropic_client.messages.create.call_args.kwargs
    assert call_kwargs["system"] == "be terse"
```
</details>

Note: this test uses the new shared `fake_settings` fixture instead of redefining one in `test_llm.py`. If Subhankar wrote the earlier `settings` fixture in `test_llm.py` directly, now is a good time to delete it and use `fake_settings` from conftest.

- [ ] **Step (f.3) — Run the full test suite**

```bash
pytest -v
```

**Expected:** all tests across `test_config.py` and `test_llm.py` pass. Should be 7 tests total (4 config + 2 original llm + 1 new llm).

### 9.5 Reflection prompts for substep (f)

1. Why does `MagicMock(spec=LLMClient)` make the mock safer than plain `MagicMock()`?
2. What's the difference between a fixture in `conftest.py` and one defined inside a test file? When would you choose one over the other?
3. We have unit tests but **zero tests that actually call Claude.** What kind of bug would slip past our pytest suite? (This question motivates Step 7 — evals.)

### 9.6 Suggested commit (after substep (f))

```bash
git add tests/conftest.py tests/test_llm.py
git commit -m "test: shared fixtures + system-prompt coverage"
```

---

## 10. Final verification — the done definition

Run all four checks from [Section 2](#2-goal-the-done-definition):

- [ ] **Final check 1** — `conda activate ds-agent` works and `python --version` shows 3.12.x
- [ ] **Final check 2** — `pytest -v` passes all tests
- [ ] **Final check 3** — `ds-agent ask "what is your model name?"` prints a real Claude response
- [ ] **Final check 4** — `git status --ignored` shows `.env` in the ignored list (proving it's gitignored, not just untracked)

If any of these fail, paste the failing output to Claude before declaring Lesson 1 done.

---

## 11. Reflection — end-of-lesson questions

Subhankar should be able to answer all of these in plain language. If any are fuzzy, ask Claude.

1. **The agent loop teaser:** today we sent one user message and got one answer. In Lesson 4 we'll loop. What part of today's code do you think will be replaced by the loop, and what will stay?
2. **Why a wrapper:** we wrote `LLMClient` instead of calling `Anthropic` directly from `cli.py`. Imagine we're in Step 6 (tracing). What does the wrapper let us do that direct calls would not?
3. **Tests vs evals:** today's tests use a mocked LLM. They prove `complete()` *transforms inputs and outputs correctly*. They do **not** prove "Claude gives good answers." Why are these two different things, and why do we need both eventually?
4. **Cost awareness:** roughly how much did your `ds-agent ask` call cost? At that price, how many calls could you make for $5?

---

## 12. Connects to Lesson 2

Lesson 2 (Olist data + DuckDB) introduces the *data layer* the agent will eventually reason over. Concretely:

- Today we built `LLMClient.complete(user_message)`.
- Lesson 2 gives us `db.query(sql) -> rows`.
- Lesson 3 (tool use) connects them: the LLM can ask our code to run SQL.

The `Settings.duckdb_path` field we set today is what Lesson 2 will use. The `LLMClient` we built today is what Lesson 3 will plug a tool-use mechanism into.

---

## 13. Mode summary for this lesson

| Substep | Mode | Why | Estimated time |
|---|---|---|---|
| (a) Conda + `.env` setup | Tutor | Mechanical config, see-it-once | 15 min |
| (b) `pyproject.toml` + scaffolding | Tutor | Industry-standard layout, see-it-once | 15 min |
| (c) `config.py` + tests | **Coach** | First real Python code; Pydantic Settings is a real pattern | 25 min |
| (d) `llm.py` + tests | **Coach** | Most foundational code in the project | 35 min |
| (e) `cli.py` Typer wiring | Tutor | Boring CLI glue; first real Claude call | 10 min |
| (f) `conftest.py` + integration test | **Coach** | Shared fixtures + assertion patterns | 20 min |

Total: ~2 hours actual work + reflection time.
