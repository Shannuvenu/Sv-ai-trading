# 30-Day Paper Trading Test Plan

## Test Period
Start: Monday (set your start date)
End: 30 trading days later

## Daily Procedure

### 1. Start Application
```
cd C:\Users\Venugopal\sv-ai-trading
docker compose up -d
```

Wait for all services to be healthy:
```
docker compose ps
```

All 6 services should show "healthy" or "Up":
- postgres: healthy
- redis: healthy
- backend: Up
- worker: Up
- frontend: Up
- nginx: Up

### 2. Check Health
Open http://localhost in browser.
Verify the login page loads without errors.

### 3. Login
Use your registered credentials.

### 4. Dashboard Review
Check summary: equity, cash, P&L, holdings count, watchlists.

### 5. Markets
Visit /markets. Verify instruments display with prices.
Note: data is SIMULATED for development/testing.

### 6. Watchlists
Check your watchlists. Add/remove symbols as needed.
Verify prices update.

### 7. Analysis
Select 1-2 symbols. Review:
- Price chart
- Technical indicators
- Signal (BUY/SELL/HOLD)
- Explanation/reasoning
- Confidence score

### 8. Trading Decisions (Paper Only)
Based on analysis, decide whether to:
- Execute paper BUY
- Execute paper SELL
- Hold

Use the Portfolio page to execute trades.

### 9. Portfolio Review
After any trades:
- Check cash balance
- Check holdings
- Check equity
- Check P&L
- Review transaction history

### 10. Backtesting (Optional)
Test strategies on /backtest before executing trades.

### 11. Alerts
Create/check alerts. Alerts are evaluated against current data.

### 12. Create Daily Snapshot
```
curl -X POST http://localhost/api/portfolio/{ID}/snapshot \
  -H "Authorization: Bearer YOUR_TOKEN"
```

This captures equity, cash, invested, market value, and P&L.

### 13. Log Day
Fill in TESTING_LOG.md with observations.

### 14. Stop Application (End of Day)
```
docker compose down
```

**IMPORTANT: Do NOT use `docker compose down -v`**
This deletes all data. Only use `docker compose down`.

## Data Export

At any time, export portfolio data as CSV:
```
http://localhost/api/portfolio/{ID}/export
```
(with auth token)

## Metrics to Track

After 30 days, analyze:

| Metric | Source |
|--------|--------|
| Starting equity | First snapshot |
| Ending equity | Last snapshot |
| Total return % | Calculated from snapshots |
| Number of trades | Transactions table |
| Win rate | Transactions analysis |
| Best trade | Review transaction history |
| Worst trade | Review transaction history |
| Max drawdown | Export data for analysis |
| Sharpe ratio | Use backtest or export + calculate |
| Most traded symbol | Transactions table |
| Signal accuracy | Compare signals to actual price moves |
| Daily P&L | Snapshot data |

## Troubleshooting

### Application won't start
```
docker compose down
docker compose up -d
```

### Page shows spinner forever
Refresh browser (F5). If problem persists:
```
docker compose restart frontend
```

### API errors
```
docker compose logs backend --tail=50
```

### Login issues
Register a new account. Old data persists in DB.

### Need to reset all data
```
docker compose down -v    # WARNING: DELETES ALL DATA
docker compose up -d       # Fresh start
```
