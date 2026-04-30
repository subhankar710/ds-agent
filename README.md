# ds-agent

A learning-first Data Science Agent — answers natural-language questions over the Olist dataset using Claude + DuckDB.

## Setup (one-time)

1. Install [Miniconda](https://docs.conda.io/en/latest/miniconda.html).
2. Get an Anthropic API key from <https://console.anthropic.com>.
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
