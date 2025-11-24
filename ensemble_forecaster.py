"""
Ensemble forecaster combining Kalman Filter + Auto-ARIMA.
Provides robust predictions by averaging multiple models.
"""
import numpy as np
from datetime import datetime
from forecaster import GGALForecaster
from automl_forecaster import AutoMLForecaster


class EnsembleForecaster:
    """
    Combines Kalman Filter + Auto-ARIMA for robust predictions.
    Uses weighted average based on model performance.
    """

    def __init__(self, min_samples=30, horizon_minutes=5):
        """
        Initialize ensemble forecaster.

        Args:
            min_samples: Minimum data points needed
            horizon_minutes: Forecast horizon in minutes
        """
        self.kalman = GGALForecaster(min_samples=10, horizon_minutes=horizon_minutes)
        self.automl = AutoMLForecaster(min_samples=min_samples, horizon_minutes=horizon_minutes)
        self.min_samples = min_samples
        self.horizon_minutes = horizon_minutes

        # Default weights (can be adjusted based on effectiveness index)
        self.kalman_weight = 0.4
        self.automl_weight = 0.6

    def forecast(self, historial, horizon_minutes=None):
        """
        Generate ensemble forecast.

        Args:
            historial: Price history deque
            horizon_minutes: Forecast horizon (default: 5 minutes)

        Returns:
            dict with ensemble prediction and individual model predictions
        """
        if len(historial) < self.min_samples:
            # Fall back to Kalman if not enough data for AutoML
            if len(historial) >= 10:
                return self.kalman.forecast(historial)
            return None

        # Get predictions from both models
        kalman_pred = self.kalman.forecast(historial)
        automl_pred = self.automl.forecast(historial)

        # If only one model is ready, return that one
        if not kalman_pred and automl_pred:
            return automl_pred
        if kalman_pred and not automl_pred:
            return kalman_pred
        if not kalman_pred and not automl_pred:
            return None

        # Ensemble prediction (weighted average)
        ensemble_price = (
            kalman_pred['prediction'] * self.kalman_weight +
            automl_pred['prediction'] * self.automl_weight
        )

        current_price = kalman_pred['current_price']
        change = ensemble_price - current_price
        change_pct = (change / current_price) * 100

        # Average confidence intervals
        lower_bound = (
            kalman_pred['lower_bound'] * self.kalman_weight +
            automl_pred['lower_bound'] * self.automl_weight
        )
        upper_bound = (
            kalman_pred['upper_bound'] * self.kalman_weight +
            automl_pred['upper_bound'] * self.automl_weight
        )

        # Consensus confidence
        confidences = {'high': 3, 'medium': 2, 'low': 1}
        avg_confidence = (
            confidences.get(kalman_pred.get('confidence', 'medium'), 2) * self.kalman_weight +
            confidences.get(automl_pred.get('confidence', 'medium'), 2) * self.automl_weight
        )
        if avg_confidence >= 2.5:
            confidence = 'high'
        elif avg_confidence >= 1.5:
            confidence = 'medium'
        else:
            confidence = 'low'

        return {
            'prediction': round(ensemble_price, 2),
            'current_price': round(current_price, 2),
            'price_change': round(change, 2),
            'price_change_pct': round(change_pct, 2),
            'horizon': f'{self.horizon_minutes}min',
            'velocity': round(change / self.horizon_minutes, 4),
            'trend': 'up' if change > 0 else 'down' if change < 0 else 'flat',
            'lower_bound': round(lower_bound, 2),
            'upper_bound': round(upper_bound, 2),
            'confidence_interval': '95%',
            'confidence': confidence,
            'model_type': 'Ensemble (Kalman + Auto-ARIMA)',
            'components': {
                'kalman': {
                    'prediction': kalman_pred['prediction'],
                    'weight': self.kalman_weight
                },
                'automl': {
                    'prediction': automl_pred['prediction'],
                    'weight': self.automl_weight,
                    'order': automl_pred.get('model_order', 'N/A')
                }
            },
            'timestamp': datetime.now().isoformat()
        }

    def get_all_forecasts(self, historial, horizons=None):
        """
        Get ensemble forecast (always 5 minutes).

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
        Generate trading signal based on ensemble prediction.

        Returns:
            dict with signal, strength, and reasoning
        """
        if len(historial) < self.min_samples:
            # Fall back to Kalman
            if len(historial) >= 15:
                return self.kalman.generate_trading_signal(historial)
            return None

        forecast = self.forecast(historial)
        if not forecast:
            return None

        price_change_pct = forecast['price_change_pct']
        confidence = forecast['confidence']
        uncertainty = (forecast['upper_bound'] - forecast['lower_bound']) / 4

        # Signal strength (0-100)
        price_magnitude = min(abs(price_change_pct) * 10, 50)

        if confidence == 'high':
            confidence_score = 30
        elif confidence == 'medium':
            confidence_score = 20
        else:
            confidence_score = 10

        uncertainty_score = max(0, 20 - uncertainty * 10)
        signal_strength = int(price_magnitude + confidence_score + uncertainty_score)

        # Determine signal
        if price_change_pct > 0.3 and confidence in ['high', 'medium']:
            signal = 'BUY'
            reason = f"Ensemble consensus: upward trend (+{price_change_pct:.2f}%)"
        elif price_change_pct < -0.3 and confidence in ['high', 'medium']:
            signal = 'SELL'
            reason = f"Ensemble consensus: downward trend ({price_change_pct:.2f}%)"
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
            'model_type': 'Ensemble',
            'components': forecast['components'],
            'timestamp': datetime.now().isoformat()
        }

    def update_weights(self, kalman_effectiveness, automl_effectiveness):
        """
        Update ensemble weights based on effectiveness indices.

        Args:
            kalman_effectiveness: Effectiveness index for Kalman (0-100)
            automl_effectiveness: Effectiveness index for AutoML (0-100)
        """
        total = kalman_effectiveness + automl_effectiveness
        if total > 0:
            self.kalman_weight = kalman_effectiveness / total
            self.automl_weight = automl_effectiveness / total
