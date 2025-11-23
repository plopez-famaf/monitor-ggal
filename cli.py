#!/usr/bin/env python3
"""
GGAL Monitor - REPL CLI Interface
Minimal boilerplate, maximum performance.
"""
import os
import sys
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt
from monitor import MonitorGGAL
from forecaster import GGALForecaster
from prediction_tracker import PredictionTracker

console = Console()


class GGALCLI:
    """Minimal REPL interface for GGAL monitoring."""

    def __init__(self, api_key):
        self.monitor = MonitorGGAL(api_key=api_key)
        self.forecaster = GGALForecaster(min_samples=10)
        self.tracker = PredictionTracker(max_predictions=100)
        self.running = True

    def start(self):
        """Start background monitoring and REPL."""
        console.print("\n[bold cyan]GGAL Monitor CLI[/bold cyan] - Kalman Filter Forecasting\n")

        # Start monitoring thread
        self.monitor.start(intervalo=10)
        console.print("[dim]Background monitoring started (10s interval)[/dim]")
        console.print("[dim]Type 'help' for commands, 'quit' to exit[/dim]\n")

        # REPL loop
        while self.running:
            try:
                cmd = Prompt.ask("[bold green]ggal[/bold green]", default="status").strip().lower()
                self.handle_command(cmd)
            except KeyboardInterrupt:
                console.print("\n[yellow]Use 'quit' to exit[/yellow]")
            except EOFError:
                self.running = False

        # Cleanup
        self.monitor.stop()
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
            "metrics": self.cmd_metrics,
            "m": self.cmd_metrics,
            "history": self.cmd_history,
            "h": self.cmd_history,
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
        """Show current price."""
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

    def cmd_forecast(self, args):
        """Show price forecast."""
        if len(self.monitor.historial) < 10:
            console.print("[yellow]Need at least 10 data points[/yellow]")
            return

        # Parse horizon (default 5)
        horizon = int(args[0]) if args and args[0].isdigit() else 5
        if horizon not in [1, 5, 10]:
            console.print("[red]Invalid horizon. Use 1, 5, or 10[/red]")
            return

        forecasts = self.forecaster.get_all_forecasts(self.monitor.historial, horizons=[horizon])
        key = f"{horizon}min"

        if key not in forecasts:
            console.print("[red]Forecast failed[/red]")
            return

        pred = forecasts[key]
        current = self.monitor.historial[-1]['price']

        # Track prediction
        if horizon == 5:
            self.tracker.add_prediction(pred)

        # Color based on change
        arrow = "↗" if pred['price_change'] >= 0 else "↘"
        color = "green" if pred['price_change'] >= 0 else "red"
        sign = "+" if pred['price_change'] >= 0 else ""

        # Build table
        table = Table.grid(padding=(0, 2))
        table.add_column(style="dim")
        table.add_column()

        table.add_row("Horizon:", f"[bold]{horizon} min[/bold]")
        table.add_row("Current:", f"${current:.2f}")
        table.add_row("Predicted:", f"[bold]{arrow} ${pred['prediction']:.2f}[/bold]")
        table.add_row("Change:", f"[{color}]{sign}{pred['price_change']:.2f} ({sign}{pred['price_change_pct']:.2f}%)[/{color}]")
        table.add_row("Velocity:", f"{pred['velocity']:.4f} $/min")
        table.add_row("IC 95%:", f"${pred['lower_bound']:.2f} - ${pred['upper_bound']:.2f}")
        table.add_row("Trend:", f"[bold]{pred['trend'].upper()}[/bold]")

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

    def cmd_metrics(self):
        """Show prediction accuracy metrics."""
        # Validate pending predictions
        self.tracker.validate_predictions(self.monitor.historial)

        metrics = self.tracker.get_accuracy_metrics()

        if metrics['validated_predictions'] == 0:
            console.print("[yellow]No validated predictions yet (need 5+ minutes)[/yellow]")
            return

        m = metrics['metrics']

        # Build table
        table = Table.grid(padding=(0, 2))
        table.add_column(style="dim")
        table.add_column()

        table.add_row("Total predictions:", f"{metrics['total_predictions']}")
        table.add_row("Validated:", f"{metrics['validated_predictions']}")
        table.add_row("Directional accuracy:", f"[bold]{m['directional_accuracy']:.1f}%[/bold]")
        table.add_row("MAPE:", f"{m['mape']:.2f}%")
        table.add_row("MAE:", f"${m['mae']:.3f}")
        table.add_row("IC 95% coverage:", f"{m['interval_coverage']:.1f}%")
        table.add_row("Evaluation:", f"[bold]{metrics['summary']}[/bold]")

        console.print(table)

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

    def cmd_help(self):
        """Show help."""
        help_text = """
[bold]Available commands:[/bold]

  [cyan]status[/cyan], [cyan]s[/cyan]          Current price
  [cyan]forecast [1|5|10][/cyan]  Price forecast (default: 5 min)
  [cyan]signal[/cyan], [cyan]sig[/cyan]       Trading signal (BUY/SELL/HOLD)
  [cyan]stats[/cyan]             Statistics (max, min, avg)
  [cyan]metrics[/cyan], [cyan]m[/cyan]        Model accuracy metrics
  [cyan]history[/cyan], [cyan]h[/cyan]        Recent price history
  [cyan]help[/cyan]              Show this help
  [cyan]quit[/cyan], [cyan]q[/cyan]           Exit

[dim]Examples:[/dim]
  ggal> status
  ggal> forecast 10
  ggal> signal
"""
        console.print(help_text)

    def cmd_quit(self):
        """Exit REPL."""
        self.running = False


def main():
    """Entry point."""
    api_key = os.environ.get('FINNHUB_API_KEY')

    if not api_key:
        console.print("[bold red]Error:[/bold red] FINNHUB_API_KEY not set")
        console.print("\n[dim]Get a free API key at: https://finnhub.io[/dim]")
        console.print("[dim]Then run: export FINNHUB_API_KEY='your_key'[/dim]\n")
        sys.exit(1)

    cli = GGALCLI(api_key=api_key)
    cli.start()


if __name__ == '__main__':
    main()
