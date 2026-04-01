<p align="center">
  <img src="src-frontend/logo.png" alt="Fortuna" width="180" />
</p>

<h1 align="center">Fortuna</h1>

<p align="center">
  A personal ASX portfolio tracker desktop app with AI-powered stock analysis, technical charting, dividend tracking, and rebalancing.
</p>

<p align="center">
  <strong>Tauri v2</strong> &nbsp;·&nbsp; <strong>Streamlit</strong> &nbsp;·&nbsp; <strong>SQLite</strong> &nbsp;·&nbsp; <strong>Python 3.14</strong>
</p>

---

## Features

- **Portfolio Dashboard** — Live ASX prices, P&L tracking, weight deviation from targets
- **Transaction Management** — Record buy/sell orders with broker fee tracking
- **AI Analysis** — Multi-provider support (Claude, OpenAI, Gemini) for stock research and insights
- **Technical Charts** — Interactive Plotly charts with MA, RSI, MACD, Bollinger Bands
- **Dividend Tracking** — Historical dividend data and yield calculations via Yahoo Finance
- **Portfolio Planner** — Target weight allocation with rebalancing suggestions
- **Desktop App** — Native macOS (.dmg) and Windows (.exe) installers — no Python required for end users
- **Dark + Gold Theme** — Consistent `#D4AF37` accent across all UI components and charts

## Getting Started

### Prerequisites

- Python 3.14+
- pip

### Setup

```bash
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

pip install -r requirements.txt
```

### Run

```bash
streamlit run app.py
```

Opens at [http://localhost:8501](http://localhost:8501).

### Configuration

AI provider API keys are configured in the **Settings** page within the app — no environment variables needed. Keys are encrypted at rest in the local SQLite database using Fernet symmetric encryption.

The database is stored in the OS app data directory (`~/Library/Application Support/Fortuna/fortuna.db` on macOS). Override for development:

```bash
DB_PATH=./fortuna.db streamlit run app.py
```

## Building the Desktop App

The desktop app wraps Streamlit in a native window using [Tauri v2](https://v2.tauri.app/). End users get a one-click installer — no Python or terminal required.

### How It Works

```
User launches Fortuna.app
  → Tauri (Rust) finds a free port, spawns PyInstaller sidecar
  → Sidecar starts Streamlit on 127.0.0.1:<port>
  → Stage-aware splash screen shows boot progress
  → Webview navigates to the Streamlit URL
  → On quit, Tauri kills the sidecar process tree
```

### Prerequisites

- Python 3.14+ with venv
- [Rust](https://rustup.rs/)
- [Node.js](https://nodejs.org/) 18+
- Xcode Command Line Tools (macOS): `xcode-select --install`

### Build

```bash
# Python dependencies + PyInstaller
source venv/bin/activate
pip install -r requirements.txt pyinstaller

# Node dependencies (Tauri CLI)
npm install

# Build the sidecar (PyInstaller bundle)
python scripts/build_sidecar.py

# Dev mode (hot-reloads Rust changes)
npx tauri dev

# Production build — .dmg (macOS) or .exe (Windows)
npx tauri build
```

Output: `src-tauri/target/release/bundle/dmg/Fortuna_<version>_<arch>.dmg`

### Code Signing (macOS)

For distribution outside the App Store, set these environment variables before building:

```bash
export APPLE_SIGNING_IDENTITY="Developer ID Application: Your Name (TEAM_ID)"
export APPLE_CERTIFICATE="base64-encoded-p12"
export APPLE_CERTIFICATE_PASSWORD="password"
export APPLE_ID="your@email.com"
export APPLE_TEAM_ID="TEAM_ID"
```

Without code signing, the .dmg works but users will see a Gatekeeper warning on first launch.

## Project Structure

```
fortuna/
├── app.py                  # Streamlit entry point, CSS theming, nav routing
├── database.py             # SQLite layer — schema, CRUD, migrations, encryption
├── ai_engine.py            # Provider-agnostic AI dispatch (Claude, OpenAI, Gemini)
├── market_data.py          # Yahoo Finance wrapper for ASX prices and fundamentals
├── charts.py               # Plotly charts — candlestick, MA, RSI, MACD, Bollinger
├── views/                  # Streamlit pages (thin UI shells)
│   ├── portfolio.py        # Portfolio dashboard
│   ├── transactions.py     # Buy/sell management
│   ├── analysis.py         # AI analysis with technical charts
│   ├── dividends.py        # Dividend tracking
│   ├── planner.py          # Target allocation and rebalancing
│   ├── settings.py         # AI provider configuration
│   └── logs.py             # Application logs
├── services/               # Business logic extracted from views
│   ├── portfolio.py        # Portfolio row computation
│   ├── analysis.py         # Analysis data gathering
│   ├── dividends.py        # Dividend calculations
│   └── planner.py          # Planner computations
├── scripts/
│   ├── fortuna_launcher.py # PyInstaller entry point (parallel DB init)
│   └── build_sidecar.py    # Sidecar build automation
├── src-tauri/              # Tauri v2 desktop shell (Rust)
│   ├── src/main.rs         # Sidecar lifecycle, port discovery, health polling
│   ├── tauri.conf.json     # Window, bundle, and DMG configuration
│   └── icons/              # App icons (all platforms)
├── src-frontend/
│   ├── index.html          # Stage-aware splash screen
│   └── logo.png            # App logo
├── .streamlit/config.toml  # Streamlit theme (dark + gold)
├── requirements.txt        # Python dependencies
└── package.json            # Node/Tauri CLI dependencies
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| UI | Streamlit with custom CSS theming |
| Desktop Shell | Tauri v2 (Rust + native webview) |
| Database | SQLite with WAL mode |
| Market Data | Yahoo Finance via yfinance |
| AI Providers | Claude, OpenAI, Gemini |
| Charts | Plotly with custom `fortuna_theme` template |
| Bundler | PyInstaller (onedir mode) |
| Installers | DMG (macOS), NSIS (Windows) |

## License

MIT License -- Copyright (c) 2026 Erick

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files, to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, subject to the conditions of the [MIT License](https://opensource.org/licenses/MIT).
