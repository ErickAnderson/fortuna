# Fortuna

Personal ASX (Australian Securities Exchange) portfolio tracker with AI-powered stock analysis.

## Features

- **Portfolio Dashboard** — Live prices, P&L tracking, weight deviation from targets
- **Transaction Management** — Record buy/sell orders with broker fee tracking
- **AI Analysis** — Multi-provider support (Claude, OpenAI, Gemini) with real-time research
- **Technical Charts** — Interactive charts with MA, RSI, MACD, Bollinger Bands
- **Dividend Tracking** — Historical dividend data from Yahoo Finance
- **Portfolio Planner** — Target weight allocation and rebalancing suggestions

## Running with Streamlit (Development)

### Prerequisites

- Python 3.12+
- pip

### Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Optional: install AI provider SDKs
pip install anthropic openai google-genai
```

### Run

```bash
streamlit run app.py
```

Opens at [http://localhost:8501](http://localhost:8501).

### Configuration

AI provider API keys are configured in the **Settings** page within the app — no environment variables needed.

For development, you can optionally override the database path:

```bash
DB_PATH=./fortuna.db streamlit run app.py
```

By default, the database is stored in the OS app data directory (`~/Library/Application Support/Fortuna/fortuna.db` on macOS).

## Building the Desktop App

The desktop app wraps Streamlit in a native window using [Tauri v2](https://v2.tauri.app/). Non-technical users get a one-click installer (.dmg for macOS, .exe for Windows) — no Python or terminal required.

### Architecture

```
User launches Fortuna.app
  → Tauri (Rust) finds a free port, spawns PyInstaller sidecar
  → Sidecar starts Streamlit on 127.0.0.1:<port>
  → Splash screen shows while Streamlit boots (~5-10s)
  → Webview navigates to the Streamlit URL
  → On quit, Tauri kills the sidecar process tree
```

### Prerequisites

- Python 3.12+ with venv
- [Rust](https://rustup.rs/) (install via `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`)
- [Node.js](https://nodejs.org/) 18+
- Xcode Command Line Tools (macOS): `xcode-select --install`

### Setup

```bash
# Python dependencies + PyInstaller
source venv/bin/activate
pip install -r requirements.txt pyinstaller

# Node dependencies (Tauri CLI)
npm install
```

### Development

```bash
# Build the sidecar (PyInstaller bundle)
source venv/bin/activate
python scripts/build_sidecar.py

# Run in dev mode (hot-reloads Rust changes)
npx tauri dev
```

### Production Build

```bash
# Build .dmg (macOS) or .exe installer (Windows)
npx tauri build
```

Output: `src-tauri/target/release/bundle/dmg/Fortuna_<version>_<arch>.dmg`

### Code Signing (macOS)

For distribution outside the App Store, you need an Apple Developer account ($99/year). Set these environment variables before building:

```bash
export APPLE_SIGNING_IDENTITY="Developer ID Application: Your Name (TEAM_ID)"
export APPLE_CERTIFICATE="base64-encoded-p12"
export APPLE_CERTIFICATE_PASSWORD="password"
export APPLE_ID="your@email.com"
export APPLE_TEAM_ID="TEAM_ID"
```

Without code signing, the .dmg will work but users will see a Gatekeeper warning on first launch.

## Project Structure

```
fortuna/
├── app.py                  # Streamlit entry point
├── database.py             # SQLite database layer (encrypted API keys)
├── ai_engine.py            # Multi-provider AI integration
├── market_data.py          # Yahoo Finance wrapper for ASX data
├── charts.py               # Technical indicators (MA, RSI, MACD, Bollinger)
├── views/                  # Streamlit page components
│   ├── portfolio.py        # Portfolio dashboard
│   ├── transactions.py     # Buy/sell management
│   ├── analysis.py         # AI analysis with charts
│   ├── dividends.py        # Dividend tracking
│   ├── planner.py          # Portfolio planning
│   ├── settings.py         # AI provider configuration
│   └── logs.py             # Application logs
├── scripts/
│   ├── fortuna_launcher.py # PyInstaller entry point
│   └── build_sidecar.py    # Sidecar build automation
├── src-tauri/              # Tauri desktop shell (Rust)
│   ├── src/main.rs         # Sidecar lifecycle management
│   ├── tauri.conf.json     # Window & bundle configuration
│   └── icons/              # App icons (all platforms)
├── src-frontend/
│   └── index.html          # Splash screen
├── .streamlit/config.toml  # Streamlit theme (dark + gold)
├── requirements.txt        # Python dependencies
└── package.json            # Node/Tauri CLI dependencies
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Web UI | Streamlit |
| Desktop Shell | Tauri v2 (Rust + native webview) |
| Database | SQLite with WAL mode |
| Market Data | Yahoo Finance (yfinance) |
| AI Providers | Claude, OpenAI, Gemini |
| Charts | Plotly |
| Bundler | PyInstaller (onedir mode) |
| Installers | DMG (macOS), NSIS (Windows) |

## License

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT).

Copyright (c) 2026 Erick

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files, to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, subject to the conditions of the MIT License.
