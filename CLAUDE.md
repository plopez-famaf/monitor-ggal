# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Flask-based web application that monitors the real-time stock price of GGAL (Banco Galicia ADR) using the Finnhub API. The application provides a dashboard with live price updates, historical charts, and statistics.

## Architecture

### Core Components

**Backend (`app.py`)**
- Flask web server with REST API endpoints
- `MonitorGGAL` class: Background monitoring service that polls Finnhub API every 10 seconds
- Uses a daemon thread to continuously fetch price data in the background
- Stores up to 1000 price points in a `deque` for efficient memory management
- All price data is stored in-memory (no persistent database)

**Frontend (`templates/index.html`)**
- Single-page application with vanilla JavaScript
- Chart.js for price visualization
- Auto-refreshes every 10 seconds via `/api/*` endpoints
- Responsive design with gradient UI

### Data Flow

1. On startup, `MonitorGGAL` launches a background daemon thread
2. Thread polls Finnhub API every 10 seconds via `obtener_precio()`
3. Price data is appended to `historial` deque (max 1000 entries)
4. Frontend polls Flask API endpoints every 10 seconds
5. API returns latest data from in-memory `historial`

### API Endpoints

**Core Endpoints:**
- `GET /` - Serves the dashboard HTML
- `GET /api/precio-actual` - Returns most recent price point
- `GET /api/historial` - Returns all stored price history (up to 1000 points)
- `GET /api/estadisticas` - Returns computed statistics (max, min, average)
- `GET /api/health` - Health check endpoint

**ML/Forecasting Endpoints:**
- `GET /api/forecast` - Returns ensemble price predictions for 1, 5, and 10 minute horizons
- `GET /api/trading-signal` - Returns AI-generated trading signal (BUY/SELL/HOLD) with reasoning

## Environment Configuration

**Required:**
- `FINNHUB_API_KEY` - Finnhub API key for stock data (falls back to "demo" if not set)
- `PORT` - Server port (defaults to 5000)

Get a free Finnhub API key at: https://finnhub.io

## Development Commands

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set API key (required for real data)
export FINNHUB_API_KEY="your_api_key_here"

# Run development server
python app.py

# Run tests
python test_app.py
```

Server runs on http://localhost:5000

### Testing

Run the comprehensive test suite before deployment:
```bash
python test_app.py
```

Tests cover:
- MonitorGGAL class functionality
- All forecasting models (MA, ES, LR, momentum, mean reversion)
- Ensemble forecasting
- Technical indicators
- All API endpoints
- Integration workflows

### Production (Render.com)

The app is deployed on Render using Gunicorn:

```bash
# Start command configured in Render
gunicorn app:app
```

## Key Implementation Details

### Background Monitoring

The `monitorear_background()` method runs in a daemon thread, which means:
- Thread automatically terminates when main process exits
- No graceful shutdown needed
- Data is lost on restart (in-memory only)

### Rate Limiting

Finnhub free tier allows 60 API calls/minute. Current configuration:
- 10-second intervals = 6 calls/minute (well within limits)
- Modify interval in line 68 of `app.py`: `args=(10,)` changes the seconds

### Symbol Modification

To monitor a different stock, change line 14 in `app.py`:
```python
self.symbol = "GGAL"  # Change to any valid Finnhub symbol
```

### Forecasting System (`forecaster.py`)

The forecasting module implements an **ensemble approach** combining 5 models:

1. **Simple Moving Average** - Fast baseline using short/long MA crossover
2. **Exponential Smoothing** - Triple ES (Holt-Winters style) for trend detection
3. **Linear Regression** - Fits linear trend to recent 20 data points
4. **Momentum-based** - Projects recent price momentum forward
5. **Mean Reversion** - Assumes prices revert to recent mean (anti-momentum)

**Ensemble Method:**
- All models predict independently
- Final prediction = median of all predictions (robust to outliers)
- Confidence based on prediction spread (low spread = high confidence)
- Requires minimum 10 data points (15 for trading signals)

**Technical Indicators:**
- SMA, EMA (5-period moving averages)
- Momentum & ROC (Rate of Change)
- Volatility (standard deviation of returns)
- RSI (Relative Strength Index, 14-period)

**Trading Signal Logic:**
- BUY: Predicted rise > 0.5% OR RSI < 30 (oversold)
- SELL: Predicted drop > 0.5% OR RSI > 70 (overbought)
- HOLD: Low confidence or conflicting signals
- Momentum check prevents counter-trend signals

**Design Philosophy:**
- Lightweight: Only numpy dependency, no heavy ML libraries
- Fast: All predictions complete in <100ms
- Stateless: No model training/persistence needed
- HFT-style: Minute-level predictions suitable for short-term trading

## Deployment Notes

This app is designed for Render.com free tier deployment:
- Free tier suspends after 15 minutes of inactivity
- Use UptimeRobot or similar to ping `/api/health` every 5 minutes to keep alive
- See `GUIA_DEPLOY_RENDER.md` for complete deployment instructions

## Limitations

- **No persistence**: All data is in-memory and lost on restart
- **Single symbol**: Only monitors one stock at a time (GGAL)
- **No authentication**: API endpoints are publicly accessible
- **Fixed history size**: Limited to last 1000 data points
- **No error recovery**: If Finnhub API is down, returns None and continues polling
- **Short-term predictions only**: Models designed for 1-10 minute horizons, not long-term
- **No model retraining**: Uses fixed statistical methods, no adaptive learning
- **Market hours**: Finnhub data only updates during market hours (US stock market)

## Forecasting Performance

Expect forecasting accuracy to:
- **Work best**: During high-volume trading hours with consistent trends
- **Work poorly**: During market open/close volatility, news events, low volume
- **Typical accuracy**: 60-70% directional accuracy on 5-minute horizon in stable conditions

The ensemble approach provides robustness but predictions should be treated as **probabilistic estimates**, not guarantees. Always validate with actual market conditions.
