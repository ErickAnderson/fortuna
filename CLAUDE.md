<!-- GSD:project-start source:PROJECT.md -->
## Project

**Fortuna — Polish Pass**

Fortuna is a personal ASX portfolio tracker desktop app (Tauri v2 + Streamlit + SQLite) with AI-powered stock analysis, technical charting, dividend tracking, and rebalancing. This milestone focuses on cleaning up the codebase and polishing the visual experience — no new features.

**Core Value:** The code should be clean enough to confidently change, and the app should look and feel like a credible financial tool — not a prototype.

### Constraints

- **Framework**: Streamlit + Tauri v2 — not changing the stack
- **Scope**: Polish pass only — fix what's there, don't add capabilities
- **Theme**: Keep dark + gold (#D4AF37), refine don't redesign
- **Desktop**: macOS DMG is the primary target
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3.14 - Core application logic, UI, data processing, AI engine (`app.py`, `database.py`, `ai_engine.py`, `market_data.py`, `charts.py`, `views/`)
- Rust (Edition 2021) - Tauri desktop shell (`src-tauri/src/main.rs`, `src-tauri/src/lib.rs`)
- TypeScript/JavaScript - Minimal Tauri frontend glue (`src-frontend/`, `package.json`)
## Runtime
- Python 3.14.3 (managed via `venv/`)
- Node.js - Required for Tauri CLI tooling only
- pip with `venv` for Python dependencies
- npm for Node/Tauri toolchain
- Lockfile: `package-lock.json` present; no `requirements.lock` (Python uses version-bounded `requirements.txt`)
## Frameworks
- Streamlit >=1.45.0 - Entire UI layer, page routing, session state, data display (`app.py`, all `views/`)
- Tauri v2 - Native desktop wrapper that spawns Streamlit as a sidecar process (`src-tauri/`)
- pandas >=2.2.0 - DataFrame manipulation, portfolio calculations, price history
- Plotly >=6.0.0 - Interactive charts; candlestick + technical indicator charts (`charts.py`)
- PyInstaller - Bundles Python app into a sidecar binary (`scripts/build_sidecar.py`)
- `@tauri-apps/cli` ^2 - Desktop build toolchain (`package.json`)
## Key Dependencies
- `streamlit>=1.45.0` - All UI rendering; removing it breaks the entire app
- `yfinance>=0.2.50` - Only market data source; ASX price feeds, fundamentals, dividends (`market_data.py`)
- `python-dotenv>=1.1.0` - Reads `.env` for AI provider config fallback (`ai_engine.py`, `database.py`)
- `cryptography` (implicit, used in `database.py`) - Fernet symmetric encryption for API keys stored in SQLite
- `platformdirs>=4.0.0` - Resolves OS-standard user data directory for the SQLite DB path (`database.py`, `scripts/fortuna_launcher.py`)
- `sqlite3` (stdlib) - Database engine; no ORM, raw SQL via `sqlite3` module (`database.py`)
- `anthropic>=0.52.0` - Claude API integration
- `openai>=1.82.0` - OpenAI/ChatGPT integration
- `google-genai>=1.0.0` - Google Gemini integration
- `tauri = "2"` - Desktop shell framework
- `tauri-plugin-opener = "2"` - Opens URLs externally
- `serde = "1"` + `serde_json = "1"` - JSON serialization
- `libc = "0.2"` - POSIX process group signals (SIGTERM/SIGKILL for sidecar cleanup)
## Configuration
- `.env` file (gitignored) — Optional AI provider fallback: `AI_PROVIDER`, `AI_API_KEY`, `AI_MODEL`, `DB_PATH`
- `.streamlit/config.toml` — Theme (dark mode, gold `#D4AF37` accent), `server.headless = true`
- AI provider API keys are primarily stored in SQLite (encrypted at rest with Fernet), with `.env` as fallback
- `src-tauri/tauri.conf.json` — Desktop app configuration: window sizing (1280x800 min 900x600), bundle targets (dmg + nsis), sidecar resource paths
- `package.json` — Defines `build:sidecar` and `tauri` NPM scripts
- `scripts/build_sidecar.py` — PyInstaller invocation; excludes pyarrow, PIL, scipy, matplotlib to reduce DMG size
## Platform Requirements
- Python 3.14 + venv
- Node.js (for Tauri CLI: `npm install`, `npm run tauri:dev`)
- Rust toolchain (for Tauri compilation)
- Run directly without Tauri: `streamlit run app.py`
- macOS: `.dmg` installer (signed identity not configured; `signingIdentity: null`)
- Windows: `.nsis` installer (current-user install mode)
- Architecture: Supports `x86_64` and `aarch64` (Apple Silicon) via Rust target triples
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Naming Patterns
- Module-level Python files use `snake_case`: `ai_engine.py`, `market_data.py`, `database.py`
- View files are named after the page they render: `views/portfolio.py`, `views/transactions.py`
- Rust files follow standard Rust conventions: `main.rs`, `lib.rs`
- Public functions use `snake_case`: `get_portfolio_summary()`, `add_transaction()`, `render()`
- Private/internal helpers are prefixed with a single underscore: `_get_config()`, `_asx_ticker()`, `_render_buy_form()`, `_friendly_error()`
- Database CRUD helpers follow a consistent verb pattern: `get_*`, `add_*`, `update_*`, `delete_*`, `upsert_*`
- View helper functions (private) are prefixed `_render_*`: `_render_add_position()`, `_render_edit_form()`
- `snake_case` throughout Python and Rust code
- Underscored state keys prefix with `_` for "private" session_state: `_buy_last_ticker`, `_sell_last_ticker`
- `UPPER_SNAKE_CASE`: `ASX_SUFFIX`, `NAV_ITEMS`, `PROVIDER_INFO`, `DB_PATH`
- Type hints use Python 3.10+ union syntax: `float | None`, `int | None`, `dict | None`
- Return types annotated consistently on all public functions
## Code Style
- No autoformatter config detected (no `.prettierrc`, `pyproject.toml` with black/ruff, or `biome.json`)
- Consistent 4-space indentation throughout all Python files
- Single blank lines between functions within a section; double blank lines between top-level definitions
- Section dividers with `# --- Section Name ---` comments in `database.py`
- No linting config file detected; style is maintained manually
- Type hints used consistently on function signatures
## Import Organization
- `import database as db` — used in all view files and `ai_engine.py`
- `import market_data as md` — used in view files
- `import ai_engine as ai` — used in `views/analysis.py`
## Module Docstrings
## Function Design
- Used selectively on non-obvious functions: `_default_db_path()`, `get_batch_prices()`, `_get_config()`
- Short one-liner format for simple helpers; multi-line for complex ones
- Not used on trivial CRUD functions (`get_brokers`, `delete_transaction`, etc.)
- View render functions are large by necessity (Streamlit is imperative); private `_render_*` helpers are used to decompose them
- Database functions are kept small — one responsibility per function
- Market data functions wrap `try/except` blocks to return safe defaults
- Keyword arguments used at call sites for multi-parameter DB functions:
- DB read functions return `list[dict]` (rows converted via `dict(row)`) or `dict | None` for single rows
- Market data functions return `float | None`, `pd.DataFrame`, or `dict`
- Functions never return bare `sqlite3.Row` objects — always converted to `dict`
## Error Handling
## Logging
## Streamlit Patterns
- Checked with `if "key" not in st.session_state:` before initializing
- Deleted with `del st.session_state.key` after use (e.g., clearing edit/confirm states)
- Used for navigation (`current_page`), edit state (`editing_txn_id`), and confirm dialogs (`confirm_delete_txn_id`)
## Rust Conventions
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Pattern Overview
- Rust (Tauri) shell spawns a PyInstaller-bundled Python/Streamlit sidecar on a dynamic free port
- The Tauri webview navigates to `http://127.0.0.1:<port>` after a health check — the entire UI is served by Streamlit
- All persistent state lives in a single SQLite database file at the OS-standard user data directory
- No network-facing server; the app is strictly local-only (127.0.0.1 bound)
- AI analysis calls out to external LLM APIs (Anthropic, OpenAI, Google Gemini) using provider-agnostic dispatch
## Layers
- Purpose: Native window management, process lifecycle, sidecar orchestration
- Location: `src-tauri/src/main.rs`, `src-tauri/src/lib.rs`
- Contains: Port discovery, health polling, process group management, window event handling
- Depends on: Nothing from Python layer directly — communicates only via HTTP health check
- Used by: End user launching the `.app` / `.exe`
- Purpose: Cosmetic splash shown while Rust health-checks the sidecar
- Location: `src-frontend/index.html`
- Contains: Animated spinner + progressive status text, replaces itself when Tauri navigates
- Depends on: Nothing; pure HTML/CSS/vanilla JS
- Purpose: PyInstaller frozen bundle launcher; starts Streamlit programmatically
- Location: `scripts/fortuna_launcher.py`
- Contains: Port argument handling, DB_PATH env setup, Streamlit CLI invocation
- Depends on: `database.py` (indirectly via `app.py`), `streamlit.web.cli`
- Used by: Tauri main.rs via `std::process::Command`
- Purpose: Session initialization, CSS theming, sidebar navigation routing
- Location: `app.py`
- Contains: `db.init_db()` call, `NAV_ITEMS` list, page dispatch via `st.session_state.current_page`
- Depends on: `database` module for init; `views/*` for page rendering
- Used by: `fortuna_launcher.py` via `streamlit run app.py`
- Purpose: Page-level Streamlit UI — each file is one navigation page
- Location: `views/`
- Contains: `render()` function per module, UI logic, form handling
- Depends on: `database`, `market_data`, `ai_engine`, `charts` modules
- Used by: `app.py` dispatch block
- Purpose: All SQLite persistence — schema, CRUD, migrations, portfolio calculations
- Location: `database.py`
- Contains: `init_db()`, CRUD functions per entity (brokers, positions, transactions, analyses, ai_providers, app_logs), `get_portfolio_summary()` computation, Fernet encryption for API keys
- Depends on: `sqlite3`, `cryptography`, `platformdirs`
- Used by: All views, `ai_engine.py`, `seed.py`
- Purpose: Live ASX price and fundamentals via yfinance; results cached via Streamlit
- Location: `market_data.py`
- Contains: `get_batch_prices()`, `get_stock_info()`, `get_price_history()`, `get_dividends()`, `get_dividend_yield()` — all decorated with `@st.cache_data(ttl=300)`
- Depends on: `yfinance`, `pandas`, `streamlit`
- Used by: `views/portfolio.py`, `views/transactions.py`, `views/planner.py`, `views/analysis.py`, `views/dividends.py`
- Purpose: Technical indicator computation and Plotly candlestick chart construction
- Location: `charts.py`
- Contains: `compute_indicators()` (MA20/50/200, RSI, MACD, Bollinger Bands), `get_indicator_summary()`, `get_price_summary()`, `create_candlestick_chart()`
- Depends on: `pandas`, `plotly`
- Used by: `views/analysis.py`
- Purpose: Provider-agnostic LLM dispatch, prompt construction, response parsing
- Location: `ai_engine.py`
- Contains: `build_analysis_prompt()`, `call_ai_api()`, `_call_claude()`, `_call_openai()`, `_call_gemini()`, `_parse_json_response()`, `list_models()`, `test_connection()`, `get_configured_providers()`
- Depends on: `database` (for provider config and logging), optionally `anthropic`, `openai`, `google-genai`
- Used by: `views/analysis.py`, `views/settings.py`
## Data Flow
- `views/analysis.py` also generates a copy-paste prompt block so users can run it in any LLM chat interface without an API key configured
- Page navigation state: `st.session_state.current_page`
- Market data cache: Streamlit `@st.cache_data(ttl=300)` (session-scoped, 5-minute TTL)
- No client-side state beyond Streamlit session; all truth is in SQLite
## Key Abstractions
- Purpose: Derives current holdings entirely from transaction history — no denormalized qty/cost stored
- Pattern: SQL aggregate queries over `transactions` grouped by `position_id`; returns list of dicts with computed `qty`, `avg_price`, `total_cost`, `total_fees`
- Purpose: Provider-agnostic LLM dispatch — callers do not need to know which provider is active
- Pattern: `_get_config()` resolves provider/key/model from DB with `.env` fallback; routes to `_call_claude()`, `_call_openai()`, or `_call_gemini()`
- Purpose: Single public interface for each page; called directly by `app.py`
- Pattern: Each `views/*.py` exports exactly one `render()` function; private helpers are prefixed `_render_*`
- Purpose: Encrypt AI provider keys at rest in SQLite
- Pattern: Key derived from `socket.gethostname()` via PBKDF2; keys encrypted on write via `upsert_ai_provider()`, decrypted on read via `_decrypt_provider_row()`
## Entry Points
- Location: `src-tauri/src/main.rs` → `main()`
- Triggers: User launches `Fortuna.app` or the `.exe`
- Responsibilities: Find free port, spawn sidecar, health-poll, navigate webview
- Location: `scripts/fortuna_launcher.py` → `main()`
- Triggers: Tauri `std::process::Command` with port argument
- Responsibilities: Set `DB_PATH` env var, invoke `streamlit run app.py --server.port=<port>`
- Location: `app.py`
- Triggers: `streamlit run app.py` (by launcher or directly in dev)
- Responsibilities: Init DB, configure page layout/CSS, render sidebar nav, dispatch to view
- Location: `app.py` directly via `streamlit run app.py`
- No Tauri required; browser opens on default port 8501
## Error Handling
- `ai_engine._friendly_error()`: maps HTTP status codes and exception messages to short readable strings; always writes full traceback to `db.add_log()`
- `market_data` functions: `try/except Exception: return None` or `return pd.DataFrame()` — silent fallback
- `database.py` migrations: wrapped in `try/except Exception: pass` — idempotent `ALTER TABLE` calls
- View layer: uses `st.error()`, `st.warning()`, `st.info()` for user-visible error messages
## Cross-Cutting Concerns
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
