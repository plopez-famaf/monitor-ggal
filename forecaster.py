import numpy as np
from datetime import datetime


class GGALForecaster:
    """
    Lightweight short-term forecasting for GGAL stock prices.
    Basic statistical models suitable for minute-level predictions.
    """

    def __init__(self, min_samples=10):
        self.min_samples = min_samples

    def _extract_prices(self, historial):
        """Extract price array from historial deque."""
        if len(historial) < self.min_samples:
            return None
        return np.array([p['price'] for p in historial])

    def _calculate_returns(self, prices):
        """Calculate log returns."""
        return np.diff(np.log(prices))

    def _calculate_technical_indicators(self, prices, window=5):
        """Calculate technical indicators for feature engineering."""
        indicators = {}

        # Moving averages
        if len(prices) >= window:
            indicators['sma'] = np.mean(prices[-window:])
            indicators['ema'] = self._exponential_moving_average(prices, window)

        # Momentum
        if len(prices) >= window:
            indicators['momentum'] = prices[-1] - prices[-window]
            indicators['roc'] = (prices[-1] - prices[-window]) / prices[-window] * 100

        # Volatility (standard deviation of returns)
        if len(prices) >= window:
            returns = self._calculate_returns(prices[-window:])
            indicators['volatility'] = np.std(returns)

        # RSI (Relative Strength Index)
        if len(prices) >= 14:
            indicators['rsi'] = self._calculate_rsi(prices, period=14)

        return indicators

    def _exponential_moving_average(self, prices, window):
        """Calculate EMA."""
        alpha = 2 / (window + 1)
        ema = prices[0]
        for price in prices[1:]:
            ema = alpha * price + (1 - alpha) * ema
        return ema

    def _calculate_rsi(self, prices, period=14):
        """Calculate Relative Strength Index."""
        deltas = np.diff(prices)
        gains = deltas.copy()
        losses = deltas.copy()
        gains[gains < 0] = 0
        losses[losses > 0] = 0
        losses = np.abs(losses)

        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])

        if avg_loss == 0:
            return 100

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def predict_simple_ma(self, historial, horizon_minutes=5):
        """
        Simple Moving Average forecast.
        Fast and lightweight, good baseline for HFT.
        """
        prices = self._extract_prices(historial)
        if prices is None:
            return None

        # Use different MA windows
        short_window = min(5, len(prices))
        long_window = min(10, len(prices))

        short_ma = np.mean(prices[-short_window:])
        long_ma = np.mean(prices[-long_window:])

        # Trend detection
        trend = short_ma - long_ma

        # Simple forecast: current price + trend
        prediction = prices[-1] + trend

        return {
            'method': 'simple_ma',
            'prediction': round(prediction, 2),
            'current_price': round(prices[-1], 2),
            'horizon_minutes': horizon_minutes,
            'confidence': 'low',  # MA is simple, lower confidence
            'trend': 'up' if trend > 0 else 'down'
        }

    def predict_exponential_smoothing(self, historial, horizon_minutes=5, alpha=0.3):
        """
        Exponential Smoothing forecast.
        Gives more weight to recent observations.
        """
        prices = self._extract_prices(historial)
        if prices is None:
            return None

        # Triple exponential smoothing (Holt-Winters style)
        level = prices[0]
        trend = 0

        for price in prices[1:]:
            last_level = level
            level = alpha * price + (1 - alpha) * (level + trend)
            trend = alpha * (level - last_level) + (1 - alpha) * trend

        # Forecast
        prediction = level + trend * horizon_minutes

        return {
            'method': 'exponential_smoothing',
            'prediction': round(prediction, 2),
            'current_price': round(prices[-1], 2),
            'horizon_minutes': horizon_minutes,
            'confidence': 'medium',
            'trend_strength': round(abs(trend), 4)
        }

    def predict_linear_regression(self, historial, horizon_minutes=5):
        """
        Simple linear regression on recent price movements.
        Captures short-term linear trends.
        """
        prices = self._extract_prices(historial)
        if prices is None:
            return None

        # Use recent window for regression
        window = min(20, len(prices))
        recent_prices = prices[-window:]

        # Time index
        X = np.arange(len(recent_prices))

        # Manual linear regression (avoid scipy dependency)
        n = len(X)
        x_mean = np.mean(X)
        y_mean = np.mean(recent_prices)

        numerator = np.sum((X - x_mean) * (recent_prices - y_mean))
        denominator = np.sum((X - x_mean) ** 2)

        slope = numerator / denominator if denominator != 0 else 0
        intercept = y_mean - slope * x_mean

        # Predict future
        future_time = len(recent_prices) + horizon_minutes
        prediction = slope * future_time + intercept

        # Simple R-squared
        y_pred = slope * X + intercept
        ss_res = np.sum((recent_prices - y_pred) ** 2)
        ss_tot = np.sum((recent_prices - y_mean) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

        confidence = 'high' if r_squared > 0.7 else 'medium' if r_squared > 0.4 else 'low'

        return {
            'method': 'linear_regression',
            'prediction': round(prediction, 2),
            'current_price': round(prices[-1], 2),
            'horizon_minutes': horizon_minutes,
            'confidence': confidence,
            'r_squared': round(r_squared, 3),
            'slope': round(slope, 4),
            'trend': 'up' if slope > 0 else 'down'
        }

    def predict_momentum_based(self, historial, horizon_minutes=5):
        """
        Momentum-based prediction.
        Assumes recent momentum continues.
        """
        prices = self._extract_prices(historial)
        if prices is None:
            return None

        # Calculate momentum over different windows
        short_momentum = prices[-1] - prices[-min(3, len(prices))]
        med_momentum = prices[-1] - prices[-min(5, len(prices))]
        long_momentum = prices[-1] - prices[-min(10, len(prices))]

        # Weighted average of momentums
        avg_momentum = (short_momentum * 0.5 + med_momentum * 0.3 + long_momentum * 0.2)

        # Project momentum forward
        prediction = prices[-1] + avg_momentum * (horizon_minutes / 5)

        return {
            'method': 'momentum',
            'prediction': round(prediction, 2),
            'current_price': round(prices[-1], 2),
            'horizon_minutes': horizon_minutes,
            'momentum': round(avg_momentum, 4),
            'confidence': 'medium'
        }

    def predict_mean_reversion(self, historial, horizon_minutes=5):
        """
        Mean reversion strategy.
        Assumes price will revert to recent mean.
        """
        prices = self._extract_prices(historial)
        if prices is None:
            return None

        # Calculate mean and std
        window = min(20, len(prices))
        recent_prices = prices[-window:]
        mean_price = np.mean(recent_prices)
        std_price = np.std(recent_prices)

        current_price = prices[-1]

        # Z-score
        z_score = (current_price - mean_price) / std_price if std_price > 0 else 0

        # Reversion prediction: move towards mean
        reversion_strength = 0.3  # How much to revert
        prediction = current_price + (mean_price - current_price) * reversion_strength

        return {
            'method': 'mean_reversion',
            'prediction': round(prediction, 2),
            'current_price': round(current_price, 2),
            'mean_price': round(mean_price, 2),
            'z_score': round(z_score, 2),
            'horizon_minutes': horizon_minutes,
            'confidence': 'medium',
            'signal': 'overbought' if z_score > 1 else 'oversold' if z_score < -1 else 'neutral'
        }

    def ensemble_forecast(self, historial, horizon_minutes=5):
        """
        Ensemble of multiple models for robust prediction.
        Combines predictions from all models.
        """
        prices = self._extract_prices(historial)
        if prices is None:
            return None

        predictions = []
        methods_used = []

        # Get all predictions
        models = [
            self.predict_simple_ma,
            self.predict_exponential_smoothing,
            self.predict_linear_regression,
            self.predict_momentum_based,
            self.predict_mean_reversion
        ]

        for model in models:
            try:
                pred = model(historial, horizon_minutes)
                if pred:
                    predictions.append(pred['prediction'])
                    methods_used.append(pred['method'])
            except Exception as e:
                print(f"Error in {model.__name__}: {e}")

        if not predictions:
            return None

        # Ensemble: median (more robust than mean)
        ensemble_pred = np.median(predictions)

        # Calculate disagreement (spread) as confidence measure
        spread = np.std(predictions)
        confidence = 'high' if spread < 0.1 else 'medium' if spread < 0.3 else 'low'

        # Technical indicators
        indicators = self._calculate_technical_indicators(prices)

        return {
            'method': 'ensemble',
            'prediction': round(ensemble_pred, 2),
            'current_price': round(prices[-1], 2),
            'horizon_minutes': horizon_minutes,
            'confidence': confidence,
            'prediction_spread': round(spread, 3),
            'models_used': methods_used,
            'num_models': len(predictions),
            'min_prediction': round(min(predictions), 2),
            'max_prediction': round(max(predictions), 2),
            'technical_indicators': indicators,
            'timestamp': datetime.now().isoformat()
        }

    def get_all_forecasts(self, historial, horizons=[1, 5, 10]):
        """
        Get ensemble forecasts for multiple time horizons.
        """
        forecasts = {}
        for horizon in horizons:
            forecast = self.ensemble_forecast(historial, horizon_minutes=horizon)
            if forecast:
                forecasts[f'{horizon}min'] = forecast

        return forecasts

    def generate_trading_signal(self, historial):
        """
        Generate trading signal based on forecasts and indicators.
        Returns: 'BUY', 'SELL', or 'HOLD'
        """
        prices = self._extract_prices(historial)
        if prices is None or len(prices) < 15:
            return {'signal': 'HOLD', 'reason': 'Insufficient data', 'confidence': 'low'}

        # Get short-term forecast
        forecast = self.ensemble_forecast(historial, horizon_minutes=5)
        if not forecast:
            return {'signal': 'HOLD', 'reason': 'Forecast unavailable', 'confidence': 'low'}

        current_price = forecast['current_price']
        predicted_price = forecast['prediction']
        price_change_pct = ((predicted_price - current_price) / current_price) * 100

        # Get technical indicators
        indicators = forecast['technical_indicators']

        # Decision logic
        signal = 'HOLD'
        reason = []

        # Price prediction signal
        if price_change_pct > 0.5:  # Expected to rise > 0.5%
            signal = 'BUY'
            reason.append(f'Predicted rise: {price_change_pct:.2f}%')
        elif price_change_pct < -0.5:  # Expected to fall > 0.5%
            signal = 'SELL'
            reason.append(f'Predicted drop: {price_change_pct:.2f}%')

        # RSI signal
        if 'rsi' in indicators:
            if indicators['rsi'] < 30:
                signal = 'BUY' if signal != 'SELL' else signal
                reason.append(f'RSI oversold: {indicators["rsi"]:.1f}')
            elif indicators['rsi'] > 70:
                signal = 'SELL' if signal != 'BUY' else signal
                reason.append(f'RSI overbought: {indicators["rsi"]:.1f}')

        # Momentum confirmation
        if 'momentum' in indicators:
            if signal == 'BUY' and indicators['momentum'] < 0:
                signal = 'HOLD'
                reason.append('Negative momentum - holding')
            elif signal == 'SELL' and indicators['momentum'] > 0:
                signal = 'HOLD'
                reason.append('Positive momentum - holding')

        return {
            'signal': signal,
            'confidence': forecast['confidence'],
            'reason': '; '.join(reason) if reason else 'No clear signal',
            'price_change_forecast': round(price_change_pct, 2),
            'current_price': current_price,
            'predicted_price': predicted_price,
            'timestamp': datetime.now().isoformat()
        }
