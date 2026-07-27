# PROJECT STATUS

## Last Updated
2026-07-25 — V1 BASELINE FROZEN for 30-day test

## Git Commit
- Hash: `78ce6c1`
- Message: `V1 paper trading - 30 day test baseline`
- Files: 72 files

## Phase Status: ALL PHASES COMPLETE + VERIFIED

| Phase | Status |
|-------|--------|
| Phase 0 — Foundation/Auth | ✅ COMPLETE |
| Phase 1 — Market Data/Watchlists/Portfolio | ✅ COMPLETE |
| Phase 2 — Technical Analysis/Signals/Explainability | ✅ COMPLETE |
| Phase 3 — Backtesting | ✅ COMPLETE |
| Phase 4 — Risk/Alerts | ✅ COMPLETE |
| Phase 5 — Integration/Testing/Deployment | ✅ COMPLETE |

## Verification Results

| Check | Result |
|-------|--------|
| Backend tests | **50 passed, 0 failed** |
| Frontend lint (ESLint) | **PASS — 0 errors, 0 warnings** |
| Frontend build (TypeScript) | **PASS — 13 routes** |
| Docker Compose | **6/6 services healthy** |
| PostgreSQL | **10 tables, 2610 OHLCV rows** |
| Redis | **Healthy** |
| Celery Worker | **Running** |
| Nginx | **Proxy working** |
| Persistence (down/up) | **PASS — all data survives** |
| Auth E2E | **PASS — register, login, refresh, /me** |
| Markets | **PASS — 10 instruments, SIMULATED label** |
| Watchlists CRUD | **PASS — create, add, remove, cross-user** |
| Portfolio BUY | **PASS — cash deduction, weighted avg** |
| Portfolio SELL | **PASS — validation, holding update** |
| P&L calculations | **PASS — equity, unrealised P&L** |
| Analysis | **PASS — indicators, signal, explanation** |
| Backtesting | **PASS — metrics, equity curve** |
| Alerts | **PASS — create, list, delete** |
| CSV Export | **PASS — transactions + snapshots** |
| Authorization isolation | **PASS — cross-user enforced** |
| Browser verified | **PASS — Edge loads all routes (nginx logs)** |

## Container Logs
- Backend: No errors. All requests 200.
- Frontend: Ready, no errors.
- Nginx: All routes returning 200. Dashboard, markets, analysis, backtest, alerts all accessed by real browser.

## SIMULATED DATA Labels
All applicable pages display "SIMULATED DATA" or "SIMULATED":
- /markets header
- /analysis header
- /backtest header
- Markets page footer disclaimer
- Analysis page signal disclaimer

## Known Limitations
- Mock market data (simulated, deterministic)
- Broker adapter is read-only (order execution disabled)
- Signal engine is rule-based, not ML
- Production would use `alembic upgrade head` instead of `create_all`
- Frontend is tracked as git submodule reference in outer repo

## URLs
| Service | URL |
|---------|-----|
| Frontend (nginx) | http://localhost |
| Backend (direct) | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |

## Daily Commands for 30-Day Test

```bash
# Start
cd C:\Users\Venugopal\sv-ai-trading
docker compose up -d

# Stop (preserves all data)
docker compose down

# NEVER: docker compose down -v  (deletes all data)
```
