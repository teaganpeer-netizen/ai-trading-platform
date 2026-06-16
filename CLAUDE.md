# AI Trading Platform - Personal Hedge Fund Project

**Project Vision:** Build a production-grade personal hedge fund that autonomously discovers, analyzes, executes, and reports on trades with institutional-quality risk management.

**Current Status:** Phase 2 - Quant Enhancement & Tax Tracking

---

## Phase 1: Foundation (✅ COMPLETE)
- [x] Data layer (YFinance, SQLite)
- [x] 8+ technical indicators
- [x] Risk management (2% position sizing, circuit breaker)
- [x] Paper trading engine
- [x] Alpaca integration (ready)
- [x] Web dashboard
- [x] Interactive CLI
- [x] 6 MCPs (news, economics, options, breadth, earnings, sentiment)
- [x] Market scanner (auto-discovery)
- [x] Enhanced trading logic (dynamic stops, exits)

## Phase 2: Quant Enhancement & Tax Tracking (🔄 IN PROGRESS - Session: 2026-06-16)

### Today's Work (Option B - Hybrid)

**Building Now:**
1. **Tax Tracking Module** - Track short/long-term gains, calculate tax liability, generate reports
2. **Quant Analyzer** - Correlation/cointegration detection, regime detection, portfolio metrics
3. **ML Skeleton** - Random forest pipeline ready for historical data training

**Saving for Future:**
- Advanced ML models (need 3-6 months live data)
- Portfolio optimization (Markowitz, efficient frontier)
- Factor analysis (Fama-French)
- Greeks & options modeling
- Multi-asset class support

### Architecture Decisions

**Tax Tracking:**
- Track entry/exit prices, dates, holding periods
- Calculate short-term (< 1 year) vs long-term (≥ 1 year) gains
- Generate tax reports per asset, per year
- Export for Form 8949
- Persist in database

**Quant Analyzer:**
- Correlation matrix detection (find correlated trades)
- Cointegration testing (find mean-revert pairs)
- Regime detection (bull/bear/sideways states)
- Portfolio concentration metrics
- Sharpe ratio, max drawdown tracking

**ML Skeleton:**
- Random forest regression for price prediction
- Feature engineering (technicals → ML features)
- Train/test split on historical data
- Continuous learning pipeline
- Prediction confidence scoring

---

## Phase 3: Hedge Fund Features (🔄 FUTURE)

### Short-term (Next 3-6 months of live trading)
- ML model training on real trade data
- Portfolio optimization across positions
- Correlation-based position sizing
- Regime-aware strategy switching
- Performance attribution (what's making $$$)

### Medium-term (6-12 months)
- Multi-asset class support (stocks, crypto, options)
- Options Greeks modeling
- Volatility forecasting (GARCH)
- Factor exposure tracking
- Leverage optimization (with margin requirements)

### Long-term (12+ months)
- Statistical arbitrage strategies
- Smart order routing (Alpaca vs other brokers)
- Portfolio rebalancing automation
- Tax-loss harvesting automation
- Institutional-grade reporting (GIPS, risk metrics)
- Multi-manager architecture (run multiple strategies)

---

## Tech Stack

**Data:**
- YFinance (free market data)
- SQLite (local persistence)
- Pandas/NumPy (analysis)

**AI/ML:**
- Groq LLM (decisions)
- scikit-learn (ML models)
- statsmodels (quant analysis)

**Execution:**
- Alpaca API (paper + live)
- Python async (concurrent trades)

**Interface:**
- Rich CLI (beautiful terminal)
- Flask dashboard (real-time web)

**Tax/Legal:**
- SQLAlchemy ORM
- Trade journal (complete audit trail)
- Tax calculation engine

---

## File Structure for Phase 2

```
ai_engine/
├── mcp_scanner.py          # (exists) Market opportunity discovery
├── mcp_enhanced.py         # (exists) Market context MCPs
├── mcp_quant.py            # (NEW) Correlation, cointegration, regime
├── ml_engine.py            # (NEW) Random forest + prediction
└── tax_tracker.py          # (NEW) Tax obligation tracking

data/
├── storage/                # (exists) Models and repos
└── ml_models/              # (NEW) Trained models, scaler, preprocessor

cli.py                       # Update with new menu options
```

---

## Success Criteria for Phase 2

- [ ] Tax tracker calculates gains accurately
- [ ] Tax reports generate for Form 8949
- [ ] Correlation analysis detects multi-position risk
- [ ] Regime detection identifies market state
- [ ] ML model trains on historical data
- [ ] Predictions integrate into trade analysis
- [ ] All components tested and working
- [ ] CLI updated with new features
- [ ] Memory updated with hedge fund roadmap

---

## Key Decisions to Make (Future)

1. **Multi-asset support** — Add crypto, options, bonds?
2. **Leverage strategy** — Use margin for higher returns?
3. **Rebalancing frequency** — Daily, weekly, monthly?
4. **ML model complexity** — Random forest vs deep learning?
5. **Strategy composition** — Multiple independent systems or one unified?

---

## Important Notes

- Keep focus on **reliability** over sophistication
- Every feature must be **backtested thoroughly**
- Tax tracking must be **100% accurate** (audit-ready)
- Paper trading for **6+ months before any live trading**
- Build hedge fund **incrementally**, not all at once
- User remains in **full control** (no black-box decisions)

---

## Contacts & References

- **Tax Rules**: https://www.irs.gov/forms/about-form-8949
- **Alpaca Docs**: https://docs.alpaca.markets
- **Quant Resources**: Quantopian's lectures, MIT OpenCourseWare

---

**Last Updated:** 2026-06-16  
**Next Review:** When Phase 2 complete
