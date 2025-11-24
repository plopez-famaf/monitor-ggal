#!/usr/bin/env python3
"""
Multi-Symbol Monitor - REPL CLI Interface
Supports stocks (Finnhub) and crypto (Binance).
"""
import os
import sys
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

        # Command history and autocomplete
        self.history = InMemoryHistory()
        self.completer = WordCompleter(
            ['status', 's', 'forecast', 'f', 'signal', 'sig', 'accuracy', 'acc',
             'stats', 'metrics', 'm', 'history', 'h', 'symbols', 'switch', 'sw',
             'help', 'quit', 'q', 'exit'] + list(symbols_config.keys()),
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

        console.print("\n[dim]Type 'help' for commands, 'quit' to exit[/dim]")
        console.print("[dim]Command history: ↑/↓ arrows | Tab: autocomplete[/dim]\n")

        # REPL loop with prompt-toolkit (history + autocomplete)
        while self.running:
            try:
                prompt_label = f"{self.current_symbol.lower()}> "
                cmd = self.session.prompt(prompt_label).strip().lower()
                if cmd:  # Only process non-empty commands
                    self.handle_command(cmd)
            except KeyboardInterrupt:
                console.print("\n[yellow]Use 'quit' to exit[/yellow]")
            except EOFError:
                self.running = False

        # Cleanup - stop all monitors
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
        """Show 5-minute price forecast."""
        if len(self.monitor.historial) < 10:
            console.print("[yellow]Need at least 10 data points[/yellow]")
            return

        # Always 5 minutes (ignore args)
        forecasts = self.forecaster.get_all_forecasts(self.monitor.historial)

        if '5min' not in forecasts:
            console.print("[red]Forecast failed[/red]")
            return

        pred = forecasts['5min']
        current = self.monitor.historial[-1]['price']

        # Track prediction
        self.tracker.add_prediction(pred)

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
            console.print("[yellow]Need at least 3 validated predictions (wait ~15 minutes)[/yellow]")
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
  [cyan]forecast[/cyan], [cyan]f[/cyan]        5-minute price forecast (Kalman Filter)
  [cyan]signal[/cyan], [cyan]sig[/cyan]       Trading signal (BUY/SELL/HOLD)
  [cyan]accuracy[/cyan], [cyan]acc[/cyan]     Effectiveness index breakdown
  [cyan]stats[/cyan]             Statistics (max, min, avg)
  [cyan]metrics[/cyan], [cyan]m[/cyan]        Same as accuracy
  [cyan]history[/cyan], [cyan]h[/cyan]        Recent price history
  [cyan]symbols[/cyan]           List available symbols
  [cyan]switch[/cyan], [cyan]sw[/cyan]        Switch to different symbol
  [cyan]help[/cyan]              Show this help
  [cyan]quit[/cyan], [cyan]q[/cyan]           Exit

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
        console.print(help_text)

    def cmd_quit(self):
        """Exit REPL."""
        self.running = False


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
