"""
AutoML-powered forecaster using Auto-ARIMA.
Automatically selects optimal ARIMA model parameters.
"""
import numpy as np
from datetime import datetime
from pmdarima import auto_arima


class AutoMLForecaster:
    """
    AutoML forecaster using pmdarima's Auto-ARIMA.
    Automatically finds optimal ARIMA(p,d,q) parameters.
    """

    def __init__(self, min_samples=30, horizon_minutes=5):
        """
        Initialize AutoML forecaster.

        Args:
            min_samples: Minimum data points needed for training
            horizon_minutes: Forecast horizon in minutes
        """
        self.min_samples = min_samples
        self.horizon_minutes = horizon_minutes
        self.model = None
        self.last_train_size = 0

    def _should_retrain(self, n_samples):
        """Determine if model needs retraining."""
        # Retrain if no model or significant new data (every 10 points)
        return self.model is None or (n_samples - self.last_train_size) >= 10

    def forecast(self, historial, horizon_minutes=None):
        """
        Generate forecast using Auto-ARIMA.

        Args:
            historial: Price history deque
            horizon_minutes: Forecast horizon (default: 5 minutes)

        Returns:
            dict with prediction, confidence interval, and metadata
        """
        if len(historial) < self.min_samples:
            return None

        # Extract prices
        prices = np.array([p["price"] for p in historial])

        # Use fixed horizon
        horizon_minutes = self.horizon_minutes

        # Retrain if needed
        if self._should_retrain(len(prices)):
            try:
                self.model = auto_arima(
                    prices,
                    seasonal=False,  # No seasonality for intraday data
                    trace=False,  # Suppress search output
                    error_action='ignore',  # Ignore warnings
                    suppress_warnings=True,
                    stepwise=True,  # Faster stepwise search
                    max_p=5,  # Limit AR order
                    max_q=5,  # Limit MA order
                    max_d=2,  # Limit differencing
                    n_jobs=-1  # Use all CPU cores
                )
                self.last_train_size = len(prices)
            except Exception as e:
                print(f"⚠️  AutoML training failed: {e}")
                return None

        # Generate forecast
        try:
            forecast_result = self.model.predict(
                n_periods=1,
                return_conf_int=True,
                alpha=0.05  # 95% confidence interval
            )

            predicted_price = forecast_result[0][0]
            conf_int = forecast_result[1][0]

        except Exception as e:
            print(f"⚠️  AutoML prediction failed: {e}")
            return None

        # Calculate metrics
        current_price = prices[-1]
        change = predicted_price - current_price
        change_pct = (change / current_price) * 100

        # Estimate uncertainty from confidence interval width
        uncertainty = (conf_int[1] - conf_int[0]) / 4  # ~1 std dev

        return {
            'prediction': round(predicted_price, 2),
            'current_price': round(current_price, 2),
            'price_change': round(change, 2),
            'price_change_pct': round(change_pct, 2),
            'horizon': f'{horizon_minutes}min',
            'velocity': round(change / horizon_minutes, 4),
            'trend': 'up' if change > 0 else 'down' if change < 0 else 'flat',
            'lower_bound': round(conf_int[0], 2),
            'upper_bound': round(conf_int[1], 2),
            'confidence_interval': '95%',
            'confidence': 'high' if uncertainty < 0.5 else 'medium' if uncertainty < 1.0 else 'low',
            'model_type': 'Auto-ARIMA',
            'model_order': str(self.model.order) if self.model else 'N/A',
            'timestamp': datetime.now().isoformat()
        }

    def get_all_forecasts(self, historial, horizons=None):
        """
        Get forecast (always 5 minutes).

        Args:
            historial: Price history
            horizons: Ignored (backward compatibility)

        Returns:
            dict with single 5-min forecast
        """
        forecast = self.forecast(historial)
        if forecast:
            return {'5min': forecast}
        return {}

    def generate_trading_signal(self, historial):
        """
        Generate trading signal based on Auto-ARIMA prediction.

        Returns:
            dict with signal, strength, and reasoning
        """
        if len(historial) < self.min_samples:
            return None

        forecast = self.forecast(historial)
        if not forecast:
            return None

        price_change_pct = forecast['price_change_pct']
        confidence = forecast['confidence']
        uncertainty = (forecast['upper_bound'] - forecast['lower_bound']) / 4

        # Signal strength (0-100)
        # Component 1: Price change magnitude (max 50 points)
        price_magnitude = min(abs(price_change_pct) * 10, 50)

        # Component 2: Confidence (max 30 points)
        if confidence == 'high':
            confidence_score = 30
        elif confidence == 'medium':
            confidence_score = 20
        else:
            confidence_score = 10

        # Component 3: Low uncertainty (max 20 points)
        uncertainty_score = max(0, 20 - uncertainty * 10)

        signal_strength = int(price_magnitude + confidence_score + uncertainty_score)

        # Determine signal
        if price_change_pct > 0.3 and confidence in ['high', 'medium']:
            signal = 'BUY'
            reason = f"Upward trend predicted (+{price_change_pct:.2f}%)"
        elif price_change_pct < -0.3 and confidence in ['high', 'medium']:
            signal = 'SELL'
            reason = f"Downward trend predicted ({price_change_pct:.2f}%)"
        else:
            signal = 'HOLD'
            reason = "Low expected movement or high uncertainty"

        return {
            'signal': signal,
            'signal_strength': signal_strength,
            'confidence': confidence,
            'reason': reason,
            'price_change_forecast': round(price_change_pct, 2),
            'current_price': forecast['current_price'],
            'predicted_price': forecast['prediction'],
            'model_type': 'Auto-ARIMA',
            'model_order': forecast['model_order'],
            'timestamp': datetime.now().isoformat()
        }
