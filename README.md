# AI Trading Platform

A production-quality AI-assisted trading platform built with Python, Claude AI, and the Alpaca Markets API.

## Architecture Overview

```
[ Data Layer ] → [ Strategy Signals ] → [ AI Decision Engine ] → [ Risk Management ] → [ Execution ]
                                                  ↑
                                       [ Trade Memory / Journal ]
```

## Project Status

| Phase | Status |
|---|---|
| Architecture & Repository | ✅ Complete |
| Environment Setup | 🔄 In Progress |
| Data Layer | ⬜ Pending |
| Backtesting Framework | ⬜ Pending |
| Risk Management | ⬜ Pending |
| Strategy Engines | ⬜ Pending |
| AI Decision Engine | ⬜ Pending |
| Trade Memory System | ⬜ Pending |
| Paper Trading | ⬜ Pending |
| Live Trading | ⬜ Pending |

## Quick Start

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd ai-trading-platform

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Mac/Linux
# venv\Scripts\activate   # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 5. Run a recommendation (once data layer is built)
python scripts/run_recommendation.py --symbol AAPL
```

## Project Structure

```
ai-trading-platform/
├── config/          # Settings and logging configuration
├── data/            # Data collectors, processors, and storage
├── strategies/      # Independent strategy engines
├── ai_engine/       # Claude-powered decision engine
├── risk/            # Risk management and circuit breakers
├── execution/       # Alpaca order execution
├── memory/          # Trade memory database
├── journal/         # Trade journal and reporting
├── backtesting/     # Historical simulation framework
├── tests/           # Unit and integration tests
└── scripts/         # Entry point scripts
```

## Design Principles

- **Modular**: Every component is independently replaceable
- **Auditable**: Every AI decision is logged with full reasoning
- **Safe**: Risk management has veto power over all AI decisions
- **Testable**: Every module has corresponding unit tests

## ⚠️ Risk Disclaimer

This software is for educational and research purposes. Paper trade extensively before considering any live trading. Past performance does not guarantee future results. Never risk money you cannot afford to lose.
