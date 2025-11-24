# Adaptive Parameter Tuning

**Automatic self-learning system that optimizes both alert thresholds AND model parameters based on accuracy.**

## Overview

The CLI now includes a **dual-layer adaptive tuning system** that automatically adjusts:
1. **Alert thresholds** based on alert accuracy (when to trigger alerts)
2. **Kalman Filter parameters** based on prediction accuracy (how the model forecasts)

This eliminates the need for manual parameter tuning and ensures the system continuously improves over time.

## Features

### 1. Alert Accuracy Tracking

Every triggered alert is validated after 5 minutes:
- **Direction**: Did we predict the correct price movement direction?
- **Magnitude**: Did the actual price change exceed the threshold?
- **Combined accuracy**: Alert is "correct" if BOTH conditions are met

### 2. Prediction Accuracy Tracking

Every forecast is validated after 5 minutes:
- **MAPE** (Mean Absolute Percentage Error): Price prediction accuracy
- **Directional Accuracy**: Did we predict correct movement direction?
- **Effectiveness Index**: Composite score (0-100) combining all metrics

### 3. Dual-Layer Parameter Adjustment

After every **10 validated alerts**, the system analyzes both alert and prediction performance:

#### Layer 1: Alert Threshold Tuning

| Scenario | Condition | Action | Logic |
|----------|-----------|--------|-------|
| **Low Accuracy** | Overall < 60% | Increase threshold by 20% | Too many false positives - be more conservative |
| **Recent Decline** | Overall ≥ 70% but recent < 50% | Increase threshold by 10% | Performance degrading - adjust slightly |
| **High Accuracy** | Overall ≥ 80% | Decrease threshold by 5% | System working well - can be more sensitive |
| **Stable** | Between 60-80% | No change | Parameters are within acceptable range |

**Limits:**
- Minimum threshold: 0.05% (prevents over-sensitivity)
- Maximum threshold: 2.0% (prevents under-sensitivity)

#### Layer 2: Model Parameter Tuning (Kalman Filter)

| Scenario | Condition | Action | Effect |
|----------|-----------|--------|--------|
| **High Prediction Error** | MAPE > 1.5% | Increase measurement noise by 15% | Trust measurements more, predictions less |
| **Low Directional Accuracy** | Dir. accuracy < 55% | Increase process noise by 25% | Allow more dynamic changes in trends |
| **Excellent Performance** | MAPE < 0.5% AND dir. acc. ≥ 75% | Decrease measurement noise by 10% | Trust model more |

**Parameter Limits:**
- Process noise: 0.01 - 0.05 (controls model adaptability)
- Measurement noise: 0.05 - 0.3 (controls trust in measurements vs predictions)

**Works with both:**
- **Kalman Filter** (default): Adjusts KF parameters directly
- **Ensemble (Kalman + Auto-ARIMA)**: Adjusts internal Kalman component

### 3. Local Persistence

Tuned parameters are saved to `~/.robot-ggal/config.json`:

```json
{
  "alert_threshold": 0.12,
  "last_updated": "2025-01-24T14:23:45.123456",
  "forecaster_params": {
    "process_noise": 0.01,
    "measurement_noise": 0.1
  }
}
```

- **Automatic loading**: Configuration loaded on CLI startup
- **Cross-session**: Parameters persist between CLI runs
- **Version control safe**: Config stored in home directory, not repo

### 4. Manual Override

You can always manually adjust settings:

```bash
# Set custom threshold
ggal> alerts 0.5

# This will be saved and used as the new baseline
# Adaptive tuning will continue from this value
```

## Commands

### `alert_stats` - View Alert Accuracy

```
ggal> alert_stats

Alert Accuracy Statistics

Overall Accuracy: ████████░░ 78.5% (GOOD)
  ├─ Correct: 11/14 alerts
  ├─ Recent: 8/10 (last 10 validated)
  └─ Pending: 3 alerts awaiting validation

┏━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━┓
┃ Symbol┃ Validated ┃ Correct┃ Accuracy ┃
┡━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━┩
│ GGAL  │         8 │      6 │   75.0%  │
│ BTC   │         6 │      5 │   83.3%  │
└───────┴───────────┴────────┴──────────┘

✓ Alert system performing well
Current configuration is effective
```

**Metrics explained:**
- **Overall Accuracy**: All-time correct alerts / validated alerts
- **Recent**: Last 10 validated alerts (shows trending performance)
- **Pending**: Alerts waiting for 5-minute validation period
- **Per-symbol**: Breakdown by each monitored asset

## Configuration

### Enable/Disable Adaptive Tuning

```bash
# Enable (default)
export ADAPTIVE_TUNING=true
python cli.py

# Disable (manual control only)
export ADAPTIVE_TUNING=false
python cli.py
```

When disabled:
- Alert threshold remains fixed
- You must manually adjust via `alerts <threshold>` command
- Configuration is still saved/loaded (just not auto-adjusted)

### Initial Alert Threshold

```bash
# Set starting threshold (default: 0.1%)
export ALERT_THRESHOLD=0.15
python cli.py
```

This sets the initial value. Adaptive tuning will adjust from here.

## Example Scenarios

### Scenario 1: System Learning Phase

**First 10 alerts:** Accuracy = 45% (many false positives)

```
🔧 Auto-Tuning Triggered
Alert accuracy: 45.0% (recent: 40.0%)

⚠️  Low accuracy detected - increasing alert threshold
Threshold: 0.10% → 0.12%
Configuration saved to ~/.robot-ggal/config.json
```

**Next 10 alerts:** Accuracy improves to 72%

```
🔧 Auto-Tuning Triggered
Alert accuracy: 72.0% (recent: 80.0%)

✓ Parameters within acceptable range
```

**Result:** System stabilized at 0.12% threshold with good accuracy.

### Scenario 2: Market Volatility Change

**Previous 30 alerts:** Accuracy = 85% (stable market)

**Market becomes volatile, next 10 alerts:** Recent accuracy drops to 45%

```
🔧 Auto-Tuning Triggered
Alert accuracy: 76.0% (recent: 45.0%)

⚠️ Recent performance decline - adjusting threshold
Threshold: 0.12% → 0.13%
Configuration saved to ~/.robot-ggal/config.json
```

**Result:** System adapts to new market conditions automatically.

### Scenario 3: High Performance Optimization

**Accuracy consistently > 85% for 30+ alerts**

```
🔧 Auto-Tuning Triggered
Alert accuracy: 87.5% (recent: 90.0%)

✓ High accuracy - optimizing sensitivity
Threshold: 0.13% → 0.12%
Configuration saved to ~/.robot-ggal/config.json
```

**Result:** System becomes more sensitive without sacrificing accuracy.

### Scenario 4: Model Parameter Adjustment (High Error)

**Prediction MAPE = 2.1%, Directional accuracy = 65%**

```
🔧 Auto-Tuning Triggered
Alert accuracy: 72.0% (recent: 70.0%)
Prediction effectiveness: 68.5/100 (MAPE: 2.10%)

⚠️  High prediction error (MAPE 2.10%) - adjusting model
Measurement noise: 0.100 → 0.115 (trust measurements more)
Configuration saved to ~/.robot-ggal/config.json
```

**Explanation:** Model predictions are less accurate, so we increase measurement noise to rely more on actual price measurements and less on model predictions.

### Scenario 5: Model Parameter Optimization (Low Error)

**Prediction MAPE = 0.4%, Directional accuracy = 82%**

```
🔧 Auto-Tuning Triggered
Alert accuracy: 85.0% (recent: 88.0%)
Prediction effectiveness: 87.2/100 (MAPE: 0.40%)

✓ Excellent predictions (MAPE 0.40%) - optimizing model
Measurement noise: 0.115 → 0.104 (trust model more)
Configuration saved to ~/.robot-ggal/config.json
```

**Explanation:** Model is highly accurate, so we can decrease measurement noise to trust the model's predictions more.

### Scenario 6: Poor Directional Accuracy

**MAPE = 0.8%, Directional accuracy = 48%**

```
🔧 Auto-Tuning Triggered
Alert accuracy: 58.0% (recent: 45.0%)
Prediction effectiveness: 62.3/100 (MAPE: 0.80%)

⚠️  Low directional accuracy (48.0%) - increasing adaptability
Process noise: 0.010 → 0.013 (more dynamic)

⚠️  Low alert accuracy - increasing threshold
Alert threshold: 0.10% → 0.12%
Configuration saved to ~/.robot-ggal/config.json
```

**Explanation:** Model is failing to predict price direction even though magnitude is OK. We increase process noise to allow the model to adapt faster to trend changes. Also increase alert threshold since alerts are inaccurate.

## Technical Details

### Validation Logic

An alert is considered **correct** if:

1. **Direction match**: Predicted direction (↗/↘) matches actual direction
2. **Threshold exceeded**: `abs(actual_change_pct) >= original_threshold`

Example:
```
Alert predicted: +0.15% (threshold 0.1%)
Actual change: +0.18%
Result: ✓ CORRECT (direction matched AND exceeded threshold)

Alert predicted: +0.15% (threshold 0.1%)
Actual change: +0.08%
Result: ✗ INCORRECT (direction matched but did NOT exceed threshold)

Alert predicted: +0.15% (threshold 0.1%)
Actual change: -0.20%
Result: ✗ INCORRECT (direction did NOT match)
```

### Tuning Frequency

- **Check interval**: Every 10 validated alerts
- **Minimum data**: Requires at least 10 validated alerts before first tuning
- **Validation delay**: 5 minutes after alert is triggered

**Timeline example:**
```
00:00 - Alert 1 triggered
00:30 - Alert 2 triggered
01:00 - Alert 3 triggered
...
05:00 - Alert 1 validated (5 min passed)
...
05:30 - Alert 10 triggered
10:30 - Alert 10 validated
10:30 - 🔧 Auto-Tuning runs (10 alerts validated)
```

### Thread Safety

- Alert validation runs in background forecasting thread
- Configuration file writes are atomic (JSON dump)
- No race conditions (single-threaded CLI)

## Benefits

1. **Zero-configuration**: Works out-of-the-box, no manual tuning needed
2. **Adapts to markets**: Automatically adjusts to changing market conditions
3. **Learns from mistakes**: False positives/negatives drive improvements
4. **Cross-session learning**: Improvements persist between CLI runs
5. **Transparent**: Clear logging of all tuning decisions
6. **Safe limits**: Built-in min/max thresholds prevent extreme adjustments

## Comparison with Fixed Thresholds

| Aspect | Fixed Threshold | Adaptive Tuning |
|--------|----------------|-----------------|
| Setup | Manual trial-and-error | Automatic |
| Market changes | Manual re-tuning | Automatic adaptation |
| Performance tracking | User must monitor | Built-in `alert_stats` |
| Optimization | Static | Continuous improvement |
| False positives | User must adjust | Self-correcting |
| Learning curve | High | Low |

## Limitations

1. **Requires data**: Needs at least 10 validated alerts before first tuning
2. **Reactive, not predictive**: Adjusts based on past performance
3. **Single parameter**: Only tunes alert threshold (not forecaster internals)
4. **Conservative**: Prefers false negatives over false positives

## Future Enhancements

Potential improvements:
- [ ] Tune Kalman Filter process/measurement noise
- [ ] Adjust ensemble weights based on per-model accuracy
- [ ] Per-symbol thresholds (different for GGAL vs BTC)
- [ ] Time-of-day adjustments (different thresholds for market open/close)
- [ ] Volatility-aware thresholds (higher threshold during high volatility)
- [ ] Machine learning for multi-parameter optimization

---

**Educational purposes only. Not financial advice.**
