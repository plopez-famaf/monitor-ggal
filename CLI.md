# GGAL Monitor - CLI Interface

**Interfaz REPL minimalista para monitoreo de GGAL con Kalman Filter forecasting y validación de predicciones.**

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set API key (required)
export FINNHUB_API_KEY="your_api_key_here"

# Run CLI (Kalman Filter only - default)
python cli.py

# Run CLI with AutoML (Ensemble: Kalman + Auto-ARIMA)
export USE_AUTOML=true
python cli.py
```

## Usage

La CLI inicia un REPL interactivo con monitoreo en background (polling cada 10s):

```
GGAL Monitor CLI - Kalman Filter Forecasting

Background monitoring started (10s interval)
Type 'help' for commands, 'quit' to exit

ggal> _
```

## Effectiveness Index ⭐ NEW

El sistema ahora incluye un **Índice de Efectividad (0-100)** que mide la calidad de las predicciones en tiempo real:

- **Directional Accuracy (33.3%)**: ¿Predijimos correctamente si el precio subiría/bajaría?
- **Price Accuracy (33.3%)**: ¿Qué tan cerca estuvo el precio predicho del real? (basado en MAPE)
- **Calibration (33.3%)**: ¿El precio real cayó dentro del intervalo de confianza 95%?

**Ratings:**
- 80-100: EXCELLENT
- 70-79: GOOD
- 60-69: FAIR
- 50-59: POOR
- 0-49: VERY POOR

### Available Commands

| Command | Alias | Description |
|---------|-------|-------------|
| `status` | `s` | Current price + effectiveness index |
| `forecast` | `f` | 5-minute price forecast (fixed horizon) |
| `signal` | `sig` | Trading signal (BUY/SELL/HOLD) |
| `accuracy` | `acc` | Detailed effectiveness index breakdown |
| `stats` | - | Statistics (max, min, avg, range) |
| `metrics` | `m` | Same as accuracy |
| `history` | `h` | Recent price history (last 10) |
| `help` | - | Show help |
| `quit` | `q` | Exit |

### Examples

**Check current price with effectiveness:**
```
ggal> status
↗ $45.67 +0.34 (+0.75%) | 14:23:45

Prediction Effectiveness: ████████░░ 82/100 (GOOD)
  ├─ Direction: 15/20 correct (75.0%)
  ├─ Accuracy: MAPE 0.34% (excellent)
  └─ Calibration: 90% within CI (optimal)
```

**Get 5-minute forecast:**
```
ggal> forecast
Forecast at: 14:23:45
Target time: 14:28:45
Horizon:     5 min (fixed)
Current:     $45.67
Predicted:   ↗ $45.92
Change:      +0.25 (+0.55%)
Velocity:    0.0025 $/min
IC 95%:      $45.68 - $46.16
Trend:       UP
Model:       Kalman Filter
```

**With AutoML enabled:**
```
ggal> forecast
Forecast at: 14:23:45
Target time: 14:28:45
Horizon:     5 min (fixed)
Current:     $45.67
Predicted:   ↗ $45.89
Change:      +0.22 (+0.48%)
Velocity:    0.0022 $/min
IC 95%:      $45.65 - $46.13
Trend:       UP
Model:       Ensemble (Kalman + Auto-ARIMA)
ARIMA order: (2, 1, 1)
```

**Effectiveness index breakdown:**
```
ggal> accuracy

Prediction Effectiveness Index
████████░░ 82/100 (GOOD)

Component Scores:
  ▸ Direction: 75.0% (15/20 correct)
  ▸ Price Accuracy: MAPE 0.34% (MAE $0.015)
  ▸ Calibration: 90.0% within 95% CI

Good: Reliable predictions
Based on 20 validated predictions (5-min horizon)
```

**Trading signal:**
```
ggal> signal
BUY ████████████████████ 82/100
Strong upward momentum with low uncertainty
```

**Statistics:**
```
ggal> stats
Samples:  127
Max:      $46.12
Min:      $44.89
Avg:      $45.23
Range:    $1.23
```

**Model accuracy (alias for 'accuracy'):**
```
ggal> metrics
(Same output as 'accuracy' command)
```

**Price history:**
```
ggal> history
┏━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┓
┃ Time     ┃  Price ┃ Change            ┃
┡━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━━┩
│ 14:20:15 │ $45.34 │ +0.12 (+0.26%)    │
│ 14:20:25 │ $45.41 │ +0.19 (+0.42%)    │
│ 14:20:35 │ $45.67 │ +0.45 (+0.99%)    │
└──────────┴────────┴───────────────────┘
```

## AutoML Mode (Optional)

El sistema incluye un modo **AutoML** que utiliza Auto-ARIMA para selección automática de parámetros:

### ¿Cuándo usar AutoML?

**Usar Kalman Filter (default):**
- Startup rápido (1s)
- Baja latencia (<50ms por forecast)
- Menor uso de memoria (~30MB)
- Óptimo para trading de alta frecuencia

**Usar AutoML Ensemble:**
- Mejor accuracy potencial
- Combina Kalman + Auto-ARIMA
- Reentrenamiento automático cada 10 datos
- Requiere 30+ muestras (vs 10 para Kalman)
- Latencia: ~100-150ms (primera vez: 2-5s)

### Activación

```bash
export USE_AUTOML=true
python cli.py
```

### Componentes del Ensemble

El Ensemble combina:
1. **Kalman Filter** (40% peso): Rápido, suave, bueno para tendencias
2. **Auto-ARIMA** (60% peso): Adaptativo, encuentra mejor orden (p,d,q)

Los pesos se pueden ajustar automáticamente basados en effectiveness index.

## CLI Features

### Command History & Autocomplete

La CLI incluye:
- **Historial de comandos**: Usa ↑/↓ para navegar comandos anteriores
- **Autocompletado**: Presiona Tab para autocompletar comandos
- **Comandos guardados en memoria**: Persisten durante la sesión

Ejemplos:
```
ggal> for[TAB]        → forecast
ggal> sw[TAB] btc[TAB] → switch btc
```

### Timestamps

Todos los forecasts muestran:
- **Forecast at**: Hora en que se generó la predicción
- **Target time**: Hora objetivo (forecast at + 5 min)

Esto permite validar fácilmente las predicciones manualmente.

## Architecture

```
cli.py                  # REPL interface (this module)
monitor.py              # Background price polling
forecaster.py           # Kalman Filter forecasting
automl_forecaster.py    # Auto-ARIMA forecasting
ensemble_forecaster.py  # Ensemble (Kalman + AutoML)
prediction_tracker.py   # Accuracy validation
app.py                  # Flask API (optional, for web interface)
```

### Design Philosophy

- **Minimal boilerplate**: ~250 lines total
- **Maximum performance**: Rich rendering + background threading
- **No dependencies bloat**: Only `rich` library for UI
- **Zero configuration**: Just set API key and run

### Performance

- Startup time: ~1 second
- Command latency: <50ms (data already in memory)
- Memory footprint: ~30MB (1000 price points)
- Background polling: 10s interval (configurable)

## Requirements

- Python 3.10+
- Finnhub API key (free tier: 60 calls/min)
- Terminal with Unicode support (for arrows/bars)

## Advanced Usage

**One-shot commands (future):**
```bash
python cli.py --command status
python cli.py --command "forecast 10"
```

**Custom polling interval (future):**
```bash
python cli.py --interval 5  # Poll every 5 seconds
```

## Troubleshooting

**"Waiting for data..."**
- Normal on startup, wait 10-30 seconds for first API call
- Check API key: `echo $FINNHUB_API_KEY`

**"Need at least 10/15 data points"**
- Forecast needs 10 points (~2 minutes of monitoring)
- Trading signal needs 15 points (~3 minutes)

**No price updates**
- Check if market is open (Mon-Fri 9:30 AM - 4:00 PM ET)
- Outside market hours, prices stay frozen at last close

**"API key inválida"**
- Get free key at: https://finnhub.io
- Demo token no longer works (401 Unauthorized)

## Comparison: CLI vs Web

| Feature | CLI | Web (app.py) |
|---------|-----|--------------|
| Startup time | 1s | 3s |
| Memory usage | 30MB | 60MB |
| Dependencies | rich | Flask + rich |
| Browser required | ❌ | ✅ |
| SSH-friendly | ✅ | ❌ |
| Scriptable | ✅ | ⚠️ (API only) |
| Charts | Text | Chart.js |
| Auto-refresh | Background | JavaScript polling |

**Recommendation:** Use CLI for development/monitoring, Web for dashboards.

## License

Same as parent project (see README.md)
