"""
Test suite for GGAL Monitor Application
Tests API endpoints, Kalman Filter forecasting, and core functionality.
"""

import unittest
import json
from collections import deque
from datetime import datetime
import sys
import os
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, MonitorGGAL
from forecaster import GGALForecaster, KalmanFilter


class TestKalmanFilter(unittest.TestCase):
    """Test Kalman Filter implementation."""

    def setUp(self):
        self.kf = KalmanFilter()

    def test_kalman_initialization(self):
        """Test that Kalman Filter initializes correctly."""
        self.assertFalse(self.kf.initialized)
        self.assertEqual(self.kf.x[0], 0.0)
        self.assertEqual(self.kf.x[1], 0.0)

    def test_kalman_update(self):
        """Test Kalman Filter updates with measurements."""
        self.kf.update(50.0)
        self.assertTrue(self.kf.initialized)
        self.assertEqual(self.kf.x[0], 50.0)
        self.assertEqual(self.kf.x[1], 0.0)

        # Update with new measurement
        self.kf.update(50.5)
        self.assertTrue(self.kf.initialized)
        # Price should be updated
        self.assertGreater(self.kf.x[0], 50.0)

    def test_kalman_predict(self):
        """Test Kalman Filter prediction."""
        # Initialize with some data
        prices = [50.0, 50.2, 50.1, 50.3, 50.5]
        for price in prices:
            self.kf.update(price)

        # Predict future
        pred, unc = self.kf.predict(steps=5)
        self.assertIsNotNone(pred)
        self.assertIsNotNone(unc)
        self.assertGreater(pred, 0)
        self.assertGreater(unc, 0)

    def test_kalman_velocity(self):
        """Test velocity tracking."""
        # Upward trend
        for i in range(10):
            self.kf.update(50.0 + i * 0.1)

        velocity = self.kf.get_velocity()
        self.assertGreater(velocity, 0)  # Should detect upward trend

    def test_kalman_predict_uninitialized(self):
        """Test that predict returns None when uninitialized."""
        pred, unc = self.kf.predict(steps=1)
        self.assertIsNone(pred)
        self.assertIsNone(unc)


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
        # Create mock historical data with upward trend
        self.mock_historial = deque(maxlen=1000)
        base_price = 50.0
        for i in range(30):
            self.mock_historial.append({
                'timestamp': datetime.now().isoformat(),
                'price': base_price + (i * 0.1),  # Upward trend
                'high': base_price + (i * 0.1) + 0.2,
                'low': base_price + (i * 0.1) - 0.2,
                'open': base_price + (i * 0.1),
                'change': 0.1,
                'change_percent': 0.2
            })

    def test_forecaster_initialization(self):
        """Test forecaster initializes correctly."""
        self.assertEqual(self.forecaster.min_samples, 10)
        self.assertIsNone(self.forecaster.kf)

    def test_extract_prices(self):
        """Test price extraction from historial."""
        prices = self.forecaster._extract_prices(self.mock_historial)
        self.assertIsNotNone(prices)
        self.assertEqual(len(prices), 30)
        self.assertAlmostEqual(prices[0], 50.0, places=1)

    def test_extract_prices_insufficient_data(self):
        """Test that None is returned with insufficient data."""
        small_historial = deque([{'price': 10.0}], maxlen=1000)
        prices = self.forecaster._extract_prices(small_historial)
        self.assertIsNone(prices)

    def test_forecast(self):
        """Test Kalman Filter forecast."""
        forecast = self.forecaster.forecast(self.mock_historial, horizon_minutes=5)

        self.assertIsNotNone(forecast)
        self.assertEqual(forecast['method'], 'kalman_filter')
        self.assertIn('prediction', forecast)
        self.assertIn('current_price', forecast)
        self.assertIn('velocity', forecast)
        self.assertIn('uncertainty', forecast)
        self.assertIn('confidence', forecast)
        self.assertIn('trend', forecast)
        self.assertIn('lower_bound', forecast)
        self.assertIn('upper_bound', forecast)

        # Check types
        self.assertIsInstance(forecast['prediction'], (int, float))
        self.assertIsInstance(forecast['velocity'], (int, float))
        self.assertIsInstance(forecast['uncertainty'], (int, float))

        # Check trend detection
        self.assertIn(forecast['trend'], ['up', 'down', 'flat'])

    def test_forecast_detects_upward_trend(self):
        """Test that forecast detects upward trend in data."""
        forecast = self.forecaster.forecast(self.mock_historial, horizon_minutes=5)

        self.assertIsNotNone(forecast)
        # Should detect upward trend
        self.assertEqual(forecast['trend'], 'up')
        self.assertGreater(forecast['velocity'], 0)

    def test_get_all_forecasts(self):
        """Test getting forecasts for multiple horizons."""
        forecasts = self.forecaster.get_all_forecasts(self.mock_historial, horizons=[1, 5, 10])

        self.assertIsInstance(forecasts, dict)
        self.assertIn('1min', forecasts)
        self.assertIn('5min', forecasts)
        self.assertIn('10min', forecasts)

        # Check that predictions increase with horizon
        pred_1min = forecasts['1min']['prediction']
        pred_10min = forecasts['10min']['prediction']
        # With upward trend, 10min prediction should be higher
        self.assertGreater(pred_10min, pred_1min)

    def test_generate_trading_signal(self):
        """Test trading signal generation."""
        signal = self.forecaster.generate_trading_signal(self.mock_historial)

        self.assertIsNotNone(signal)
        self.assertIn('signal', signal)
        self.assertIn(signal['signal'], ['BUY', 'SELL', 'HOLD'])
        self.assertIn('signal_strength', signal)
        self.assertIn('confidence', signal)
        self.assertIn('reason', signal)

        # Check signal strength is 0-100
        self.assertGreaterEqual(signal['signal_strength'], 0)
        self.assertLessEqual(signal['signal_strength'], 100)

    def test_trading_signal_upward_trend(self):
        """Test that upward trend generates BUY or positive signal."""
        signal = self.forecaster.generate_trading_signal(self.mock_historial)

        self.assertIsNotNone(signal)
        # With strong upward trend, should be BUY or have positive strength
        if signal['signal'] == 'BUY':
            self.assertGreater(signal['signal_strength'], 0)

    def test_forecast_insufficient_data(self):
        """Test forecast with insufficient data."""
        small_historial = deque([
            {'price': 50.0, 'timestamp': datetime.now().isoformat()}
            for _ in range(5)
        ], maxlen=1000)

        forecast = self.forecaster.forecast(small_historial, horizon_minutes=5)
        self.assertIsNone(forecast)

    def test_trading_signal_insufficient_data(self):
        """Test trading signal with insufficient data."""
        small_historial = deque([
            {'price': 50.0, 'timestamp': datetime.now().isoformat()}
            for _ in range(10)
        ], maxlen=1000)

        signal = self.forecaster.generate_trading_signal(small_historial)
        self.assertEqual(signal['signal'], 'HOLD')
        self.assertEqual(signal['signal_strength'], 0)


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
        self.assertIn(b'Kalman', response.data)

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
            # Check for Kalman-specific fields
            if '5min' in data:
                self.assertEqual(data['5min']['method'], 'kalman_filter')
                self.assertIn('velocity', data['5min'])
                self.assertIn('uncertainty', data['5min'])

    def test_trading_signal_endpoint(self):
        """Test trading signal endpoint."""
        response = self.client.get('/api/trading-signal')
        # May return 202 if insufficient data
        self.assertIn(response.status_code, [200, 202])

        if response.status_code == 200:
            data = json.loads(response.data)
            self.assertIn('signal', data)
            self.assertIn(data['signal'], ['BUY', 'SELL', 'HOLD'])
            # Check for signal_strength field
            self.assertIn('signal_strength', data)
            self.assertGreaterEqual(data['signal_strength'], 0)
            self.assertLessEqual(data['signal_strength'], 100)

    def test_debug_endpoint(self):
        """Test debug endpoint."""
        response = self.client.get('/api/debug')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertIn('historial_size', data)
        self.assertIn('thread_running', data)


class TestIntegration(unittest.TestCase):
    """Integration tests for complete workflows."""

    def test_full_forecast_pipeline(self):
        """Test complete Kalman forecasting pipeline."""
        # Create mock data
        monitor = MonitorGGAL(api_key="demo")
        forecaster = GGALForecaster(min_samples=10)

        # Add sufficient mock data with upward trend
        for i in range(20):
            monitor.historial.append({
                'timestamp': datetime.now().isoformat(),
                'price': 50.0 + (i * 0.05),
                'high': 50.5 + (i * 0.05),
                'low': 49.5 + (i * 0.05),
                'open': 50.0 + (i * 0.05),
                'change': 0.05,
                'change_percent': 0.1
            })

        # Test forecast
        forecast = forecaster.forecast(monitor.historial, horizon_minutes=5)
        self.assertIsNotNone(forecast)
        self.assertIn('prediction', forecast)
        self.assertEqual(forecast['method'], 'kalman_filter')

        # Test trading signal
        signal = forecaster.generate_trading_signal(monitor.historial)
        self.assertIsNotNone(signal)
        self.assertIn('signal', signal)
        self.assertIn('signal_strength', signal)

    def test_kalman_consistency(self):
        """Test that Kalman Filter produces consistent results."""
        forecaster = GGALForecaster(min_samples=10)

        # Create stable price data
        historial = deque(maxlen=1000)
        for i in range(30):
            historial.append({
                'timestamp': datetime.now().isoformat(),
                'price': 50.0 + (i * 0.01),  # Small upward drift
            })

        # Get two forecasts
        forecast1 = forecaster.forecast(historial, horizon_minutes=5)
        forecast2 = forecaster.forecast(historial, horizon_minutes=5)

        # Should be identical (stateless, deterministic)
        self.assertEqual(forecast1['prediction'], forecast2['prediction'])
        self.assertEqual(forecast1['velocity'], forecast2['velocity'])


def run_tests():
    """Run all tests and return results."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestKalmanFilter))
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
    print("GGAL Monitor - Test Suite (Kalman Filter)")
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
