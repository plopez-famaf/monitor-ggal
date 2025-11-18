from flask import Flask, jsonify, render_template
import requests
import threading
import time
from datetime import datetime
from collections import deque
import os
import sys
from forecaster import GGALForecaster
from prediction_tracker import PredictionTracker

# Force unbuffered output for immediate logging visibility
import functools
print = functools.partial(print, flush=True)

app = Flask(__name__)

class MonitorGGAL:
    def __init__(self, api_key):
        self.api_key = api_key
        self.symbol = "GGAL"
        self.historial = deque(maxlen=1000)
        self.running = False
    
    def obtener_precio(self):
        try:
            response = requests.get(
                "https://finnhub.io/api/v1/quote",
                params={
                    "symbol": self.symbol,
                    "token": self.api_key
                },
                timeout=5
            )
            data = response.json()

            # Check for API errors
            if "error" in data:
                print(f"❌ Finnhub API Error: {data['error']}")
                if response.status_code == 401:
                    print(f"   → API key inválida. Configura: export FINNHUB_API_KEY='tu_key'")
                return None

            if "c" in data and data["c"] > 0:
                return {
                    "timestamp": datetime.now().isoformat(),
                    "price": data.get("c", 0),
                    "high": data.get("h", 0),
                    "low": data.get("l", 0),
                    "open": data.get("o", 0),
                    "change": round(data.get("c", 0) - data.get("pc", 0), 2),
                    "change_percent": round((data.get("c", 0) - data.get("pc", 0)) / data.get("pc", 1) * 100, 2)
                }
            elif "c" in data and data["c"] == 0:
                print(f"⚠️  Precio = 0 (mercado cerrado o símbolo no disponible)")
                return None

        except Exception as e:
            print(f"Error obteniendo precio: {e}")
        return None
    
    def monitorear_background(self, intervalo=10):
        self.running = True
        print(f"Iniciando monitoreo de {self.symbol}...")
        print(f"API key length: {len(self.api_key)}, Is demo: {self.api_key == 'demo'}")

        while self.running:
            try:
                precio = self.obtener_precio()
                if precio:
                    self.historial.append(precio)
                    print(f"[{precio['timestamp']}] Precio: ${precio['price']:.2f} (historial size: {len(self.historial)})")
                else:
                    print(f"⚠️  obtener_precio() returned None")
            except Exception as e:
                print(f"❌ Error in monitorear_background: {e}")
            time.sleep(intervalo)
    
    def obtener_historial(self):
        return list(self.historial)

# Obtener API key desde variable de entorno
api_key = os.environ.get('FINNHUB_API_KEY')
if not api_key:
    print("=" * 60)
    print("⚠️  ADVERTENCIA: FINNHUB_API_KEY no está configurada")
    print("=" * 60)
    print("La app se iniciará pero NO OBTENDRÁ DATOS.")
    print("El token 'demo' ya no funciona (401 Unauthorized).")
    print()
    print("Para obtener datos reales:")
    print("  1. Registra una API key gratis en: https://finnhub.io")
    print("  2. Configura la variable: export FINNHUB_API_KEY='tu_key'")
    print("  3. Reinicia la app: python app.py")
    print()
    print("Para diagnosticar: python debug_api.py")
    print("=" * 60)
    api_key = "demo"

monitor = MonitorGGAL(api_key=api_key)
forecaster = GGALForecaster(min_samples=10)
prediction_tracker = PredictionTracker(max_predictions=100)

# Background thread initialization moved to gunicorn_config.py post_fork hook
# This prevents duplicate threads when Gunicorn forks worker processes
# For local development with `python app.py`, the thread is started in __main__ block below

# Routes

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/precio-actual')
def precio_actual():
    if monitor.historial:
        return jsonify(monitor.historial[-1])
    return jsonify({"error": "Sin datos", "message": "Esperando primer dato..."}), 202

@app.route('/api/historial')
def historial():
    return jsonify(monitor.obtener_historial())

@app.route('/api/estadisticas')
def estadisticas():
    if not monitor.historial:
        return jsonify({"error": "Sin datos"}), 202
    
    precios = [p["price"] for p in monitor.historial]
    return jsonify({
        "max": round(max(precios), 2),
        "min": round(min(precios), 2),
        "promedio": round(sum(precios) / len(precios), 2),
        "muestras": len(precios),
        "ultimo_update": monitor.historial[-1]["timestamp"]
    })

@app.route('/api/health')
def health():
    return jsonify({"status": "ok", "symbol": "GGAL"})

@app.route('/api/debug')
def debug():
    """Debug endpoint to check API configuration and connection status."""
    api_key_configured = os.environ.get('FINNHUB_API_KEY') is not None
    api_key_length = len(monitor.api_key) if monitor.api_key else 0
    is_demo = monitor.api_key == "demo"

    # Try to get current price to test connection
    test_response = None
    try:
        response = requests.get(
            "https://finnhub.io/api/v1/quote",
            params={"symbol": "GGAL", "token": monitor.api_key},
            timeout=5
        )
        test_response = {
            "status_code": response.status_code,
            "has_error": "error" in response.json(),
            "error_message": response.json().get("error", None) if "error" in response.json() else None,
            "has_price": "c" in response.json(),
            "price": response.json().get("c", None) if "c" in response.json() else None
        }
    except Exception as e:
        test_response = {"error": str(e)}

    return jsonify({
        "process_id": os.getpid(),
        "parent_process_id": os.getppid(),
        "api_key_configured": api_key_configured,
        "api_key_is_demo": is_demo,
        "api_key_length": api_key_length,
        "historial_size": len(monitor.historial),
        "historial_max_size": monitor.historial.maxlen,
        "thread_running": monitor.running,
        "test_connection": test_response,
        "instructions": "Configure FINNHUB_API_KEY environment variable in Render dashboard" if is_demo else "API key is configured"
    })

@app.route('/api/forecast')
def forecast():
    """Get price forecast for next 1, 5, and 10 minutes."""
    if len(monitor.historial) < 10:
        return jsonify({"error": "Insufficient data", "message": "Need at least 10 data points"}), 202

    forecasts = forecaster.get_all_forecasts(monitor.historial, horizons=[1, 5, 10])

    # Store 5-minute prediction for validation
    if '5min' in forecasts:
        prediction_tracker.add_prediction(forecasts['5min'])

    # Validate old predictions against current price history
    validated_count = prediction_tracker.validate_predictions(monitor.historial)
    if validated_count > 0:
        print(f"✅ Validated {validated_count} prediction(s)")

    return jsonify(forecasts)

@app.route('/api/trading-signal')
def trading_signal():
    """Get AI-generated trading signal (BUY/SELL/HOLD)."""
    if len(monitor.historial) < 15:
        return jsonify({"error": "Insufficient data", "message": "Need at least 15 data points"}), 202

    signal = forecaster.generate_trading_signal(monitor.historial)
    return jsonify(signal)

@app.route('/api/prediction-metrics')
def prediction_metrics():
    """Get accuracy metrics for predictions."""
    # Validate pending predictions first
    prediction_tracker.validate_predictions(monitor.historial)

    # Get metrics
    metrics = prediction_tracker.get_accuracy_metrics()

    # Get recent predictions
    recent = prediction_tracker.get_recent_predictions(limit=10)

    return jsonify({
        'metrics': metrics,
        'recent_predictions': recent,
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    # Start background thread for local development (not needed when using gunicorn)
    if not monitor.running:
        print(f"🚀 [Local Dev] Starting background monitoring thread (PID: {os.getpid()})")
        thread = threading.Thread(target=monitor.monitorear_background, args=(10,), daemon=True)
        thread.start()

    port = int(os.environ.get('PORT', 5001))
    app.run(debug=False, host='0.0.0.0', port=port)