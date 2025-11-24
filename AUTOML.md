# AutoML Integration Guide

**Automated Machine Learning for time series forecasting using Auto-ARIMA + Kalman Filter ensemble.**

## Overview

The robot-ggal project now supports **AutoML mode** which automatically selects optimal forecasting models and hyperparameters. This is implemented through an ensemble approach combining:

1. **Kalman Filter** - Fast, optimal state estimation
2. **Auto-ARIMA** - Automatic ARIMA model selection using pmdarima

## Quick Start

```bash
# Install dependencies (includes pmdarima)
pip install -r requirements.txt

# Enable AutoML mode
export FINNHUB_API_KEY="your_key"
export USE_AUTOML=true
python cli.py
```

## Architecture

### Three Forecaster Options

| Forecaster | Min Samples | Latency | Memory | Use Case |
|------------|-------------|---------|--------|----------|
| `GGALForecaster` (Kalman) | 10 | <50ms | 30MB | High-frequency, default |
| `AutoMLForecaster` (ARIMA) | 30 | ~100ms | 45MB | Standalone AutoML |
| `EnsembleForecaster` | 30 | ~150ms | 50MB | Best accuracy |

### Ensemble Strategy

The ensemble uses **weighted averaging** of predictions:

```python
ensemble_price = kalman_pred * 0.4 + automl_pred * 0.6
```

**Weights can be dynamically adjusted** based on effectiveness index:

```python
forecaster.update_weights(
    kalman_effectiveness=75,  # 0-100
    automl_effectiveness=85   # 0-100
)
# New weights: 75/(75+85) = 0.47 Kalman, 0.53 AutoML
```

## Auto-ARIMA Details

### Model Selection

Auto-ARIMA automatically finds optimal `(p, d, q)` parameters:

- **p**: AR (autoregressive) order
- **d**: Differencing order (for stationarity)
- **q**: MA (moving average) order

Search constraints (for performance):
```python
max_p=5     # Max AR order
max_d=2     # Max differencing
max_q=5     # Max MA order
stepwise=True  # Faster stepwise search
```

### Retraining Strategy

**Incremental retraining** every 10 new data points:

```python
def _should_retrain(self, n_samples):
    return self.model is None or (n_samples - self.last_train_size) >= 10
```

This balances:
- **Model freshness**: Adapts to recent market changes
- **Performance**: Avoids constant retraining overhead

### Confidence Intervals

Auto-ARIMA returns **native 95% confidence intervals**:

```python
forecast_result = model.predict(
    n_periods=1,
    return_conf_int=True,
    alpha=0.05  # 95% CI
)
predicted_price = forecast_result[0][0]
conf_int = forecast_result[1][0]  # [lower, upper]
```

## Performance Comparison

### Startup Time

| Mode | Time | Reason |
|------|------|--------|
| Kalman only | ~1s | Direct initialization |
| AutoML enabled | ~3-5s | Initial ARIMA model fit |

### Forecast Latency

| Mode | First Call | Cached |
|------|------------|--------|
| Kalman | 20-50ms | 20-50ms |
| Auto-ARIMA | 2-5s | 80-120ms |
| Ensemble | 2-5s | 100-150ms |

**Note**: First AutoML call is slow (model fitting), subsequent calls are fast (cached model).

### Memory Usage

| Component | Memory |
|-----------|--------|
| Base CLI | 30MB |
| + Kalman Filter | +5MB per symbol |
| + Auto-ARIMA | +15MB per symbol |
| **Total (Ensemble, 2 symbols)** | **~70MB** |

## Trade-offs

### When to Use Kalman Only (Default)

✅ **Advantages:**
- Fast startup (1s)
- Low latency (<50ms)
- Minimal memory (30MB)
- Works with 10 data points
- Mathematically optimal for linear trends

❌ **Limitations:**
- Assumes constant velocity
- No parameter adaptation
- Poor for complex patterns

### When to Use AutoML Ensemble

✅ **Advantages:**
- Better accuracy potential
- Adapts to market patterns
- Automatic parameter tuning
- Combines multiple models

❌ **Limitations:**
- Slower startup (3-5s)
- Higher latency (100-150ms)
- More memory (50-70MB)
- Needs 30 data points

## Implementation Details

### File Structure

```
automl_forecaster.py      # Auto-ARIMA implementation
ensemble_forecaster.py    # Weighted ensemble
forecaster.py             # Kalman Filter (baseline)
```

### Ensemble Forecaster API

```python
from ensemble_forecaster import EnsembleForecaster

forecaster = EnsembleForecaster(min_samples=30, horizon_minutes=5)

# Generate forecast
forecast = forecaster.forecast(historial)

# Result includes both models
{
    'prediction': 45.89,
    'model_type': 'Ensemble (Kalman + Auto-ARIMA)',
    'components': {
        'kalman': {'prediction': 45.92, 'weight': 0.4},
        'automl': {'prediction': 45.87, 'weight': 0.6, 'order': '(2, 1, 1)'}
    }
}

# Update weights dynamically
forecaster.update_weights(
    kalman_effectiveness=80,
    automl_effectiveness=85
)
```

### AutoML Forecaster API

```python
from automl_forecaster import AutoMLForecaster

forecaster = AutoMLForecaster(min_samples=30)

# Generate forecast
forecast = forecaster.forecast(historial)

# Result includes ARIMA order
{
    'prediction': 45.87,
    'model_type': 'Auto-ARIMA',
    'model_order': '(2, 1, 1)',  # ARIMA(p,d,q)
    'confidence': 'high'
}
```

## CLI Usage

### Commands Work Identically

All CLI commands work the same in both modes:

```bash
# Kalman mode
python cli.py
ggal> forecast

# AutoML mode
USE_AUTOML=true python cli.py
ggal> forecast
```

### Output Differences

**Kalman output:**
```
Model:       Kalman Filter
```

**AutoML output:**
```
Model:       Ensemble (Kalman + Auto-ARIMA)
ARIMA order: (2, 1, 1)
```

## Future Enhancements

Possible improvements:

- [ ] **LightGBM/XGBoost**: Gradient boosting for non-linear patterns
- [ ] **LSTM/GRU**: Deep learning for complex sequences
- [ ] **Prophet**: Facebook's time series library
- [ ] **Dynamic weighting**: Auto-adjust ensemble based on effectiveness
- [ ] **Feature engineering**: Add technical indicators (RSI, MACD, etc.)
- [ ] **Multi-horizon**: Optimize different models for 1/5/10 min
- [ ] **Online learning**: Update models incrementally without full retrain

## Troubleshooting

### "Need at least 30 data points"

AutoML requires more samples than Kalman (30 vs 10). Wait ~5 minutes for data collection.

**Workaround**: Falls back to Kalman if < 30 samples available.

### Slow first forecast

Auto-ARIMA fitting takes 2-5 seconds initially. This is normal.

**Solution**: Model is cached, subsequent forecasts are fast (~100ms).

### High memory usage

Each symbol with AutoML uses ~25MB (vs 10MB with Kalman).

**Solution**: Disable AutoML if monitoring many symbols (>5).

### Forecast fails

Check:
1. Enough data points? (`len(monitor.historial) >= 30`)
2. ARIMA convergence? (check console for pmdarima warnings)
3. Price variance? (constant prices cause ARIMA issues)

## References

- **pmdarima**: https://alkaline-ml.com/pmdarima/
- **ARIMA theory**: Box-Jenkins methodology
- **Kalman Filter**: Optimal state estimation (1960)

---

**Educational purposes only. Not financial advice.**
