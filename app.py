from flask import Flask, jsonify, render_template
import requests
import threading
import time
from datetime import datetime
from collections import deque
import os

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
            
            if "c" in data:
                return {
                    "timestamp": datetime.now().isoformat(),
                    "price": data.get("c", 0),
                    "high": data.get("h", 0),
                    "low": data.get("l", 0),
                    "open": data.get("o", 0),
                    "change": round(data.get("c", 0) - data.get("pc", 0), 2),
                    "change_percent": round((data.get("c", 0) - data.get("pc", 0)) / data.get("pc", 1) * 100, 2)
                }
        except Exception as e:
            print(f"Error obteniendo precio: {e}")
        return None
    
    def monitorear_background(self, intervalo=10):
        self.running = True
        print(f"Iniciando monitoreo de {self.symbol}...")
        while self.running:
            precio = self.obtener_precio()
            if precio:
                self.historial.append(precio)
                print(f"[{precio['timestamp']}] Precio: ${precio['price']:.2f}")
            time.sleep(intervalo)
    
    def obtener_historial(self):
        return list(self.historial)

# Obtener API key desde variable de entorno
api_key = os.environ.get('FINNHUB_API_KEY')
if not api_key:
    print("ADVERTENCIA: FINNHUB_API_KEY no está configurada")
    api_key = "demo"

monitor = MonitorGGAL(api_key=api_key)

# Iniciar monitoreo en background thread
thread = threading.Thread(target=monitor.monitorear_background, args=(10,), daemon=True)
thread.start()

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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)