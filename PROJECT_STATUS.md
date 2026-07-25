# PROJECT STATUS

## Last Updated
2026-07-25 (Session 3 — Frontend fixes, persistence, snapshots, docs)

## Phase Status: ALL PHASES COMPLETE + VERIFIED

### Phase 0 — Foundation + Authentication ✅
- JWT auth (access/refresh), bcrypt hashing
- Register, login, refresh, /users/me
- User A cannot access User B resources

### Phase 1 — Market Data + Watchlists + Portfolio ✅
- DatabaseMarketDataProvider with PostgreSQL
- MockMarketDataProvider fallback when DB empty
- 10 instruments + 2610 OHLCV rows seeded
- Watchlist CRUD with ownership enforcement
- Paper BUY/SELL with validation + weighted average price

### Phase 2 — Technical Analysis + Signals ✅
- SMA, EMA, RSI, MACD, Bollinger Bands, ATR, Volume SMA
- Rule-based signal engine with confidence
- Plain-language explanations from actual feature values

### Phase 3 — Backtesting ✅
- Walk-forward backtest engine
- Sharpe, Sortino, max drawdown, equity curve

### Phase 4 — Risk + Alerts ✅
- Position/sector concentration, position sizing
- Alert types: PRICE_ABOVE, PRICE_BELOW, SIGNAL_BUY, SIGNAL_SELL

### Phase 5 — Integration ✅
- Docker Compose: 6 services (postgres, redis, backend, worker, frontend, nginx)
- Data persistence verified across `docker compose down` + `docker compose up`
- Portfolio snapshots model + API endpoint
- CSV export: transactions + snapshots
- 30-day test plan + testing log template

## Bugs Fixed (Session 3)

1. **₹$ typo in dashboard/portfolio page** — Fixed `₹$` double-prefix on prices
2. **Markets page showing empty/crashing** — Rewrote with proper error handling, SIMULATED DATA label, and improved grid layout
3. **Analysis page unstable** — Added debounced search, quick-select presets, loading guards, empty chart state handling
4. **Portfolio page improvements** — Added PAPER TRADING badge, success messages for trades, validation for zero/negative inputs, improved transaction table
5. **Dashboard improvements** — PAPER TRADING badge, watchlist summary, improved empty states
6. **Backtest page** — Proper error states, SIMULATED label, trade result validation
7. **Alerts page** — Symbol suggestions dropdown, success/error messages

## New Features (Session 3)

1. **PortfolioSnapshot model** — `portfolio_snapshots` table storing equity, cash, invested, market value, P&L per snapshot
2. **POST /portfolio/{id}/snapshot** — Creates daily snapshot
3. **GET /portfolio/{id}/snapshots** — Lists all snapshots
4. **GET /portfolio/{id}/export** — CSV export of transactions + snapshots

## Commands Verified

| Command | Result |
|---------|--------|
| `docker compose build backend` | ✅ Pass |
| `docker run --rm sv-ai-trading-backend pytest -v` | **50 passed, 0 failed** |
| `docker compose build frontend` | ✅ Pass (13 routes, TypeScript OK) |
| `docker compose down && docker compose up -d` | ✅ All 6 healthy, data persisted |
| `http://localhost/api/health` | ✅ 200 OK |
| `http://localhost:8000/health` | ✅ 200 OK |
| `http://localhost:3000/` | ✅ 200 OK |
| `http://localhost/` | ✅ 200 OK |

## PostgreSQL Verification
- 5 users, 2 portfolios, 2 watchlists, 1 alert — all survived stop/start cycles
- Volume not deleted during normal `docker compose down`

## Known Limitations
- Mock market data (simulated, not live)
- Broker adapter is read-only (order execution disabled)
- Signal engine is rule-based, not ML
- Backend uses `Base.metadata.create_all()` on startup (production should use `alembic upgrade head`)
