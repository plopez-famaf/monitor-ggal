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

        # Error tracking
        self.consecutive_errors = 0
        self.max_consecutive_errors = 5
        self.last_error_time = None

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

            # Check HTTP status before parsing JSON
            if response.status_code == 401:
                self._handle_error(f"[{self.symbol}] Finnhub API key inválida (401)")
                return None
            elif response.status_code == 429:
                self._handle_error(f"[{self.symbol}] Finnhub rate limit exceeded (429)")
                return None
            elif response.status_code != 200:
                self._handle_error(f"[{self.symbol}] Finnhub HTTP {response.status_code}")
                return None

            # Try to parse JSON
            try:
                data = response.json()
            except ValueError as e:
                # JSONDecodeError is a subclass of ValueError
                self._handle_error(f"[{self.symbol}] Finnhub invalid response (not JSON): {response.text[:100]}")
                return None

            # Check for API errors
            if "error" in data:
                self._handle_error(f"[{self.symbol}] Finnhub API error: {data.get('error', 'unknown')}")
                return None

            if "c" in data and data["c"] > 0:
                # Success - reset error counter
                self.consecutive_errors = 0
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
                # Market closed or no trading
                return None

        except requests.exceptions.Timeout:
            self._handle_error(f"[{self.symbol}] Finnhub timeout (5s) - red congestionada o servidor lento")
        except requests.exceptions.ConnectionError:
            self._handle_error(f"[{self.symbol}] Finnhub connection error - verificar internet")
        except requests.exceptions.RequestException as e:
            self._handle_error(f"[{self.symbol}] Finnhub request error: {type(e).__name__}")
        except Exception as e:
            self._handle_error(f"[{self.symbol}] Finnhub unexpected error: {type(e).__name__} - {str(e)[:50]}")
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
                self._handle_error(f"[{self.symbol}] Binance API error: HTTP {response.status_code}")
                return None

            data = response.json()

            # Success - reset error counter
            self.consecutive_errors = 0
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

        except requests.exceptions.Timeout:
            self._handle_error(f"[{self.symbol}] Binance timeout (5s) - red congestionada o servidor lento")
        except requests.exceptions.ConnectionError:
            self._handle_error(f"[{self.symbol}] Binance connection error - verificar internet")
        except requests.exceptions.RequestException as e:
            self._handle_error(f"[{self.symbol}] Binance request error: {type(e).__name__}")
        except Exception as e:
            self._handle_error(f"[{self.symbol}] Binance unexpected error: {type(e).__name__} - {str(e)[:50]}")
        return None

    def _handle_error(self, message):
        """Handle API errors with consecutive error tracking."""
        self.consecutive_errors += 1
        self.last_error_time = datetime.now()

        # Only print if it's a new error or every 5th consecutive error
        if self.consecutive_errors == 1 or self.consecutive_errors % 5 == 0:
            print(f"⚠️  {message}")
            if self.consecutive_errors >= self.max_consecutive_errors:
                print(f"⚠️  [{self.symbol}] {self.consecutive_errors} errores consecutivos - verificar conectividad")

    def monitorear_background(self, intervalo=10):
        """Background polling loop."""
        self.running = True

        while self.running:
            try:
                precio = self.obtener_precio()
                if precio:
                    self.historial.append(precio)
            except Exception as e:
                self._handle_error(f"[{self.symbol}] Error crítico en monitoreo: {type(e).__name__}")
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
