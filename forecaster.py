import numpy as np
from datetime import datetime


class KalmanFilter:
    """
    Kalman Filter for real-time price prediction.

    State vector: [price, velocity]
    - price: current price estimate
    - velocity: rate of price change ($/timestep)

    The filter optimally combines:
    1. Predictions from the motion model (physics)
    2. Noisy measurements (actual prices)
    """

    def __init__(self, process_noise=0.01, measurement_noise=0.1):
        """
        Initialize Kalman Filter.

        Args:
            process_noise: How much the model can deviate (Q matrix)
            measurement_noise: How noisy are price measurements (R)
        """
        # State: [price, velocity]
        self.x = np.array([0.0, 0.0])

        # Covariance matrix (uncertainty)
        self.P = np.eye(2) * 1000  # High initial uncertainty

        # State transition matrix (how state evolves)
        # price(t+1) = price(t) + velocity(t)
        # velocity(t+1) = velocity(t)
        self.F = np.array([
            [1, 1],  # price += velocity
            [0, 1]   # velocity unchanged
        ])

        # Measurement matrix (we only observe price, not velocity)
        self.H = np.array([[1, 0]])

        # Process noise covariance
        self.Q = np.eye(2) * process_noise

        # Measurement noise covariance
        self.R = measurement_noise

        self.initialized = False

    def update(self, measurement):
        """
        Update filter with new price measurement.

        This is the Kalman filter cycle:
        1. Predict next state
        2. Compute Kalman gain
        3. Update state with measurement
        """
        if not self.initialized:
            # Initialize with first measurement
            self.x[0] = measurement
            self.x[1] = 0.0
            self.initialized = True
            return

        # 1. PREDICT STEP
        # Project state ahead
        x_pred = self.F @ self.x

        # Project covariance ahead
        P_pred = self.F @ self.P @ self.F.T + self.Q

        # 2. UPDATE STEP
        # Innovation (measurement residual)
        y = measurement - (self.H @ x_pred)[0]

        # Innovation covariance
        S = (self.H @ P_pred @ self.H.T)[0, 0] + self.R

        # Kalman gain (how much to trust measurement vs prediction)
        K = (P_pred @ self.H.T) / S

        # Update state estimate
        self.x = x_pred + K.flatten() * y

        # Update covariance estimate
        I_KH = np.eye(2) - np.outer(K, self.H)
        self.P = I_KH @ P_pred

    def predict(self, steps=1):
        """
        Predict future price 'steps' timesteps ahead.

        Args:
            steps: Number of timesteps to predict forward

        Returns:
            predicted_price, uncertainty
        """
        if not self.initialized:
            return None, None

        # Project state forward
        x_pred = self.x.copy()
        P_pred = self.P.copy()

        for _ in range(steps):
            x_pred = self.F @ x_pred
            P_pred = self.F @ P_pred @ self.F.T + self.Q

        predicted_price = x_pred[0]
        uncertainty = np.sqrt(P_pred[0, 0])  # Standard deviation

        return predicted_price, uncertainty

    def get_velocity(self):
        """Get current estimated velocity (rate of change)."""
        return self.x[1] if self.initialized else 0.0

    def get_state(self):
        """Get full state [price, velocity]."""
        return self.x.copy() if self.initialized else None


class GGALForecaster:
    """
    Simplified forecaster using only Kalman Filter.
    Focused on 5-minute predictions for optimal performance.
    """

    def __init__(self, min_samples=10, horizon_minutes=5):
        self.min_samples = min_samples
        self.horizon_minutes = horizon_minutes  # Fixed at 5 minutes
        self.kf = None

    def _extract_prices(self, historial):
        """Extract price array from historial deque."""
        if len(historial) < self.min_samples:
            return None
        return np.array([p['price'] for p in historial])

    def _initialize_filter(self, prices):
        """Initialize and train Kalman filter with historical data."""
        self.kf = KalmanFilter(process_noise=0.01, measurement_noise=0.1)

        # Feed all historical prices to the filter
        for price in prices:
            self.kf.update(price)

    def forecast(self, historial, horizon_minutes=None):
        """
        Generate forecast using Kalman Filter.
        Fixed at 5-minute horizon for consistency.

        Args:
            historial: Price history deque
            horizon_minutes: Ignored (always uses 5 minutes)

        Returns:
            dict with prediction, confidence, and metadata
        """
        prices = self._extract_prices(historial)
        if prices is None:
            return None

        # Always use 5 minutes for consistency
        horizon_minutes = self.horizon_minutes

        # Initialize/reinitialize filter with latest data
        self._initialize_filter(prices)

        # Predict forward
        predicted_price, uncertainty = self.kf.predict(steps=horizon_minutes)

        if predicted_price is None:
            return None

        current_price = prices[-1]
        price_change = predicted_price - current_price
        price_change_pct = (price_change / current_price) * 100

        # Confidence based on uncertainty
        # Lower uncertainty = higher confidence
        if uncertainty < 0.1:
            confidence = 'high'
        elif uncertainty < 0.3:
            confidence = 'medium'
        else:
            confidence = 'low'

        # Velocity (rate of change)
        velocity = self.kf.get_velocity()

        return {
            'method': 'kalman_filter',
            'prediction': round(predicted_price, 2),
            'current_price': round(current_price, 2),
            'price_change': round(price_change, 2),
            'price_change_pct': round(price_change_pct, 2),
            'horizon_minutes': horizon_minutes,
            'confidence': confidence,
            'uncertainty': round(uncertainty, 3),
            'velocity': round(velocity, 4),
            'trend': 'up' if velocity > 0 else 'down' if velocity < 0 else 'flat',
            'lower_bound': round(predicted_price - 2 * uncertainty, 2),
            'upper_bound': round(predicted_price + 2 * uncertainty, 2),
            'confidence_interval': '95%',
            'timestamp': datetime.now().isoformat()
        }

    def get_all_forecasts(self, historial, horizons=None):
        """
        Get forecast (always 5 minutes).
        'horizons' parameter ignored for backward compatibility.

        Args:
            historial: Price history
            horizons: Ignored (always returns 5-min forecast)

        Returns:
            dict with single 5-min forecast
        """
        forecast = self.forecast(historial)
        if forecast:
            return {'5min': forecast}
        return {}

    def generate_trading_signal(self, historial):
        """
        Generate trading signal based on Kalman prediction.

        Signal logic:
        - BUY: Predicted rise > 0.3% with medium/high confidence
        - SELL: Predicted drop > 0.3% with medium/high confidence
        - HOLD: Otherwise

        Returns:
            dict with signal, confidence score (0-100), and reasoning
        """
        prices = self._extract_prices(historial)
        if prices is None or len(prices) < 15:
            return {
                'signal': 'HOLD',
                'signal_strength': 0,
                'reason': 'Insufficient data',
                'confidence': 'low'
            }

        # Get 5-minute forecast
        forecast = self.forecast(historial, horizon_minutes=5)
        if not forecast:
            return {
                'signal': 'HOLD',
                'signal_strength': 0,
                'reason': 'Forecast unavailable',
                'confidence': 'low'
            }

        price_change_pct = forecast['price_change_pct']
        velocity = forecast['velocity']
        uncertainty = forecast['uncertainty']

        # Calculate signal strength (0-100)
        # Based on: magnitude of change, velocity, and inverse of uncertainty
        strength_from_change = min(abs(price_change_pct) * 20, 50)  # Max 50 from price change
        strength_from_velocity = min(abs(velocity) * 100, 30)         # Max 30 from velocity
        strength_from_confidence = max(0, 20 - uncertainty * 50)     # Max 20 from low uncertainty

        signal_strength = int(strength_from_change + strength_from_velocity + strength_from_confidence)
        signal_strength = min(signal_strength, 100)  # Cap at 100

        # Determine signal
        if price_change_pct > 0.3 and forecast['confidence'] in ['medium', 'high']:
            signal = 'BUY'
            reason = f'Kalman predicts +{price_change_pct:.2f}% rise in 5min'
        elif price_change_pct < -0.3 and forecast['confidence'] in ['medium', 'high']:
            signal = 'SELL'
            reason = f'Kalman predicts {price_change_pct:.2f}% drop in 5min'
        else:
            signal = 'HOLD'
            if abs(price_change_pct) < 0.3:
                reason = f'Low expected movement ({price_change_pct:+.2f}%)'
            else:
                reason = f'Low confidence (uncertainty: {uncertainty:.2f})'

        return {
            'signal': signal,
            'signal_strength': signal_strength,
            'confidence': forecast['confidence'],
            'reason': reason,
            'price_change_forecast': round(price_change_pct, 2),
            'current_price': forecast['current_price'],
            'predicted_price': forecast['prediction'],
            'velocity': round(velocity, 4),
            'uncertainty': round(uncertainty, 3),
            'timestamp': datetime.now().isoformat()
        }
