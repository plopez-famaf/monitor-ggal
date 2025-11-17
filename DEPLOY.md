# Quick Deployment Guide

## ✅ Pre-Deployment Verification

Run the verification script to ensure everything is ready:

```bash
python3 verify_deployment.py
```

Should output: **✅ ALL CHECKS PASSED - Ready for deployment!**

## 🚀 Deploy to Render.com

### Step 1: Commit Changes

```bash
git add .
git commit -m "Add ML forecasting with dark theme UI

- Implemented 5-model ensemble forecasting (MA, ES, LR, momentum, mean reversion)
- Added /api/forecast and /api/trading-signal endpoints
- Redesigned UI with dark minimalistic theme
- Added comprehensive test suite (30+ tests)
- Updated documentation"

git push origin main
```

### Step 2: Render Configuration

If this is your first deploy, configure Render with:

- **Environment**: Python 3
- **Build Command**: (leave blank - uses default)
- **Start Command**: `gunicorn app:app`
- **Environment Variables**:
  - `FINNHUB_API_KEY`: Your Finnhub API key

### Step 3: Verify Deployment

Once deployed, test the endpoints:

```bash
# Replace with your Render URL
RENDER_URL="https://your-app.onrender.com"

# Health check
curl $RENDER_URL/api/health

# Wait 2-3 minutes for data collection, then:
curl $RENDER_URL/api/forecast
curl $RENDER_URL/api/trading-signal
```

## 🧪 Local Testing (Optional)

### Install Dependencies

```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Run Tests

```bash
python test_app.py
```

Expected: All tests pass (30+ test cases)

### Run Locally

```bash
export FINNHUB_API_KEY="your_api_key_here"
python app.py
```

Visit: http://localhost:5000

## 📊 What's New

### New Features
- **ML Forecasting**: 5 statistical models predicting 1, 5, 10 minute horizons
- **Trading Signals**: BUY/SELL/HOLD recommendations with reasoning
- **Dark Theme**: Minimalistic UI with #0a0e27 background
- **Technical Indicators**: RSI, Momentum, Volatility, Moving Averages

### New API Endpoints
- `GET /api/forecast` - Multi-horizon price predictions
- `GET /api/trading-signal` - Trading recommendations

### New Files
- `forecaster.py` - ML forecasting engine (380 lines)
- `test_app.py` - Comprehensive test suite (322 lines)
- `verify_deployment.py` - Pre-deployment checks
- `FORECAST_README.md` - Feature documentation
- `CLAUDE.md` - Updated with forecasting details

### Modified Files
- `app.py` - Added forecast/signal endpoints
- `templates/index.html` - Dark theme + forecast UI
- `requirements.txt` - Added numpy

## 📈 Usage

After deployment and 2-3 minutes of data collection:

1. **Dashboard**: View real-time prices with dark theme
2. **5-min Forecast**: See predicted price in 5 minutes
3. **Trading Signal**: Get BUY/SELL/HOLD recommendation
4. **Price Chart**: Interactive chart with predictions

## ⚠️ Important Notes

- **Market Hours**: Predictions only work during US market hours
- **Data Requirement**: Needs 10+ data points (~2 minutes) for forecasts
- **Signal Requirement**: Needs 15+ data points (~2.5 minutes) for trading signals
- **Accuracy**: 60-70% directional accuracy in stable markets
- **Educational Only**: Not financial advice

## 🔧 Troubleshooting

### "Insufficient data" error
- Wait 2-3 minutes after deployment for data collection
- Check Finnhub API is responding (market hours)

### Forecasts not appearing
- Check browser console for API errors
- Verify `/api/forecast` returns 200 (not 202)
- Ensure numpy is installed on Render

### Tests failing locally
- Install all dependencies: `pip install -r requirements.txt`
- Ensure numpy version matches: `1.24.3`

## 📚 Documentation

- [FORECAST_README.md](FORECAST_README.md) - Detailed feature guide
- [CLAUDE.md](CLAUDE.md) - Architecture & implementation details
- [GUIA_DEPLOY_RENDER.md](GUIA_DEPLOY_RENDER.md) - Original deployment guide

---

**Ready to deploy! 🚀**
