"""Stock price monitoring module - extraído de app.py para reutilización."""
import requests
import threading
import time
from datetime import datetime
from collections import deque
import functools

# Force unbuffered output
print = functools.partial(print, flush=True)


class MonitorGGAL:
    """Background daemon that polls Finnhub API for real-time GGAL price."""

    def __init__(self, api_key, symbol="GGAL"):
        self.api_key = api_key
        self.symbol = symbol
        self.historial = deque(maxlen=1000)
        self.running = False
        self._thread = None

    def obtener_precio(self):
        """Fetch current price from Finnhub API."""
        try:
            response = requests.get(
                "https://finnhub.io/api/v1/quote",
                params={"symbol": self.symbol, "token": self.api_key},
                timeout=5
            )
            data = response.json()

            # Check for API errors
            if "error" in data:
                if response.status_code == 401:
                    print(f"❌ API key inválida")
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
                return None

        except Exception as e:
            print(f"Error obteniendo precio: {e}")
        return None

    def monitorear_background(self, intervalo=10):
        """Background polling loop."""
        self.running = True

        while self.running:
            try:
                precio = self.obtener_precio()
                if precio:
                    self.historial.append(precio)
            except Exception as e:
                print(f"❌ Error in monitorear_background: {e}")
            time.sleep(intervalo)

    def start(self, intervalo=10):
        """Start background monitoring thread."""
        if not self.running:
            self._thread = threading.Thread(
                target=self.monitorear_background,
                args=(intervalo,),
                daemon=True
            )
            self._thread.start()

    def stop(self):
        """Stop background monitoring."""
        self.running = False
        if self._thread:
            self._thread.join(timeout=2)

    def obtener_historial(self):
        """Get all price history."""
        return list(self.historial)
