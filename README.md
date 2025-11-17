# Monitor GGAL - Stock Price Monitor with ML Forecasting

Real-time stock price monitoring for GGAL (Banco Galicia ADR) with machine learning-based price forecasting and trading signals.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/flask-3.0+-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## Features

- 📈 **Real-time Price Monitoring** - Live GGAL stock price updates every 10 seconds
- 🔬 **Kalman Filter Forecasting** - Optimal state estimation for 1/5/10-minute predictions
- 📊 **Numeric Trading Signals** - 0-100 signal strength (not just BUY/SELL/HOLD)
- 📉 **Confidence Intervals** - 95% prediction bounds with uncertainty quantification
- 🎨 **Dark Theme UI** - Clean, minimalistic interface focused on predictions
- ⚡ **Lightweight** - Only numpy, no ML frameworks

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Get API Key (Required)

The demo token no longer works. You need a real API key:

1. Register for free at: https://finnhub.io
2. Get your API key from the dashboard
3. Set environment variable:

```bash
export FINNHUB_API_KEY="your_api_key_here"
```

### 3. Run the Application

```bash
python app.py
```

Open browser at: http://localhost:5001

### 4. Debug Connection (Optional)

If you're not seeing data, run the diagnostic tool:

```bash
python debug_api.py
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Dashboard UI |
| `GET /api/precio-actual` | Latest price data |
| `GET /api/historial` | Historical prices (up to 1000 points) |
| `GET /api/estadisticas` | Price statistics |
| `GET /api/forecast` | ML predictions (1/5/10 min) |
| `GET /api/trading-signal` | BUY/SELL/HOLD signal |
| `GET /api/health` | Health check |

## How It Works

### Data Collection
- Background daemon thread polls Finnhub API every 10 seconds
- Stores up to 1000 price points in-memory
- No database persistence (data lost on restart)

### Kalman Filter Forecasting
Optimal state estimation for noisy time series:
- **State vector**: [price, velocity]
- **Prediction**: Price forecast with 95% confidence interval
- **Uncertainty**: Automatic quantification of prediction confidence
- **Velocity**: Rate of price change ($/timestep)
- **Mathematically optimal**: Minimizes mean squared error

Used in production systems like GPS, autopilot, and rocket guidance.

### Trading Signals
- **Signal strength**: 0-100 numeric score
- Calculated from price change, velocity, and uncertainty
- **BUY**: Predicted rise > 0.3% with medium/high confidence
- **SELL**: Predicted drop > 0.3% with medium/high confidence
- **HOLD**: Low expected movement or high uncertainty

## Testing

Run the comprehensive test suite:

```bash
python test_app.py
```

Tests cover:
- Kalman Filter implementation
- Forecast accuracy and uncertainty
- API endpoints
- Integration workflows

## Troubleshooting

### App shows warning but no data

**Problem**: You'll see `⚠️ ADVERTENCIA: FINNHUB_API_KEY no está configurada`

**Solution**:
1. Verify API key is set: `echo $FINNHUB_API_KEY`
2. Run diagnostic: `python debug_api.py`
3. Test API directly: `curl "https://finnhub.io/api/v1/quote?symbol=GGAL&token=YOUR_KEY"`

### Data showing but not updating

**Problem**: Prices frozen at same value

**Possible causes**:
- Market is closed (US hours: Mon-Fri 9:30 AM - 4:00 PM ET)
- Outside market hours, prices show last close value
- This is normal behavior

### Forecasting returns 202

**Problem**: `/api/forecast` or `/api/trading-signal` return status 202

**Explanation**:
- Normal - needs time to collect data
- Forecast needs 10+ data points (~2 minutes)
- Trading signal needs 15+ points (~3 minutes)
- Wait and try again

## Deployment

### Render.com (Recommended)

See [GUIA_DEPLOY_RENDER.md](GUIA_DEPLOY_RENDER.md) for detailed instructions.

Quick deploy:
1. Push to GitHub
2. Create new Web Service on Render
3. Connect repository
4. Add environment variable: `FINNHUB_API_KEY`
5. Deploy

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FINNHUB_API_KEY` | **Yes** | `demo` | Finnhub API key |
| `PORT` | No | `5001` | Server port |

## Limitations

- **No persistence** - All data in-memory, lost on restart
- **Single symbol** - Only monitors GGAL
- **No authentication** - Public API endpoints
- **Short-term predictions** - 1-10 min horizons only
- **Gaussian assumption** - Kalman assumes normally distributed noise
- **Constant velocity model** - Works best for gradual trends
- **Market hours** - Data only updates during US trading hours

## Performance

- **Prediction speed**: <50ms per forecast (Kalman is faster than ensemble)
- **Memory usage**: ~10KB per 1000 data points
- **API rate limit**: 60 calls/min (free tier)
- **Current usage**: 6 calls/min (10-second intervals)

## Project Structure

```
monitor-ggal/
├── app.py                 # Flask app & MonitorGGAL class
├── forecaster.py          # ML forecasting models
├── test_app.py           # Comprehensive test suite
├── debug_api.py          # API connection diagnostic tool
├── requirements.txt      # Python dependencies
├── templates/
│   └── index.html        # Dark theme dashboard UI
├── CLAUDE.md            # AI assistant instructions
├── GUIA_DEPLOY_RENDER.md # Deployment guide (Spanish)
└── README.md            # This file
```

## Technologies

- **Backend**: Flask 3.0, Python 3.8+
- **Forecasting**: NumPy 1.26+ (Kalman Filter)
- **Frontend**: Vanilla JavaScript (no external libraries)
- **API**: Finnhub Stock API
- **Deployment**: Gunicorn, Render.com

## Disclaimer

⚠️ **Educational purposes only. Not financial advice.**

The Kalman Filter provides probabilistic estimates with uncertainty quantification, but should not be used as the sole basis for trading decisions. Always:
- Validate with multiple sources
- Use proper risk management
- Consult financial professionals
- Understand that Kalman assumes Gaussian noise and constant velocity

## License

MIT License - see LICENSE file for details

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Run tests: `python test_app.py`
4. Submit a pull request

## Support

- **Documentation**: [CLAUDE.md](CLAUDE.md) for architecture details
- **Issues**: Open an issue on GitHub
- **API Docs**: https://finnhub.io/docs/api

---

Built with ❤️ for learning and experimentation
