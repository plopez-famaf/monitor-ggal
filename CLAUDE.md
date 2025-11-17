# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Flask-based web application that monitors real-time stock price of GGAL (Banco Galicia ADR) using the Finnhub API. Features live price updates, historical charts, statistics, and ML-based price forecasting for short-term trading signals.

See [README.md](README.md) for user-facing documentation.

## Architecture

### Core Components

**Backend (`app.py`)**
- Flask web server with REST API endpoints
- `MonitorGGAL` class: Background daemon thread that polls Finnhub API every 10 seconds
- In-memory storage: `deque(maxlen=1000)` for price history (no database persistence)
- `GGALForecaster` class: Ensemble ML forecasting for 1/5/10-minute predictions

**Frontend (`templates/index.html`)**
- Single-page vanilla JavaScript app with Chart.js visualization
- Auto-refreshes every 10 seconds via API polling
- Dark theme UI with real-time updates

### Data Flow

1. **Production (Gunicorn)**: `gunicorn_config.py` `post_fork()` hook starts background thread after worker fork
2. **Local Dev**: Thread started in `__main__` block when running `python app.py`
3. Background daemon thread continuously polls Finnhub API → `obtener_precio()`
4. Price data appended to in-memory `historial` deque (max 1000 entries)
5. Frontend polls API endpoints every 10 seconds
6. Forecaster analyzes price history on demand to generate predictions

**CRITICAL**: Thread must start AFTER Gunicorn forks workers, not during module import. Otherwise multiple threads run simultaneously and data collection becomes inconsistent.

### API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Dashboard HTML |
| `GET /api/precio-actual` | Latest price point |
| `GET /api/historial` | All price history (up to 1000 points) |
| `GET /api/estadisticas` | Statistics (max, min, avg) |
| `GET /api/health` | Health check |
| `GET /api/forecast` | Ensemble predictions (1/5/10 min horizons) |
| `GET /api/trading-signal` | Trading signal (BUY/SELL/HOLD) with reasoning |

## Environment Configuration

- `FINNHUB_API_KEY` - **REQUIRED** Finnhub API key for stock data. Get free key at: https://finnhub.io
  - Note: The "demo" token is no longer valid and will return 401 Unauthorized
  - App will start but return no data without valid API key
- `PORT` - Server port (defaults to 5001)

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run with API key (REQUIRED)
export FINNHUB_API_KEY="your_api_key_here"
python app.py

# Debug API connection
python debug_api.py

# Run comprehensive test suite (30+ test cases)
python test_app.py

# Production deployment (Render.com with Gunicorn)
gunicorn -c gunicorn_config.py app:app
```

Server runs on http://localhost:5001 by default. See [GUIA_DEPLOY_RENDER.md](GUIA_DEPLOY_RENDER.md) for deployment instructions.

**Important:**
- ⚠️ Without valid `FINNHUB_API_KEY`, app will show warning but **NO DATA will be collected**
- The "demo" token no longer works (returns 401 Unauthorized)
- Use `debug_api.py` script to verify API connection
- Status 202 responses mean data is still being collected (need ~10-15 data points)

## Key Implementation Details

### Background Monitoring

**Thread Initialization:**
- **Production**: Started via `gunicorn_config.py` `post_fork()` hook after worker process fork
- **Local Dev**: Started in `if __name__ == '__main__'` block when running `python app.py`
- Runs as daemon thread → automatically terminates with main process
- No graceful shutdown needed

**Configuration:**
- 10-second polling interval = 6 calls/min (well within Finnhub free tier 60/min limit)
- To change interval: modify `args=(10,)` in `gunicorn_config.py` or `app.py` __main__ block
- To change symbol: modify `self.symbol = "GGAL"` in `MonitorGGAL.__init__()`
- All data lost on restart (no persistence)

**CRITICAL for Production (Render.com):**
- Data stored in-memory in `monitor.historial` deque
- **MUST use single Gunicorn worker** (`workers=1` in `gunicorn_config.py`)
- Multiple workers = separate memory spaces = requests see empty historial
- **Thread MUST start in `post_fork()` hook**, not at module import time
  - If started at import: parent process starts thread → worker fork → worker also starts thread = 2 threads
  - Both threads write to same deque causing data inconsistency
  - See `gunicorn_config.py` for correct implementation

### Forecasting System (`forecaster.py`)

**Single Model: Kalman Filter**
- Optimal state estimation for real-time noisy time series
- State vector: [price, velocity] where velocity = $/timestep
- Mathematically proven to minimize mean squared error (under Gaussian assumptions)
- Used in production systems: GPS navigation, autopilot, rocket guidance

**How it works:**
1. Predict: Projects state forward using motion model
2. Update: Corrects prediction with new measurement
3. Optimal: Balances prediction vs measurement based on uncertainties
4. Recursive: Updates incrementally, no full history recomputation needed

**Key Outputs:**
- Price prediction with 95% confidence interval
- Velocity (rate of price change)
- Uncertainty quantification (standard deviation)
- Trend direction (up/down/flat based on velocity)

**Trading Signal:**
- **Signal strength**: 0-100 numeric score (not just BUY/SELL/HOLD)
- Calculated from:
  * Price change magnitude (max 50 points)
  * Velocity strength (max 30 points)
  * Low uncertainty (max 20 points)
- **BUY**: Predicted rise > 0.3% with medium/high confidence
- **SELL**: Predicted drop > 0.3% with medium/high confidence
- **HOLD**: Low expected movement or high uncertainty

**Design Philosophy:**
- Lightweight (numpy only, ~150 lines)
- Fast (<50ms per prediction)
- Stateless (reinitializes filter each call with full history)
- Theoretically optimal (Kalman = maximum likelihood estimator)

## Troubleshooting

**App shows warning but no data appears:**
1. **MOST COMMON**: Missing or invalid API key
   - Run: `python debug_api.py` to diagnose
   - Verify: `echo $FINNHUB_API_KEY` shows your key
   - Test API directly: `curl "https://finnhub.io/api/v1/quote?symbol=GGAL&token=YOUR_KEY"`
   - Demo token no longer works (401 error)

2. **"GET /api/precio-actual HTTP/1.1 202" responses:**
   - Normal on startup - app needs time to collect data
   - Wait 10-30 seconds for first data to appear
   - If persists beyond 1 minute, check API key

3. **Forecasting endpoints returning 202:**
   - `/api/forecast` needs minimum 10 data points (~2 minutes of monitoring)
   - `/api/trading-signal` needs minimum 15 data points (~3 minutes)
   - Check browser console or `curl` the endpoint to see exact error message

4. **No price updates / stuck data:**
   - Check if market is open (US market hours: Mon-Fri 9:30 AM - 4:00 PM ET)
   - Outside market hours, prices stay frozen at last close
   - Background thread logs to console: look for "Error obteniendo precio" messages
   - Verify rate limit: API returns header `X-Ratelimit-Remaining`

5. **Port already in use:**
   - Default port is 5001 in [app.py:124](app.py)
   - Override with: `PORT=8000 python app.py`

## Limitations & Considerations

**System Limitations:**
- No persistence (all data in-memory, lost on restart)
- Single symbol monitoring only
- No authentication on API endpoints
- Fixed history (max 1000 data points)
- No graceful API error recovery (returns None, continues polling)

**Forecasting Limitations:**
- Short-term only (1-10 min horizons, not for long-term trends)
- Assumes Gaussian noise (Kalman optimal under this assumption)
- Assumes constant velocity model (price changes linearly)
- No adaptive learning (reinitializes filter each prediction)
- Market hours only (data updates during US trading hours)
- Works best: stable markets with gradual trends
- Works poorly: sudden news events, market gaps, high volatility periods

**Deployment Notes:**
- Designed for Render.com free tier (suspends after 15 min inactivity)
- Use UptimeRobot to ping `/api/health` every 5 min to keep alive
- Predictions are probabilistic estimates, not financial advice
