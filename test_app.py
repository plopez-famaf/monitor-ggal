"""
Test suite for GGAL Monitor Application
Tests API endpoints, forecasting models, and core functionality.
"""

import unittest
import json
from collections import deque
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, MonitorGGAL
from forecaster import GGALForecaster


class TestMonitorGGAL(unittest.TestCase):
    """Test MonitorGGAL class functionality."""

    def setUp(self):
        self.monitor = MonitorGGAL(api_key="demo")

    def test_monitor_initialization(self):
        """Test that monitor initializes correctly."""
        self.assertEqual(self.monitor.symbol, "GGAL")
        self.assertEqual(len(self.monitor.historial), 0)
        self.assertIsInstance(self.monitor.historial, deque)
        self.assertEqual(self.monitor.historial.maxlen, 1000)

    def test_obtener_precio_structure(self):
        """Test that precio data has correct structure."""
        precio = self.monitor.obtener_precio()

        if precio:  # May be None if API fails
            self.assertIsInstance(precio, dict)
            required_keys = ['timestamp', 'price', 'high', 'low', 'open', 'change', 'change_percent']
            for key in required_keys:
                self.assertIn(key, precio)

    def test_obtener_historial(self):
        """Test historial retrieval."""
        # Add mock data
        mock_data = {
            'timestamp': datetime.now().isoformat(),
            'price': 10.5,
            'high': 11.0,
            'low': 10.0,
            'open': 10.2,
            'change': 0.3,
            'change_percent': 2.94
        }
        self.monitor.historial.append(mock_data)

        historial = self.monitor.obtener_historial()
        self.assertEqual(len(historial), 1)
        self.assertEqual(historial[0]['price'], 10.5)


class TestGGALForecaster(unittest.TestCase):
    """Test GGALForecaster functionality."""

    def setUp(self):
        self.forecaster = GGALForecaster(min_samples=10)
        # Create mock historical data
        self.mock_historial = deque(maxlen=1000)
        base_price = 10.0
        for i in range(30):
            self.mock_historial.append({
                'timestamp': datetime.now().isoformat(),
                'price': base_price + (i * 0.1),  # Upward trend
                'high': base_price + (i * 0.1) + 0.2,
                'low': base_price + (i * 0.1) - 0.2,
                'open': base_price + (i * 0.1),
                'change': 0.1,
                'change_percent': 1.0
            })

    def test_forecaster_initialization(self):
        """Test forecaster initializes correctly."""
        self.assertEqual(self.forecaster.min_samples, 10)

    def test_extract_prices(self):
        """Test price extraction from historial."""
        prices = self.forecaster._extract_prices(self.mock_historial)
        self.assertIsNotNone(prices)
        self.assertEqual(len(prices), 30)
        self.assertAlmostEqual(prices[0], 10.0, places=1)

    def test_extract_prices_insufficient_data(self):
        """Test that None is returned with insufficient data."""
        small_historial = deque([{'price': 10.0}], maxlen=1000)
        prices = self.forecaster._extract_prices(small_historial)
        self.assertIsNone(prices)

    def test_predict_simple_ma(self):
        """Test simple moving average prediction."""
        prediction = self.forecaster.predict_simple_ma(self.mock_historial, horizon_minutes=5)

        self.assertIsNotNone(prediction)
        self.assertEqual(prediction['method'], 'simple_ma')
        self.assertIn('prediction', prediction)
        self.assertIn('current_price', prediction)
        self.assertIn('trend', prediction)
        self.assertIsInstance(prediction['prediction'], float)

    def test_predict_exponential_smoothing(self):
        """Test exponential smoothing prediction."""
        prediction = self.forecaster.predict_exponential_smoothing(self.mock_historial, horizon_minutes=5)

        self.assertIsNotNone(prediction)
        self.assertEqual(prediction['method'], 'exponential_smoothing')
        self.assertIn('prediction', prediction)
        self.assertIn('confidence', prediction)

    def test_predict_linear_regression(self):
        """Test linear regression prediction."""
        prediction = self.forecaster.predict_linear_regression(self.mock_historial, horizon_minutes=5)

        self.assertIsNotNone(prediction)
        self.assertEqual(prediction['method'], 'linear_regression')
        self.assertIn('r_squared', prediction)
        self.assertIn('slope', prediction)
        self.assertIn('trend', prediction)

    def test_predict_momentum_based(self):
        """Test momentum-based prediction."""
        prediction = self.forecaster.predict_momentum_based(self.mock_historial, horizon_minutes=5)

        self.assertIsNotNone(prediction)
        self.assertEqual(prediction['method'], 'momentum')
        self.assertIn('momentum', prediction)

    def test_predict_mean_reversion(self):
        """Test mean reversion prediction."""
        prediction = self.forecaster.predict_mean_reversion(self.mock_historial, horizon_minutes=5)

        self.assertIsNotNone(prediction)
        self.assertEqual(prediction['method'], 'mean_reversion')
        self.assertIn('z_score', prediction)
        self.assertIn('signal', prediction)

    def test_ensemble_forecast(self):
        """Test ensemble forecast combines multiple models."""
        forecast = self.forecaster.ensemble_forecast(self.mock_historial, horizon_minutes=5)

        self.assertIsNotNone(forecast)
        self.assertEqual(forecast['method'], 'ensemble')
        self.assertIn('prediction', forecast)
        self.assertIn('confidence', forecast)
        self.assertIn('models_used', forecast)
        self.assertIn('technical_indicators', forecast)
        self.assertGreater(forecast['num_models'], 0)

    def test_get_all_forecasts(self):
        """Test getting forecasts for multiple horizons."""
        forecasts = self.forecaster.get_all_forecasts(self.mock_historial, horizons=[1, 5, 10])

        self.assertIsInstance(forecasts, dict)
        self.assertIn('1min', forecasts)
        self.assertIn('5min', forecasts)
        self.assertIn('10min', forecasts)

    def test_generate_trading_signal(self):
        """Test trading signal generation."""
        signal = self.forecaster.generate_trading_signal(self.mock_historial)

        self.assertIsNotNone(signal)
        self.assertIn('signal', signal)
        self.assertIn(signal['signal'], ['BUY', 'SELL', 'HOLD'])
        self.assertIn('confidence', signal)
        self.assertIn('reason', signal)

    def test_technical_indicators(self):
        """Test technical indicators calculation."""
        prices = self.forecaster._extract_prices(self.mock_historial)
        indicators = self.forecaster._calculate_technical_indicators(prices)

        self.assertIsInstance(indicators, dict)
        # Check for expected indicators
        expected_indicators = ['sma', 'ema', 'momentum', 'roc', 'volatility', 'rsi']
        for indicator in expected_indicators:
            self.assertIn(indicator, indicators)


class TestFlaskAPI(unittest.TestCase):
    """Test Flask API endpoints."""

    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_index_route(self):
        """Test that index route returns HTML."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'GGAL Monitor', response.data)

    def test_health_endpoint(self):
        """Test health check endpoint."""
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['symbol'], 'GGAL')

    def test_precio_actual_endpoint(self):
        """Test current price endpoint."""
        response = self.client.get('/api/precio-actual')
        # May return 202 if no data yet, or 200 with data
        self.assertIn(response.status_code, [200, 202])

    def test_historial_endpoint(self):
        """Test historical data endpoint."""
        response = self.client.get('/api/historial')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertIsInstance(data, list)

    def test_estadisticas_endpoint(self):
        """Test statistics endpoint."""
        response = self.client.get('/api/estadisticas')
        # May return 202 if no data yet
        self.assertIn(response.status_code, [200, 202])

    def test_forecast_endpoint(self):
        """Test forecast endpoint."""
        response = self.client.get('/api/forecast')
        # May return 202 if insufficient data
        self.assertIn(response.status_code, [200, 202])

        if response.status_code == 200:
            data = json.loads(response.data)
            self.assertIsInstance(data, dict)

    def test_trading_signal_endpoint(self):
        """Test trading signal endpoint."""
        response = self.client.get('/api/trading-signal')
        # May return 202 if insufficient data
        self.assertIn(response.status_code, [200, 202])

        if response.status_code == 200:
            data = json.loads(response.data)
            self.assertIn('signal', data)
            self.assertIn(data['signal'], ['BUY', 'SELL', 'HOLD'])


class TestIntegration(unittest.TestCase):
    """Integration tests for complete workflows."""

    def test_full_forecast_pipeline(self):
        """Test complete forecasting pipeline."""
        # Create mock data
        monitor = MonitorGGAL(api_key="demo")
        forecaster = GGALForecaster(min_samples=10)

        # Add sufficient mock data
        for i in range(20):
            monitor.historial.append({
                'timestamp': datetime.now().isoformat(),
                'price': 10.0 + (i * 0.05),
                'high': 10.5 + (i * 0.05),
                'low': 9.5 + (i * 0.05),
                'open': 10.0 + (i * 0.05),
                'change': 0.05,
                'change_percent': 0.5
            })

        # Test forecast
        forecast = forecaster.ensemble_forecast(monitor.historial, horizon_minutes=5)
        self.assertIsNotNone(forecast)
        self.assertIn('prediction', forecast)

        # Test trading signal
        signal = forecaster.generate_trading_signal(monitor.historial)
        self.assertIsNotNone(signal)
        self.assertIn('signal', signal)


def run_tests():
    """Run all tests and return results."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestMonitorGGAL))
    suite.addTests(loader.loadTestsFromTestCase(TestGGALForecaster))
    suite.addTests(loader.loadTestsFromTestCase(TestFlaskAPI))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result


if __name__ == '__main__':
    print("=" * 70)
    print("GGAL Monitor - Test Suite")
    print("=" * 70)
    print()

    result = run_tests()

    print()
    print("=" * 70)
    print("Test Summary:")
    print(f"  Tests run: {result.testsRun}")
    print(f"  Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"  Failures: {len(result.failures)}")
    print(f"  Errors: {len(result.errors)}")
    print("=" * 70)

    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
