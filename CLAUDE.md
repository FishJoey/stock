# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run tests
.venv/bin/python3 -m pytest tests/ -v

# Run single test file
.venv/bin/python3 -m pytest tests/test_technical.py -v

# Run single test
.venv/bin/python3 -m pytest tests/test_strategy.py::TestBacktest::test_ma_cross_backtest -v

# Initialize database (fetches stock list + demo K-lines)
.venv/bin/python3 scripts/init_db.py

# Batch fetch K-line data (optional limit arg)
.venv/bin/python3 scripts/fetch_all.py 100

# Start web app
streamlit run src/stock/web/app.py

# Install dependencies (uv is at ~/.local/bin/uv)
~/.local/bin/uv pip install --python .venv/bin/python3 -e ".[dev,ai]"
```

## Architecture

A股综合分析平台 — Chinese A-stock analysis platform built with Python + Streamlit + DuckDB.

### Data Layer (`src/stock/data/`)
Adapter pattern: `DataProvider` abstract base → `AKShareProvider` implementation. AKShare accesses 东方财富 APIs which require IPv4-only connections (IPv6 is broken) and proxy clearing. The `@retry()` decorator handles both. `Storage` wraps DuckDB for persistence with upsert semantics.

### Analysis (`src/stock/analysis/`)
Technical indicators are pure functions `(DataFrame) -> DataFrame` that add columns. Fundamental analysis computes valuation/profitability/growth metrics. `screener.py` applies `FilterCondition` chains to DataFrames.

### Strategy (`src/stock/strategy/`)
`Strategy.generate_signals(df) -> Series` returns 1 (buy) / -1 (sell) / 0 (hold). `backtest()` enforces A-stock rules: T+1 execution, 万2.5 commission (min 5 yuan), 千0.5 stamp tax (sell only), slippage, and 涨跌停 limits.

### LLM (`src/stock/llm.py`)
Unified `chat(prompt, system)` interface supporting 5 providers (Claude/通义千问/DeepSeek/智谱GLM/OpenAI). Provider is set via `LLM_PROVIDER` env var. 通义千问/DeepSeek/智谱 all use OpenAI-compatible API with different `base_url`. Used by `ai_report.py` (intelligent reports) and `nl_screener.py` (natural language stock screening).

### Web (`src/stock/web/`)
Streamlit multi-page app. Pages are numbered files in `pages/` (1-6). Each page does `sys.path.insert` to find `src/stock`. K-line charts use red-up/green-down (A-stock convention).

## A-Stock Domain Rules

- T+1: signal on day N → execute at day N+1 open
- Price limits: 10% main board, 20% ChiNext/STAR, 5% ST stocks
- Commission: 0.025% both ways, minimum 5 yuan
- Stamp tax: 0.05% sell-side only
- Stock codes: 6xx=SH main, 688=STAR, 000/002=SZ, 300=ChiNext
- KDJ uses (9,3,3) parameters (Chinese market standard, differs from Western Stochastic)
- Always store raw (unadjusted) prices; compute 前复权/后复权 on the fly
