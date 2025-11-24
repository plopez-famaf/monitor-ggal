# Multi-Symbol Monitoring

**Monitor multiple assets (stocks + crypto) simultaneously with independent Kalman Filter forecasters.**

## Quick Start

### Option 1: GGAL only (default)

```bash
export FINNHUB_API_KEY="your_finnhub_key"
python cli.py
```

### Option 2: GGAL + Bitcoin

```bash
export FINNHUB_API_KEY="your_finnhub_key"
export ENABLE_CRYPTO=true
python cli.py
```

### Option 3: With Binance API key (optional)

```bash
export FINNHUB_API_KEY="your_finnhub_key"
export BINANCE_API_KEY="your_binance_key"  # Optional for public data
export ENABLE_CRYPTO=true
python cli.py
```

**Note:** Binance API key is **not required** for public price data. The system uses Binance's public endpoints which don't need authentication.

## Usage

### List available symbols

```
ggal> symbols
```

Output:
```
┏━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━┓
┃ Key    ┃ Symbol   ┃ Name                  ┃  Type  ┃ Status ┃
┡━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━┩
│ GGAL ◄ │ GGAL     │ Banco Galicia ADR     │ stock  │   ✓    │
│ BTC    │ BTCUSDT  │ Bitcoin / USDT        │ crypto │   ✓    │
└────────┴──────────┴───────────────────────┴────────┴────────┘

Current: GGAL | Use 'switch <key>' to change
```

### Switch between symbols

```
ggal> switch btc
Switched to BTC (Bitcoin / USDT)

btc> status
↗ $67345.12 +1234.56 (+1.87%) | 14:23:45

btc> forecast
Horizon:   5 min (fixed)
Current:   $67345.12
Predicted: ↗ $67489.23
Change:    +144.11 (+0.21%)
...

btc> switch ggal
Switched to GGAL (Banco Galicia ADR)

ggal> status
↗ $45.67 +0.34 (+0.75%) | 14:23:45
```

## Features

### Independent Forecasters

Each symbol has its own:
- **Kalman Filter** - Trained on symbol's specific price history
- **Prediction Tracker** - Validates forecasts independently
- **Effectiveness Index** - Measures prediction quality per symbol

### Continuous Monitoring

All symbols are monitored **simultaneously** in background threads:
- 10-second polling interval for all symbols
- Data collected even when viewing different symbol
- Switch between symbols without losing data

### Supported Symbols

#### Current Support

| Symbol | Type | API | Description |
|--------|------|-----|-------------|
| GGAL | stock | Finnhub | Banco Galicia ADR |
| BTCUSDT | crypto | Binance | Bitcoin / Tether |

#### Easy to Extend

Add more symbols by editing `cli.py`:

```python
symbols_config = {
    'GGAL': {
        'type': 'stock',
        'api_key': finnhub_key,
        'name': 'Banco Galicia ADR'
    },
    'BTC': {
        'type': 'crypto',
        'symbol': 'BTCUSDT',
        'name': 'Bitcoin / USDT'
    },
    'ETH': {
        'type': 'crypto',
        'symbol': 'ETHUSDT',
        'name': 'Ethereum / USDT'
    },
    'AAPL': {
        'type': 'stock',
        'api_key': finnhub_key,
        'name': 'Apple Inc.'
    }
}
```

## Architecture

### Data Flow

```
┌─────────────────────────────────────────────────┐
│                   CLI Process                    │
├─────────────────────────────────────────────────┤
│                                                  │
│  ┌─────────────┐        ┌─────────────┐         │
│  │   GGAL      │        │     BTC     │         │
│  │  Monitor    │        │   Monitor   │         │
│  │  Thread     │        │   Thread    │         │
│  │  (10s poll) │        │  (10s poll) │         │
│  └──────┬──────┘        └──────┬──────┘         │
│         │                      │                 │
│         ▼                      ▼                 │
│  ┌─────────────┐        ┌─────────────┐         │
│  │  Historial  │        │  Historial  │         │
│  │  (1000 pts) │        │  (1000 pts) │         │
│  └──────┬──────┘        └──────┬──────┘         │
│         │                      │                 │
│         ▼                      ▼                 │
│  ┌─────────────┐        ┌─────────────┐         │
│  │   Kalman    │        │   Kalman    │         │
│  │   Filter    │        │   Filter    │         │
│  └──────┬──────┘        └──────┬──────┘         │
│         │                      │                 │
│         ▼                      ▼                 │
│  ┌─────────────┐        ┌─────────────┐         │
│  │  Tracker    │        │   Tracker   │         │
│  │  (GGAL)     │        │   (BTC)     │         │
│  └─────────────┘        └─────────────┘         │
│                                                  │
│        User switches between with 'switch'       │
└─────────────────────────────────────────────────┘
```

### API Endpoints

#### Finnhub (Stocks)
- Endpoint: `https://finnhub.io/api/v1/quote`
- Rate limit: 60 calls/min (free tier)
- Returns: OHLC + previous close

#### Binance (Crypto)
- Endpoint: `https://api.binance.com/api/v3/ticker/24hr`
- Rate limit: Very high (public endpoint)
- Returns: OHLC + 24h stats + volume
- **No API key required** for price data

## Performance

### Memory Usage
- Base: ~30MB
- Per symbol: ~10MB (1000 price points)
- Total (2 symbols): ~50MB

### CPU Usage
- Background threads: <1% each
- Forecast computation: <50ms
- Symbol switching: <1ms (instant)

### Network
- Finnhub: 6 calls/min (10s interval)
- Binance: 6 calls/min (10s interval)
- Total: 12 calls/min (well within limits)

## Commands Reference

| Command | Description |
|---------|-------------|
| `symbols` | List all monitored symbols |
| `switch <key>` | Switch to different symbol |
| `status` | Current price of active symbol |
| `forecast` | 5-min forecast for active symbol |
| `signal` | Trading signal for active symbol |
| `accuracy` | Effectiveness index for active symbol |
| `stats` | Statistics for active symbol |
| `history` | Recent prices for active symbol |

## Troubleshooting

**"Unknown symbol: BTC"**
- Make sure `ENABLE_CRYPTO=true` is set
- Restart CLI after setting environment variable

**Binance returns no data**
- Check symbol format (must be `BTCUSDT`, not `BTC-USDT` or `BTC/USDT`)
- Verify internet connection to `api.binance.com`

**Effectiveness index shows 0**
- Each symbol needs 3+ validated predictions (~15 minutes)
- Predictions are independent per symbol
- Switch to symbol and wait for data

## Future Enhancements

Possible additions:
- [ ] Auto-detect crypto pairs from Binance
- [ ] Support for Coinbase, Kraken APIs
- [ ] Symbol comparison mode (compare forecasts side-by-side)
- [ ] Alert system (price crosses threshold)
- [ ] Export data per symbol to CSV

---

**Educational purposes only. Not financial advice.**
