#!/usr/bin/env python3
"""
Multi-Symbol Monitor - REPL CLI Interface
Supports stocks (Finnhub) and crypto (Binance).
"""
import os
import sys
import time
import threading
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import InMemoryHistory
from monitor import PriceMonitor
from forecaster import GGALForecaster
from prediction_tracker import PredictionTracker

console = Console()


class MultiSymbolCLI:
    """REPL interface for multi-symbol monitoring."""

    def __init__(self, symbols_config, use_automl=False):
        """
        Initialize CLI with multiple symbols.

        Args:
            symbols_config: Dict mapping symbol keys to config dicts
                Example: {
                    'GGAL': {'type': 'stock', 'api_key': 'xxx', 'name': 'Banco Galicia ADR'},
                    'BTC': {'type': 'crypto', 'symbol': 'BTCUSDT', 'name': 'Bitcoin/USDT'}
                }
            use_automl: If True, use Ensemble forecaster (Kalman + Auto-ARIMA)
        """
        self.symbols_config = symbols_config
        self.monitors = {}
        self.forecasters = {}
        self.trackers = {}
        self.running = True
        self.use_automl = use_automl

        # Import forecaster based on mode
        if use_automl:
            from ensemble_forecaster import EnsembleForecaster
            forecaster_class = EnsembleForecaster
            min_samples = 30
        else:
            forecaster_class = GGALForecaster
            min_samples = 10

        # Initialize monitors for each symbol
        for key, config in symbols_config.items():
            symbol = config.get('symbol', key)  # Use symbol if specified, else key
            self.monitors[key] = PriceMonitor(
                symbol=symbol,
                api_type=config['type'],
                api_key=config.get('api_key')
            )
            self.forecasters[key] = forecaster_class(min_samples=min_samples)
            self.trackers[key] = PredictionTracker(max_predictions=100)

        # Start with first symbol
        self.current_symbol = list(symbols_config.keys())[0]

        # Price alerts configuration
        self.alerts_enabled = True
        self.alert_threshold = float(os.environ.get('ALERT_THRESHOLD', '0.1'))  # Default 0.1%
        self.pending_alerts = {}  # symbol -> alert_message

        # Continuous forecasting
        self.forecast_interval = int(os.environ.get('FORECAST_INTERVAL', '30'))  # seconds
        self.last_forecasts = {}  # symbol -> forecast_data
        self.forecasting_running = False
        self._forecast_thread = None

        # Command history and autocomplete
        self.history = InMemoryHistory()
        self.completer = WordCompleter(
            ['status', 's', 'forecast', 'f', 'signal', 'sig', 'accuracy', 'acc',
             'stats', 'metrics', 'm', 'history', 'h', 'symbols', 'switch', 'sw',
             'alerts', 'alert', 'help', 'quit', 'q', 'exit'] + list(symbols_config.keys()),
            ignore_case=True
        )
        self.session = PromptSession(history=self.history, completer=self.completer)

    @property
    def monitor(self):
        """Get current symbol's monitor."""
        return self.monitors[self.current_symbol]

    @property
    def forecaster(self):
        """Get current symbol's forecaster."""
        return self.forecasters[self.current_symbol]

    @property
    def tracker(self):
        """Get current symbol's tracker."""
        return self.trackers[self.current_symbol]

    def start(self):
        """Start background monitoring and REPL."""
        model_type = "Ensemble (Kalman + Auto-ARIMA)" if self.use_automl else "Kalman Filter"
        console.print(f"\n[bold cyan]Multi-Symbol Monitor CLI[/bold cyan] - {model_type} Forecasting\n")

        # Start monitoring threads for all symbols
        for key, monitor in self.monitors.items():
            monitor.start(intervalo=10)
            console.print(f"[dim]Started monitoring {key} ({self.symbols_config[key]['name']})[/dim]")

        # Start continuous forecasting thread
        self._start_forecasting()
        console.print(f"[dim]Started continuous forecasting (every {self.forecast_interval}s)[/dim]")

        console.print("\n[dim]Type 'help' for commands, 'quit' to exit[/dim]")
        console.print("[dim]Command history: ↑/↓ arrows | Tab: autocomplete[/dim]")
        if self.alerts_enabled:
            console.print(f"[dim]Price alerts: ON (threshold: {self.alert_threshold}%)[/dim]\n")
        else:
            console.print("[dim]Price alerts: OFF[/dim]\n")

        # REPL loop with prompt-toolkit (history + autocomplete)
        while self.running:
            try:
                # Show alert banner if any pending (alerts detected by background thread)
                if self.pending_alerts:
                    self._display_alerts()

                prompt_label = f"{self.current_symbol.lower()}> "
                cmd = self.session.prompt(prompt_label).strip().lower()
                if cmd:  # Only process non-empty commands
                    self.handle_command(cmd)
            except KeyboardInterrupt:
                console.print("\n[yellow]Use 'quit' to exit[/yellow]")
            except EOFError:
                self.running = False

        # Cleanup - stop all threads
        self._stop_forecasting()
        for monitor in self.monitors.values():
            monitor.stop()
        console.print("\n[dim]Goodbye![/dim]")

    def handle_command(self, cmd):
        """Route command to handler."""
        parts = cmd.split()
        command = parts[0] if parts else ""
        args = parts[1:] if len(parts) > 1 else []

        handlers = {
            "status": self.cmd_status,
            "s": self.cmd_status,
            "forecast": lambda: self.cmd_forecast(args),
            "f": lambda: self.cmd_forecast(args),
            "signal": self.cmd_signal,
            "sig": self.cmd_signal,
            "stats": self.cmd_stats,
            "accuracy": self.cmd_accuracy,
            "acc": self.cmd_accuracy,
            "metrics": self.cmd_metrics,
            "m": self.cmd_metrics,
            "history": self.cmd_history,
            "h": self.cmd_history,
            "symbols": self.cmd_symbols,
            "switch": lambda: self.cmd_switch(args),
            "sw": lambda: self.cmd_switch(args),
            "alerts": lambda: self.cmd_alerts(args),
            "alert": lambda: self.cmd_alerts(args),
            "help": self.cmd_help,
            "quit": self.cmd_quit,
            "q": self.cmd_quit,
            "exit": self.cmd_quit,
        }

        handler = handlers.get(command)
        if handler:
            handler()
        elif command:
            console.print(f"[red]Unknown command:[/red] {command}")
            console.print("[dim]Type 'help' for available commands[/dim]")

    def cmd_status(self):
        """Show current price with effectiveness index."""
        if not self.monitor.historial:
            console.print("[yellow]Waiting for data...[/yellow]")
            return

        data = self.monitor.historial[-1]
        price = data['price']
        change = data['change']
        change_pct = data['change_percent']
        timestamp = datetime.fromisoformat(data['timestamp']).strftime('%H:%M:%S')

        # Color based on change
        arrow = "↗" if change >= 0 else "↘"
        color = "green" if change >= 0 else "red"
        sign = "+" if change >= 0 else ""

        console.print(
            f"[bold]{arrow} ${price:.2f}[/bold] "
            f"[{color}]{sign}{change:.2f} ({sign}{change_pct:.2f}%)[/{color}] "
            f"[dim]| {timestamp}[/dim]"
        )

        # Show effectiveness index if available
        self.tracker.validate_predictions(self.monitor.historial)
        metrics = self.tracker.get_accuracy_metrics()

        if metrics['validated_predictions'] >= 3:
            effectiveness = metrics['effectiveness_index']
            rating = metrics['rating']

            # Visual bar (10 blocks)
            filled = int(effectiveness / 10)
            bar = "█" * filled + "░" * (10 - filled)

            # Color based on rating
            if effectiveness >= 80:
                eff_color = "bright_green"
            elif effectiveness >= 70:
                eff_color = "green"
            elif effectiveness >= 60:
                eff_color = "yellow"
            else:
                eff_color = "red"

            console.print(
                f"\nPrediction Effectiveness: [{eff_color}]{bar} {effectiveness}/100 ({rating})[/{eff_color}]"
            )

            m = metrics['metrics']
            console.print(
                f"[dim]  ├─ Direction: "
                f"{m['correct_direction_count']}/{m['total_direction_count']} correct "
                f"({m['directional_accuracy']:.1f}%)[/dim]"
            )
            console.print(
                f"[dim]  ├─ Accuracy: MAPE {m['mape']:.2f}% "
                f"({'excellent' if m['mape'] < 0.5 else 'good' if m['mape'] < 1.0 else 'fair'})[/dim]"
            )
            console.print(
                f"[dim]  └─ Calibration: {int(m['interval_coverage'])}% within CI "
                f"({'optimal' if 90 <= m['interval_coverage'] <= 98 else 'needs tuning'})[/dim]"
            )

    def cmd_forecast(self, args):
        """Show current 5-minute price forecast (generated by background thread)."""
        # Check if we have a forecast for current symbol
        if self.current_symbol not in self.last_forecasts:
            if len(self.monitor.historial) < 10:
                console.print("[yellow]Need at least 10 data points for forecasting[/yellow]")
                console.print(f"[dim]Currently have: {len(self.monitor.historial)} data points[/dim]")
            else:
                console.print("[yellow]No forecast available yet. Waiting for next forecast cycle...[/yellow]")
                console.print(f"[dim]Forecasts are generated every {self.forecast_interval} seconds[/dim]")
            return

        # Get latest forecast from background thread
        pred = self.last_forecasts[self.current_symbol]
        current = self.monitor.historial[-1]['price']

        # Note: prediction is already tracked by background thread

        # Color based on change
        arrow = "↗" if pred['price_change'] >= 0 else "↘"
        color = "green" if pred['price_change'] >= 0 else "red"
        sign = "+" if pred['price_change'] >= 0 else ""

        # Build table
        table = Table.grid(padding=(0, 2))
        table.add_column(style="dim")
        table.add_column()

        # Extract timestamp and format it
        forecast_time = datetime.fromisoformat(pred['timestamp']).strftime('%H:%M:%S')
        target_time = datetime.fromisoformat(pred['timestamp'])
        from datetime import timedelta
        target_time = (target_time + timedelta(minutes=5)).strftime('%H:%M:%S')

        table.add_row("Forecast at:", f"[dim]{forecast_time}[/dim]")
        table.add_row("Target time:", f"[dim]{target_time}[/dim]")
        table.add_row("Horizon:", f"[bold]5 min[/bold] (fixed)")
        table.add_row("Current:", f"${current:.2f}")
        table.add_row("Predicted:", f"[bold]{arrow} ${pred['prediction']:.2f}[/bold]")
        table.add_row("Change:", f"[{color}]{sign}{pred['price_change']:.2f} ({sign}{pred['price_change_pct']:.2f}%)[/{color}]")
        table.add_row("Velocity:", f"{pred['velocity']:.4f} $/min")
        table.add_row("IC 95%:", f"${pred['lower_bound']:.2f} - ${pred['upper_bound']:.2f}")
        table.add_row("Trend:", f"[bold]{pred['trend'].upper()}[/bold]")

        # Show model type if using AutoML
        if 'model_type' in pred:
            table.add_row("Model:", f"[dim]{pred['model_type']}[/dim]")
            if 'model_order' in pred:
                table.add_row("ARIMA order:", f"[dim]{pred['model_order']}[/dim]")

        console.print(table)

    def cmd_signal(self):
        """Show trading signal."""
        if len(self.monitor.historial) < 15:
            console.print("[yellow]Need at least 15 data points[/yellow]")
            return

        signal = self.forecaster.generate_trading_signal(self.monitor.historial)

        # Color based on signal
        colors = {"BUY": "green", "SELL": "red", "HOLD": "yellow"}
        color = colors.get(signal['signal'], "white")

        # Strength bar
        strength = signal.get('signal_strength', 0)
        bar_length = 20
        filled = int((strength / 100) * bar_length)
        bar = "█" * filled + "░" * (bar_length - filled)

        console.print(
            f"[bold {color}]{signal['signal']}[/bold {color}] "
            f"[dim]{bar}[/dim] {strength}/100"
        )
        console.print(f"[dim]{signal['reason']}[/dim]")

    def cmd_stats(self):
        """Show statistics."""
        if not self.monitor.historial:
            console.print("[yellow]No data available[/yellow]")
            return

        precios = [p["price"] for p in self.monitor.historial]
        max_price = max(precios)
        min_price = min(precios)
        avg_price = sum(precios) / len(precios)

        table = Table.grid(padding=(0, 2))
        table.add_column(style="dim")
        table.add_column()

        table.add_row("Samples:", f"{len(precios)}")
        table.add_row("Max:", f"[green]${max_price:.2f}[/green]")
        table.add_row("Min:", f"[red]${min_price:.2f}[/red]")
        table.add_row("Avg:", f"${avg_price:.2f}")
        table.add_row("Range:", f"${max_price - min_price:.2f}")

        console.print(table)

    def cmd_accuracy(self):
        """Show detailed effectiveness index breakdown."""
        # Validate pending predictions
        self.tracker.validate_predictions(self.monitor.historial)

        metrics = self.tracker.get_accuracy_metrics()

        if metrics['validated_predictions'] < 3:
            validated = metrics['validated_predictions']
            pending = metrics['total_predictions']

            # Calculate estimated time
            # Predictions are made every time user calls 'forecast'
            # Validation happens 5 minutes after prediction
            predictions_needed = 3 - validated

            console.print(f"\n[yellow]⏳ Insuficientes predicciones validadas[/yellow]")
            console.print(f"  • Validadas: {validated}/3")
            console.print(f"  • Pendientes de validar: {pending - validated}")
            console.print(f"  • Necesitas: {predictions_needed} predicción(es) más")
            console.print(f"\n[dim]Tip: Ejecuta 'forecast' ahora, espera 5 minutos, y vuelve a revisar 'accuracy'[/dim]")
            return

        effectiveness = metrics['effectiveness_index']
        rating = metrics['rating']
        m = metrics['metrics']

        # Header with big effectiveness score
        filled = int(effectiveness / 10)
        bar = "█" * filled + "░" * (10 - filled)

        if effectiveness >= 80:
            eff_color = "bright_green"
        elif effectiveness >= 70:
            eff_color = "green"
        elif effectiveness >= 60:
            eff_color = "yellow"
        else:
            eff_color = "red"

        console.print(f"\n[bold]Prediction Effectiveness Index[/bold]")
        console.print(f"[{eff_color}]{bar} {effectiveness}/100 ({rating})[/{eff_color}]\n")

        # Component breakdown
        console.print("[bold]Component Scores:[/bold]")

        # Direction
        dir_acc = m['directional_accuracy']
        dir_color = "green" if dir_acc >= 70 else "yellow" if dir_acc >= 60 else "red"
        console.print(f"  [{dir_color}]▸ Direction:[/{dir_color}] {dir_acc:.1f}% "
                     f"({m['correct_direction_count']}/{m['total_direction_count']} correct)")

        # Price accuracy
        mape = m['mape']
        price_color = "green" if mape < 0.5 else "yellow" if mape < 1.0 else "red"
        console.print(f"  [{price_color}]▸ Price Accuracy:[/{price_color}] MAPE {mape:.2f}% "
                     f"(MAE ${m['mae']:.3f})")

        # Calibration
        coverage = m['interval_coverage']
        cal_color = "green" if 90 <= coverage <= 98 else "yellow" if 85 <= coverage <= 99 else "red"
        console.print(f"  [{cal_color}]▸ Calibration:[/{cal_color}] {coverage:.1f}% within 95% CI")

        # Summary
        console.print(f"\n[dim]{metrics['summary']}[/dim]")
        console.print(f"[dim]Based on {metrics['validated_predictions']} validated predictions (5-min horizon)[/dim]")

    def cmd_metrics(self):
        """Show prediction accuracy metrics (alias for accuracy)."""
        self.cmd_accuracy()

    def cmd_history(self):
        """Show recent price history."""
        if not self.monitor.historial:
            console.print("[yellow]No data available[/yellow]")
            return

        # Show last 10 entries
        recent = list(self.monitor.historial)[-10:]

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Time", style="dim")
        table.add_column("Price", justify="right")
        table.add_column("Change", justify="right")

        for entry in recent:
            timestamp = datetime.fromisoformat(entry['timestamp']).strftime('%H:%M:%S')
            price = f"${entry['price']:.2f}"
            change = entry['change']
            change_pct = entry['change_percent']

            color = "green" if change >= 0 else "red"
            sign = "+" if change >= 0 else ""
            change_str = f"[{color}]{sign}{change:.2f} ({sign}{change_pct:.2f}%)[/{color}]"

            table.add_row(timestamp, price, change_str)

        console.print(table)

    def cmd_symbols(self):
        """Show available symbols."""
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Key", style="cyan")
        table.add_column("Symbol", style="white")
        table.add_column("Name", style="dim")
        table.add_column("Type", justify="center")
        table.add_column("Status", justify="center")

        for key, config in self.symbols_config.items():
            symbol = config.get('symbol', key)
            name = config['name']
            api_type = config['type']
            monitor = self.monitors[key]

            # Check if has data
            status = "✓" if len(monitor.historial) > 0 else "⏳"
            status_color = "green" if len(monitor.historial) > 0 else "yellow"

            # Highlight current symbol
            if key == self.current_symbol:
                key_display = f"[bold]{key} ◄[/bold]"
            else:
                key_display = key

            table.add_row(
                key_display,
                symbol,
                name,
                api_type,
                f"[{status_color}]{status}[/{status_color}]"
            )

        console.print(table)
        console.print(f"\n[dim]Current: {self.current_symbol} | Use 'switch <key>' to change[/dim]")

    def cmd_switch(self, args):
        """Switch to different symbol."""
        if not args:
            console.print("[yellow]Usage: switch <symbol_key>[/yellow]")
            console.print(f"[dim]Available: {', '.join(self.symbols_config.keys())}[/dim]")
            return

        target = args[0].upper()

        if target not in self.symbols_config:
            console.print(f"[red]Unknown symbol: {target}[/red]")
            console.print(f"[dim]Available: {', '.join(self.symbols_config.keys())}[/dim]")
            return

        self.current_symbol = target
        config = self.symbols_config[target]
        console.print(f"[green]Switched to {target}[/green] ({config['name']})")

    def cmd_help(self):
        """Show help."""
        help_text = """
[bold]Available commands:[/bold]

  [cyan]status[/cyan], [cyan]s[/cyan]          Current price + effectiveness index
  [cyan]forecast[/cyan], [cyan]f[/cyan]        Show current 5-min forecast (auto-generated)
  [cyan]signal[/cyan], [cyan]sig[/cyan]       Trading signal (BUY/SELL/HOLD)
  [cyan]accuracy[/cyan], [cyan]acc[/cyan]     Effectiveness index breakdown
  [cyan]stats[/cyan]             Statistics (max, min, avg)
  [cyan]metrics[/cyan], [cyan]m[/cyan]        Same as accuracy
  [cyan]history[/cyan], [cyan]h[/cyan]        Recent price history
  [cyan]symbols[/cyan]           List available symbols
  [cyan]switch[/cyan], [cyan]sw[/cyan]        Switch to different symbol
  [cyan]alerts[/cyan]            Configure price alerts (on/off/threshold)
  [cyan]help[/cyan]              Show this help
  [cyan]quit[/cyan], [cyan]q[/cyan]           Exit

[bold]Continuous Forecasting:[/bold]
  [dim]Forecasts are auto-generated every {interval}s in the background[/dim]
  [dim]• Predictions are validated automatically after 5 minutes[/dim]
  [dim]• Alerts trigger when price change exceeds threshold[/dim]

[bold]Multi-Symbol Support:[/bold]
  [dim]Monitor multiple assets simultaneously with independent forecasters[/dim]
  [dim]• Each symbol has its own Kalman Filter and effectiveness index[/dim]
  [dim]• Switch between symbols without losing data[/dim]

[dim]Examples:[/dim]
  ggal> symbols          # List all symbols
  ggal> switch btc       # Switch to Bitcoin
  btc> status            # Bitcoin price
  btc> forecast          # Bitcoin forecast
  btc> switch ggal       # Back to GGAL
"""
        # Format with actual interval value
        help_text = help_text.replace('{interval}', str(self.forecast_interval))
        console.print(help_text)

    def _check_alerts(self):
        """Check all symbols for significant price movements in forecasts."""
        if not self.alerts_enabled:
            return

        for key, monitor in self.monitors.items():
            # Skip if not enough data
            if len(monitor.historial) < 10:
                continue

            # Get forecast for this symbol
            forecaster = self.forecasters[key]
            forecasts = forecaster.get_all_forecasts(monitor.historial)

            if '5min' in forecasts:
                pred = forecasts['5min']
                change_pct = abs(pred['price_change_pct'])

                # Check if exceeds threshold
                if change_pct >= self.alert_threshold:
                    # Create alert message
                    direction = "↗ SUBE" if pred['price_change'] > 0 else "↘ BAJA"
                    color = "green" if pred['price_change'] > 0 else "red"

                    alert_msg = {
                        'symbol': key,
                        'direction': direction,
                        'color': color,
                        'change_pct': pred['price_change_pct'],
                        'current': pred['current_price'],
                        'predicted': pred['prediction'],
                        'timestamp': datetime.now()
                    }

                    # Update pending alerts
                    self.pending_alerts[key] = alert_msg

    def _display_alerts(self):
        """Display pending price alerts."""
        if not self.pending_alerts:
            return

        console.print("\n[bold yellow]🔔 ALERTAS DE PRECIO:[/bold yellow]")

        for key, alert in self.pending_alerts.items():
            symbol_name = self.symbols_config[key]['name']
            color = alert['color']
            direction = alert['direction']
            change_pct = alert['change_pct']
            current = alert['current']
            predicted = alert['predicted']

            console.print(
                f"  [{color}]• {key}[/{color}] ({symbol_name}): {direction} "
                f"[bold]{change_pct:+.2f}%[/bold] | ${current:.2f} → ${predicted:.2f}"
            )

        console.print("[dim]Escribe cualquier comando para continuar...[/dim]\n")

        # Clear alerts after display
        self.pending_alerts.clear()

    def cmd_alerts(self, args):
        """Configure or show alert settings."""
        if not args:
            # Show current settings
            status = "ON" if self.alerts_enabled else "OFF"
            console.print(f"\n[bold]Alert Settings:[/bold]")
            console.print(f"  Status: [{('green' if self.alerts_enabled else 'red')}]{status}[/]")
            console.print(f"  Threshold: {self.alert_threshold}%")
            console.print(f"\n[dim]Usage:[/dim]")
            console.print(f"  [cyan]alerts on[/cyan]  - Enable alerts")
            console.print(f"  [cyan]alerts off[/cyan] - Disable alerts")
            console.print(f"  [cyan]alerts 0.5[/cyan] - Set threshold to 0.5%")
            return

        cmd = args[0].lower()

        if cmd == "on":
            self.alerts_enabled = True
            console.print("[green]✓ Alerts enabled[/green]")
        elif cmd == "off":
            self.alerts_enabled = False
            self.pending_alerts.clear()
            console.print("[yellow]Alerts disabled[/yellow]")
        else:
            # Try to parse as threshold
            try:
                new_threshold = float(cmd)
                if 0 < new_threshold <= 100:
                    self.alert_threshold = new_threshold
                    console.print(f"[green]✓ Alert threshold set to {new_threshold}%[/green]")
                else:
                    console.print("[red]Threshold must be between 0 and 100[/red]")
            except ValueError:
                console.print("[red]Invalid command. Use: alerts on/off/NUMBER[/red]")

    def cmd_quit(self):
        """Exit REPL."""
        self.running = False

    def _start_forecasting(self):
        """Start continuous forecasting background thread."""
        if not self.forecasting_running:
            self.forecasting_running = True
            self._forecast_thread = threading.Thread(
                target=self.continuous_forecasting_loop,
                daemon=True
            )
            self._forecast_thread.start()

    def _stop_forecasting(self):
        """Stop continuous forecasting thread."""
        self.forecasting_running = False
        if self._forecast_thread:
            self._forecast_thread.join(timeout=2)

    def continuous_forecasting_loop(self):
        """
        Background loop that continuously:
        1. Generates forecasts for all symbols
        2. Validates old predictions
        3. Checks for alerts
        """
        while self.forecasting_running:
            try:
                # Process each symbol
                for key, monitor in self.monitors.items():
                    historial = monitor.historial

                    if len(historial) < 10:
                        # Not enough data yet
                        continue

                    # Generate forecast
                    forecaster = self.forecasters.get(key)
                    if not forecaster:
                        continue

                    forecast = forecaster.forecast(historial)

                    if forecast:
                        # Store latest forecast
                        self.last_forecasts[key] = forecast

                        # Add prediction to tracker for validation
                        tracker = self.trackers.get(key)
                        if tracker:
                            tracker.add_prediction(forecast)

                            # Validate old predictions
                            validated_count = tracker.validate_predictions(historial)
                            if validated_count > 0:
                                # Optionally log validation events
                                pass

                        # Check for alerts
                        if self.alerts_enabled:
                            change_pct = abs(forecast['price_change_pct'])
                            if change_pct >= self.alert_threshold:
                                direction = "↗" if forecast['price_change'] > 0 else "↘"
                                self.pending_alerts[key] = {
                                    'forecast': forecast,
                                    'direction': direction,
                                    'change_pct': change_pct
                                }

                # Sleep until next iteration
                time.sleep(self.forecast_interval)

            except Exception as e:
                # Don't crash the thread on errors
                print(f"⚠️  Error in forecasting loop: {type(e).__name__}: {str(e)[:100]}")
                time.sleep(self.forecast_interval)


def main():
    """Entry point."""
    finnhub_key = os.environ.get('FINNHUB_API_KEY')
    binance_key = os.environ.get('BINANCE_API_KEY')  # Optional

    # Configure symbols
    symbols_config = {
        'GGAL': {
            'type': 'stock',
            'api_key': finnhub_key,
            'name': 'Banco Galicia ADR'
        }
    }

    # Add BTC if user wants it (optional)
    if os.environ.get('ENABLE_CRYPTO', '').lower() in ('true', '1', 'yes'):
        symbols_config['BTC'] = {
            'type': 'crypto',
            'symbol': 'BTCUSDT',
            'api_key': binance_key,  # Not required for public endpoints
            'name': 'Bitcoin / USDT'
        }

    # Validate we have at least Finnhub key
    if not finnhub_key:
        console.print("[bold red]Error:[/bold red] FINNHUB_API_KEY not set")
        console.print("\n[dim]Get a free API key at: https://finnhub.io[/dim]")
        console.print("[dim]Then run: export FINNHUB_API_KEY='your_key'[/dim]")
        console.print("\n[dim]To enable crypto: export ENABLE_CRYPTO=true[/dim]")
        console.print("[dim]To enable AutoML: export USE_AUTOML=true[/dim]\n")
        sys.exit(1)

    # Check if user wants AutoML (Ensemble forecaster)
    use_automl = os.environ.get('USE_AUTOML', '').lower() in ('true', '1', 'yes')

    cli = MultiSymbolCLI(symbols_config=symbols_config, use_automl=use_automl)
    cli.start()


if __name__ == '__main__':
    main()
