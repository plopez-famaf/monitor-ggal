# GGAL Monitor - Kalman Filter Forecasting

## Overview

Real-time price forecasting using **Kalman Filter** with configurable prediction horizons (default: 15 minutes). The system includes adaptive parameter tuning, confidence scoring, and multi-symbol support.

## What Was Added

### 1. Core Forecasting (`forecaster.py`)

**Kalman Filter Implementation:**
- State vector: `[price, velocity]` where velocity = rate of price change
- Optimal state estimation for noisy real-time data
- Configurable horizon: 1-60 minutes (default: 15 minutes)
- Tunable parameters: `process_noise`, `measurement_noise`

**Output:**
- Price prediction with 95% confidence interval
- Velocity (trend direction and strength)
- Uncertainty quantification
- Trading signal generation (BUY/SELL/HOLD with 0-100 strength)

### 2. Adaptive Parameter Tuning (see [ADAPTIVE_TUNING.md](ADAPTIVE_TUNING.md))

**Dual-Layer Auto-Tuning:**
1. **Alert Thresholds** - Adjusted based on alert accuracy (60-80% target)
2. **Model Parameters** - Kalman Filter process/measurement noise tuned based on:
   - MAPE (Mean Absolute Percentage Error)
   - Directional accuracy
   - Effectiveness index (0-100)

**Local Persistence:**
- Configuration saved to `~/.robot-ggal/config.json`
- Parameters persist across sessions
- Manual override support

### 3. Confidence Scoring System

**Alert Confidence Index (0-100):**
- **Data score** (40 points): Based on sample quantity (100+ samples = full score)
- **Uncertainty score** (30 points): Lower model uncertainty = higher score
- **Accuracy score** (30 points): Historical effectiveness index

**Confidence Levels:**
- 80-100: MUY ALTA (very high)
- 65-79: ALTA (high)
- 50-64: MEDIA (medium)
- 35-49: BAJA (low)
- 0-34: MUY BAJA (very low)

### 4. Prediction Tracking (`prediction_tracker.py`)

Validates predictions against actual outcomes:
- Calculates MAPE, MAE, RMSE
- Tracks directional accuracy
- Measures confidence interval coverage
- Generates effectiveness index (0-100)

### 5. Multi-Symbol Support (`monitor.py`)

**Unified PriceMonitor class:**
- Supports stocks (Finnhub API) and crypto (Binance API)
- Per-symbol forecasters and accuracy trackers
- Symbol switching via CLI commands

## Quick Start

### Install Dependencies

```bash
pip install -r requirements.txt
```

Key dependencies: `numpy>=1.26.0`, `rich>=13.7.0`, `pmdarima>=2.0.0`, `prompt-toolkit>=3.0.0`

### Run CLI (Primary Interface)

```bash
export FINNHUB_API_KEY="your_key_here"
python cli.py
```

**CLI Commands:**
- `status` / `s` - Current price and statistics
- `forecast` / `f` - Price predictions (default: 15-minute horizon)
- `signal` / `sig` - Trading signal with reasoning
- `accuracy` / `acc` - Model accuracy metrics
- `alert_stats` - Alert accuracy statistics
- `horizon <minutes>` - Configure forecast horizon (1-60 minutes)
- `alerts <threshold>` - Set alert threshold
- `symbols` - List available symbols
- `switch <symbol>` - Switch to different symbol
- `help` - Full command list

### Run Web Interface (Optional)

```bash
export FINNHUB_API_KEY="your_key_here"
python app.py
```

Visit http://localhost:5001 for web dashboard.

## CLI Usage Examples

### Get Current Forecast

```
ggal> forecast
┌─────────────────────────────────────────┐
│ Predicción (15 minutos)                 │
├─────────────────────────────────────────┤
│ Precio Actual:    $10.50               │
│ Precio Previsto:  $10.57               │
│ Cambio:          +0.67%                │
│ Tendencia:       ↗ up                  │
│                                         │
│ Confianza:       medium                │
│ Intervalo 95%:   $10.45 - $10.69      │
│                                         │
│ Velocidad:       +0.0047 $/min        │
└─────────────────────────────────────────┘
```

### Change Forecast Horizon

```
ggal> horizon 30
✓ Forecast horizon changed: 15 → 30 minutes
All forecasters updated to 30-minute horizon
Forecast cache cleared

ggal> forecast
┌─────────────────────────────────────────┐
│ Predicción (30 minutos)                 │
│ ...                                     │
└─────────────────────────────────────────┘
```

### Trading Signal

```
ggal> signal
┌─────────────────────────────────────────┐
│ TRADING SIGNAL                          │
├─────────────────────────────────────────┤
│ Signal:      🟢 BUY                    │
│ Strength:    75/100 ████████░░         │
│ Confidence:  medium                    │
│                                         │
│ Reason: Kalman predicts +0.67% rise    │
│         in 15 minutes                  │
│                                         │
│ Forecast: $10.50 → $10.57              │
│ Velocity: +0.0047 $/min                │
└─────────────────────────────────────────┘
```

### View Accuracy Metrics

```
ggal> accuracy
┌──────────────────────────────────────────┐
│ Model Accuracy (15-min predictions)      │
├──────────────────────────────────────────┤
│ Validated: 25 predictions                │
│                                          │
│ Effectiveness: 78.5/100 (GOOD)          │
│                                          │
│ MAPE:              0.82%                 │
│ Directional Acc:   76.0%                 │
│ CI Coverage:       94.1%                 │
│                                          │
│ Summary: Good, reliable predictions      │
└──────────────────────────────────────────┘
```

## Technical Details

### Kalman Filter Approach

**Why Kalman Filter:**
- Mathematically proven optimal state estimator (minimizes mean squared error)
- Recursive updates (no recomputation of full history)
- Real-time friendly (<50ms predictions)
- Used in production: GPS, autopilot, rocket guidance

**How it Works:**
1. **Predict**: Projects state forward using motion model
2. **Update**: Corrects prediction with new measurement
3. **Optimal Balance**: Weights prediction vs measurement based on uncertainties
4. **State Vector**: `[price, velocity]` tracks both value and trend

**Model Parameters:**
- `process_noise` (0.01-0.05): Controls model adaptability to trend changes
- `measurement_noise` (0.05-0.3): Controls trust in measurements vs predictions

### Adaptive Tuning System

**Layer 1: Alert Thresholds**
- Target: 60-80% alert accuracy
- Increase threshold if too many false positives (<60% accuracy)
- Decrease threshold if system too conservative (>80% accuracy)

**Layer 2: Model Parameters**
- High MAPE (>1.5%) → Increase measurement noise (trust data more)
- Low directional accuracy (<55%) → Increase process noise (more dynamic)
- Excellent performance (MAPE <0.5%, dir.acc ≥75%) → Decrease measurement noise (trust model)

**Evaluation Metrics:**
- **MAPE**: Mean Absolute Percentage Error (price accuracy)
- **Directional Accuracy**: % correct trend predictions
- **Effectiveness Index**: Composite score (0-100) combining all metrics

### Performance Characteristics

- **Prediction Speed**: <50ms per forecast
- **Memory Usage**: ~30KB per symbol (1000 price points)
- **Minimum Data**: 10 samples for Kalman, 30 for Ensemble
- **Accuracy**: Typically 60-75% directional accuracy after tuning
- **Best Conditions**: Stable markets with gradual trends
- **Worst Conditions**: Sudden news events, market gaps, high volatility

### Design Philosophy

✅ **Mathematically Optimal**
- Kalman Filter = maximum likelihood estimator under Gaussian noise
- Provably minimizes estimation error

✅ **Adaptive & Self-Improving**
- Automatic parameter tuning based on performance
- Learns from mistakes (false alerts drive threshold adjustments)
- Configuration persists across sessions

✅ **Production-Ready**
- Minimal dependencies (numpy, rich, pmdarima)
- Error handling and graceful degradation
- Multi-symbol support with per-symbol tracking

## Limitations

- **Short-term predictions**: Optimized for 15-minute horizon (configurable 1-60 min)
- **Gaussian assumption**: Kalman optimal under Gaussian noise (may not hold during extreme events)
- **Linear motion model**: Assumes constant velocity (works poorly with sudden reversals)
- **Market hours**: Only useful when market is actively trading
- **Probabilistic**: Predictions are estimates with uncertainty, not guarantees

## Key Files

- [cli.py](cli.py) - Primary CLI interface (~1200 lines)
- [forecaster.py](forecaster.py) - Kalman Filter forecaster (~310 lines)
- [ensemble_forecaster.py](ensemble_forecaster.py) - Kalman + Auto-ARIMA ensemble (~180 lines)
- [prediction_tracker.py](prediction_tracker.py) - Accuracy tracking (~335 lines)
- [monitor.py](monitor.py) - Multi-symbol price monitoring (~200 lines)
- [ADAPTIVE_TUNING.md](ADAPTIVE_TUNING.md) - Adaptive tuning documentation
- [CLAUDE.md](CLAUDE.md) - Development guide

## Configuration Files

- `~/.robot-ggal/config.json` - Tuned parameters (alert threshold, model parameters)
- `~/.robot-ggal/alert_accuracy.json` - Alert validation history
- Environment variables:
  - `FINNHUB_API_KEY` - Required for stock data
  - `ALERT_THRESHOLD` - Initial alert threshold (default: 0.1%)
  - `FORECAST_HORIZON` - Default horizon in minutes (default: 15)
  - `ADAPTIVE_TUNING` - Enable/disable auto-tuning (default: true)

## Future Enhancements

Potential improvements (not yet implemented):
- Per-symbol alert thresholds (different for GGAL vs BTC)
- Time-of-day adjustments (different thresholds for market open/close)
- Volatility-aware thresholds (higher during high volatility)
- Extended Kalman Filter for non-linear models
- Particle filter for non-Gaussian noise
- Multi-symbol correlation analysis
- Backtesting framework with historical data
- Database persistence for long-term analysis

---

**Educational purposes only. Not financial advice. Past performance does not guarantee future results.**
