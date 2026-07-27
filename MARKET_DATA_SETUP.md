# MARKET DATA SETUP — Upstox Integration

## Overview

The SV AI Trading Platform supports two market data modes:

| Mode | Environment Variable | Description |
|------|---------------------|-------------|
| Simulated | `MARKET_DATA_PROVIDER=simulated` | Deterministic mock data (default, no API keys needed) |
| Upstox Live | `MARKET_DATA_PROVIDER=upstox` | Real NSE market data via Upstox API |

## Step 1: Create Upstox API App

1. Go to https://upstox.com/
2. Sign up / log in
3. Navigate to **Developer Console** → **My Apps**
4. Create a new app with:
   - Redirect URI: `http://localhost:8000/upstox/callback`
   - Required permissions: **Market Data Feed** (data read-only is sufficient)
5. Note your **Client ID** and **Client Secret**

## Step 2: Get Access Token

Upstox uses OAuth 2.0. The easiest way:

```bash
# Visit this URL in your browser (replace CLIENT_ID and REDIRECT_URI):
# https://api.upstox.com/v2/login/authorization/dialog?
#   client_id=YOUR_CLIENT_ID&
#   redirect_uri=http://localhost:8000/upstox/callback&
#   response_type=code

# After authorization, you get a `code` in the redirect URL.
# Exchange it for an access token:

curl -X POST https://api.upstox.com/v2/login/authorization/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "code=YOUR_AUTH_CODE" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET" \
  -d "redirect_uri=http://localhost:8000/upstox/callback" \
  -d "grant_type=authorization_code"
```

The response contains `access_token`. Tokens expire in 1 day.

## Step 3: Configure Environment

Create or edit the `.env` file in the `backend/` directory:

```
MARKET_DATA_PROVIDER=upstox
UPSTOX_ACCESS_TOKEN=your_access_token_here
UPSTOX_CLIENT_ID=your_client_id
UPSTOX_CLIENT_SECRET=your_client_secret
UPSTOX_REDIRECT_URI=http://localhost:8000/upstox/callback
```

Or pass them as environment variables to Docker Compose:

```
set UPSTOX_ACCESS_TOKEN=your_token
docker compose up -d
```

## Step 4: Start the Application

```bash
cd C:\Users\Venugopal\sv-ai-trading
docker compose up --build -d
```

Check health:
```bash
curl http://localhost/api/health
# Response includes: "market_data_provider": "upstox", "upstox": "configured"
```

## Architecture

```
Upstox Market Feed V3 (WebSocket)
        │ wss://api.upstox.com/v3/feed/market-data-feed
        ▼
┌─────────────────────────────┐
│  UpstoxMarketDataProvider    │
│  (decodes binary protobuf,   │
│   writes to Redis cache)     │
└──────────┬──────────────────┘
           │
     ┌─────▼──────┐
     │ Redis Cache │  (key: market:NSE_EQ:TCS, TTL: 120s)
     └─────┬──────┘
           │
     ┌─────▼────────┐
     │ FastAPI routes │
     │ GET /market/*  │
     │ WS /ws/market  │  (frontend live updates)
     └───────────────┘
           │
     ┌─────▼────────┐
     │ Next.js UI    │
     └──────────────┘
```

## Supported Instruments

| Symbol | Instrument Key | Sector |
|--------|---------------|--------|
| RELIANCE | NSE_EQ\|INE002A01018 | Oil & Gas |
| TCS | NSE_EQ\|INE467B01029 | IT |
| INFY | NSE_EQ\|INE009A01021 | IT |
| HDFCBANK | NSE_EQ\|INE040A01034 | Banking |
| ICICIBANK | NSE_EQ\|INE090A01021 | Banking |
| SBIN | NSE_EQ\|INE062A01020 | Banking |
| ITC | NSE_EQ\|INE154A01025 | FMCG |
| LT | NSE_EQ\|INE018A01030 | Infrastructure |
| BHARTIARTL | NSE_EQ\|INE397D01024 | Telecom |
| AXISBANK | NSE_EQ\|INE238A01034 | Banking |

## Historical Data

Historical OHLCV candles are fetched from Upstox History API (`/v2/historical-candle/{instrument_key}/{interval}/{to_date}/{from_date}`).

- Interval: 1 day
- Stored in PostgreSQL `ohlcv_data` table
- Deduplication: on `(instrument_id, timestamp, interval)`

## Redis Caching

- Live quotes cached with 120-second TTL
- Key format: `market:NSE_EQ:{SYMBOL}`
- Auto-refreshed by WebSocket feed

## Market Hours

- NSE trading hours: 9:15 AM — 3:30 PM IST (Asia/Kolkata)
- Monday — Friday (excluding Indian holidays)
- The application handles market-closed state gracefully

## WebSocket for Frontend

Frontend connects to `ws://localhost/ws/market` (through nginx).

Subscribe to symbols:
```json
{"action": "subscribe", "symbols": ["TCS", "RELIANCE"]}
```

Receive updates:
```json
{
  "type": "quote",
  "symbol": "TCS",
  "last_price": 3850.50,
  "change": 25.30,
  "change_pct": 0.66,
  "volume": 1250000,
  "timestamp": "2026-07-26T10:30:00+05:30",
  "source": "UPSTOX"
}
```

## Token Renewal

Upstox access tokens expire after 1 day. For production use:
1. Use the authorization code flow to get a refresh token
2. Set up a cron/Celery task to refresh the token daily
3. Update the `UPSTOX_ACCESS_TOKEN` environment variable

## Troubleshooting

### "Provider will return empty results"
The `UPSTOX_ACCESS_TOKEN` is not set or invalid. Verify through:
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "https://api.upstox.com/v2/market-quote/quotes?instrument_key=NSE_EQ%7CINE467B01029"
```

### WebSocket not connecting
- Check token validity
- Verify network allows outbound WebSocket connections
- Check Docker logs: `docker compose logs backend`

### No data during market hours
- Verify instrument keys are correct
- Check subscription was acknowledged by the feed
- Check Redis: `docker exec sv-ai-trading-redis-1 redis-cli GET market:NSE_EQ:TCS`

### Switching between providers
```bash
# To use simulated data:
set MARKET_DATA_PROVIDER=simulated
docker compose up -d

# To use Upstox:
set MARKET_DATA_PROVIDER=upstox
set UPSTOX_ACCESS_TOKEN=your_token
docker compose up -d
```

## Security Notes
- NEVER commit `UPSTOX_ACCESS_TOKEN` to git
- NEVER expose Upstox tokens to the browser/frontend
- All Upstox API calls go through the backend
- Market data WebSocket is backend-only, frontend connects to our own WS
