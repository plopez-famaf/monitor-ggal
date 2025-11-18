"""
Prediction Tracker for GGAL Monitor
Stores predictions and validates them against actual prices.
"""

import numpy as np
from datetime import datetime, timedelta
from collections import deque


class PredictionTracker:
    """
    Tracks predictions and compares them with actual outcomes.
    Calculates accuracy metrics for model performance evaluation.
    """

    def __init__(self, max_predictions=100):
        """
        Initialize prediction tracker.

        Args:
            max_predictions: Maximum number of predictions to store
        """
        self.predictions = deque(maxlen=max_predictions)
        self.validated_predictions = deque(maxlen=max_predictions)

    def add_prediction(self, forecast_data, timestamp=None):
        """
        Store a prediction for later validation.

        Args:
            forecast_data: Forecast dictionary from Kalman Filter
            timestamp: When the prediction was made (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.now()

        prediction_record = {
            'timestamp': timestamp.isoformat(),
            'current_price': forecast_data['current_price'],
            'predicted_price': forecast_data['prediction'],
            'horizon_minutes': forecast_data['horizon_minutes'],
            'velocity': forecast_data['velocity'],
            'uncertainty': forecast_data['uncertainty'],
            'confidence': forecast_data['confidence'],
            'lower_bound': forecast_data['lower_bound'],
            'upper_bound': forecast_data['upper_bound'],
            'validated': False,
            'actual_price': None,
            'error': None
        }

        self.predictions.append(prediction_record)

    def validate_predictions(self, current_historial):
        """
        Check if any predictions can now be validated with actual prices.

        Args:
            current_historial: Deque of current price history

        Returns:
            Number of predictions validated in this call
        """
        if not current_historial:
            return 0

        validated_count = 0
        current_time = datetime.now()

        # Convert historial to dict keyed by timestamp for fast lookup
        historial_dict = {}
        for record in current_historial:
            try:
                ts = datetime.fromisoformat(record['timestamp'])
                historial_dict[ts] = record['price']
            except (KeyError, ValueError):
                continue

        # Check each unvalidated prediction
        for pred in self.predictions:
            if pred['validated']:
                continue

            try:
                pred_time = datetime.fromisoformat(pred['timestamp'])
                target_time = pred_time + timedelta(minutes=pred['horizon_minutes'])

                # Check if enough time has passed
                if current_time < target_time:
                    continue

                # Find closest actual price to target time
                actual_price = self._find_closest_price(target_time, historial_dict)

                if actual_price is not None:
                    # Calculate error metrics
                    error = actual_price - pred['predicted_price']
                    error_pct = (error / pred['current_price']) * 100

                    # Check if within confidence interval
                    within_interval = (pred['lower_bound'] <= actual_price <= pred['upper_bound'])

                    # Update prediction record
                    pred['validated'] = True
                    pred['actual_price'] = actual_price
                    pred['error'] = error
                    pred['error_pct'] = error_pct
                    pred['within_interval'] = within_interval
                    pred['validation_time'] = current_time.isoformat()

                    # Add to validated list
                    self.validated_predictions.append(pred.copy())
                    validated_count += 1

            except (KeyError, ValueError) as e:
                print(f"Error validating prediction: {e}")
                continue

        return validated_count

    def _find_closest_price(self, target_time, historial_dict):
        """
        Find the price closest to target time.

        Args:
            target_time: Target datetime
            historial_dict: Dict mapping timestamps to prices

        Returns:
            Price at closest timestamp, or None if not found
        """
        if not historial_dict:
            return None

        # Find timestamp within ±30 seconds of target
        tolerance = timedelta(seconds=30)

        for ts, price in historial_dict.items():
            if abs(ts - target_time) <= tolerance:
                return price

        return None

    def get_accuracy_metrics(self):
        """
        Calculate accuracy metrics from validated predictions.

        Returns:
            Dict with accuracy statistics
        """
        if not self.validated_predictions:
            return {
                'total_predictions': 0,
                'validated_predictions': 0,
                'metrics': None
            }

        validated_list = list(self.validated_predictions)
        errors = [p['error'] for p in validated_list if p.get('error') is not None]
        error_pcts = [p['error_pct'] for p in validated_list if p.get('error_pct') is not None]
        within_intervals = [p['within_interval'] for p in validated_list if 'within_interval' in p]

        if not errors:
            return {
                'total_predictions': len(self.predictions),
                'validated_predictions': 0,
                'metrics': None
            }

        # Calculate error metrics
        mae = np.mean(np.abs(errors))  # Mean Absolute Error
        rmse = np.sqrt(np.mean(np.array(errors) ** 2))  # Root Mean Squared Error
        mape = np.mean(np.abs(error_pcts))  # Mean Absolute Percentage Error

        # Directional accuracy (did we predict direction correctly?)
        correct_direction = 0
        for p in validated_list:
            if p.get('error') is None:
                continue
            predicted_direction = 'up' if p['predicted_price'] > p['current_price'] else 'down'
            actual_direction = 'up' if p['actual_price'] > p['current_price'] else 'down'
            if predicted_direction == actual_direction:
                correct_direction += 1

        directional_accuracy = (correct_direction / len(errors)) * 100 if errors else 0

        # Confidence interval coverage (95% should be within bounds)
        interval_coverage = (sum(within_intervals) / len(within_intervals)) * 100 if within_intervals else 0

        # Recent performance (last 10 predictions)
        recent_errors = error_pcts[-10:] if len(error_pcts) >= 10 else error_pcts
        recent_mape = np.mean(np.abs(recent_errors)) if recent_errors else 0

        return {
            'total_predictions': len(self.predictions),
            'validated_predictions': len(validated_list),
            'metrics': {
                'mae': round(mae, 3),  # Mean Absolute Error ($)
                'rmse': round(rmse, 3),  # Root Mean Squared Error ($)
                'mape': round(mape, 2),  # Mean Absolute Percentage Error (%)
                'directional_accuracy': round(directional_accuracy, 1),  # % correct direction
                'interval_coverage': round(interval_coverage, 1),  # % within 95% CI
                'recent_mape': round(recent_mape, 2),  # Recent 10 predictions MAPE
            },
            'summary': self._generate_summary(directional_accuracy, mape, interval_coverage)
        }

    def _generate_summary(self, dir_acc, mape, coverage):
        """Generate human-readable summary of performance."""
        if dir_acc >= 70 and mape < 1.0:
            return 'Excellent: High accuracy, low error'
        elif dir_acc >= 60 and mape < 1.5:
            return 'Good: Reliable predictions'
        elif dir_acc >= 50 and mape < 2.5:
            return 'Fair: Moderate accuracy'
        else:
            return 'Poor: Needs parameter tuning'

    def get_recent_predictions(self, limit=10):
        """
        Get most recent validated predictions.

        Args:
            limit: Number of predictions to return

        Returns:
            List of recent prediction records
        """
        validated_list = list(self.validated_predictions)
        return validated_list[-limit:] if validated_list else []

    def clear_old_predictions(self, hours=24):
        """
        Remove predictions older than specified hours.

        Args:
            hours: Remove predictions older than this
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)

        # Filter predictions
        self.predictions = deque(
            [p for p in self.predictions
             if datetime.fromisoformat(p['timestamp']) > cutoff_time],
            maxlen=self.predictions.maxlen
        )

        # Filter validated predictions
        self.validated_predictions = deque(
            [p for p in self.validated_predictions
             if datetime.fromisoformat(p['timestamp']) > cutoff_time],
            maxlen=self.validated_predictions.maxlen
        )
