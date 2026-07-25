# SV AI Trading Platform

AI-assisted stock analysis and paper trading platform. Analyze stocks, generate technical signals with explainable reasoning, backtest strategies, and execute simulated paper trades — all with zero real money.

## Quick Start (Windows)

```bash
cd C:\Users\Venugopal\sv-ai-trading

# Start
docker compose up -d
# Wait ~30 seconds for backend to seed database

# Check
docker compose ps
# All 6 services should show "healthy" or "Up"

# Open
# http://localhost → frontend
# http://localhost/api/health → backend health
```

## Stop
```bash
docker compose down
# NEVER use: docker compose down -v  (deletes all data)
```

## Rebuild After Code Changes
```bash
docker compose up --build -d
```

## View Logs
```bash
docker compose logs backend --tail=50
docker compose logs frontend --tail=50
docker compose logs nginx --tail=20
```

## Architecture
```
Nginx (:80) → Frontend (:3000, Next.js)
            → /api/* → Backend (:8000, FastAPI)
Backend → PostgreSQL (:5432) + Redis (:6379)
Worker → Celery + Redis
```

## URLs
| Service | URL |
|---------|-----|
| Frontend | http://localhost |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| API through proxy | http://localhost/api/health |

## Features
- JWT authentication (register, login, refresh tokens)
- Market data with 10 seeded instruments + OHLCV history
- Watchlists with CRUD and symbol management
- Paper trading portfolio (BUY/SELL with weighted average price)
- Portfolio analytics (equity, P&L, cost basis, market value)
- Technical analysis (RSI, MACD, SMA, EMA, Bollinger Bands, ATR)
- Rule-based signal engine (BUY/SELL/HOLD with confidence + explanation)
- Backtesting (Sharpe, Sortino, max drawdown, equity curve)
- Risk analytics (position concentration, sector exposure)
- Alerts (price above/below, signal BUY/SELL)
- Daily portfolio snapshots
- CSV export of transactions and snapshots
- Broker adapter interface (read-only, order execution disabled)

## Running Tests

### Backend
```bash
docker compose build backend
docker run --rm sv-ai-trading-backend pytest -v
```

### Frontend
```bash
cd frontend
npm install
npm run build    # validates TypeScript and builds
npm run lint     # ESLint
```

## Data Persistence
All user data persists across restarts:
- Users, portfolios, holdings, transactions, watchlists, alerts
- PostgreSQL data stored in Docker named volume
- Redis cache (not critical for persistence)

**WARNING**: `docker compose down -v` deletes the `pgdata` volume and all data.

## CSV Export
Get portfolio data at `/api/portfolio/{id}/export` with auth token.
Downloads transactions + snapshots as CSV.

## Daily Snapshot
```bash
curl -X POST http://localhost/api/portfolio/{id}/snapshot \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Disclaimer
This is a PAPER TRADING platform. No real trades are executed. Market data is simulated for development/testing. All signals are algorithmic outputs from a rule-based engine. This is not financial advice.

## 30-Day Test
See `30_DAY_TEST_PLAN.md` for daily procedures.
Use `TESTING_LOG.md` to record observations.
