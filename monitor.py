"""
Multi-symbol price monitoring module.
Supports stocks (Finnhub) and crypto (Binance).
"""
import requests
import threading
import time
from datetime import datetime
from collections import deque
import functools

# Force unbuffered output
print = functools.partial(print, flush=True)


class PriceMonitor:
    """
    Universal price monitor supporting multiple assets and APIs.
    Replaces MonitorGGAL with multi-symbol support.
    """

    def __init__(self, symbol, api_type='stock', api_key=None):
        """
        Initialize monitor for a single symbol.

        Args:
            symbol: Symbol to monitor (e.g., 'GGAL', 'BTCUSDT')
            api_type: 'stock' (Finnhub) or 'crypto' (Binance)
            api_key: API key (required for stocks, optional for crypto)
        """
        self.symbol = symbol
        self.api_type = api_type
        self.api_key = api_key
        self.historial = deque(maxlen=1000)
        self.running = False
        self._thread = None

    def obtener_precio(self):
        """Fetch current price from appropriate API."""
        if self.api_type == 'stock':
            return self._fetch_finnhub()
        elif self.api_type == 'crypto':
            return self._fetch_binance()
        else:
            print(f"❌ Unknown API type: {self.api_type}")
            return None

    def _fetch_finnhub(self):
        """Fetch stock price from Finnhub API."""
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
                    print(f"❌ Finnhub API key inválida")
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
            print(f"Error obteniendo precio Finnhub: {e}")
        return None

    def _fetch_binance(self):
        """Fetch crypto price from Binance Public API."""
        try:
            # Use public endpoint (no API key required for price data)
            response = requests.get(
                "https://api.binance.com/api/v3/ticker/24hr",
                params={"symbol": self.symbol},
                timeout=5
            )

            if response.status_code != 200:
                print(f"❌ Binance API error: {response.status_code}")
                return None

            data = response.json()

            return {
                "timestamp": datetime.now().isoformat(),
                "price": float(data.get("lastPrice", 0)),
                "high": float(data.get("highPrice", 0)),
                "low": float(data.get("lowPrice", 0)),
                "open": float(data.get("openPrice", 0)),
                "volume": float(data.get("volume", 0)),
                "change": float(data.get("priceChange", 0)),
                "change_percent": float(data.get("priceChangePercent", 0))
            }

        except Exception as e:
            print(f"Error obteniendo precio Binance: {e}")
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


# Backward compatibility alias
MonitorGGAL = PriceMonitor
