#!/usr/bin/env python
"""
Interactive CLI for the AI Trading Platform.
Main entry point for running the system.
"""

import sys
import os
from pathlib import Path

# Add project to path
project_root = str(Path(__file__).parent)
sys.path.insert(0, project_root)

import logging
import time
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from config.settings import settings
from data import get_session, BarRepository
from execution import PaperTrader
from backtesting import Backtester, SMACrossoverStrategy, RSIStrategy, MACDStrategy
from ai_engine import AIDecisionMaker, Decision
from ai_engine.mcp_tools import MarketContextProvider
from ai_engine.mcp_enhanced import ComprehensiveMarketContext
from ai_engine.mcp_scanner import MarketScanner
from ai_engine.tax_tracker import TaxTracker
from ai_engine.quant_analyzer import QuantAnalysisEngine
from ai_engine.ml_engine import ContinuousLearningPipeline
from execution.trading_logic import EnhancedTradingLogic

logging.basicConfig(level=logging.INFO)
console = Console()


def print_header():
    """Print application header."""
    console.print(
        Panel(
            "[bold cyan]🤖 AI TRADING PLATFORM[/bold cyan]\n"
            "[dim]Production-Grade Algorithmic Trading System[/dim]",
            expand=False,
            border_style="cyan",
        )
    )


def main_menu():
    """Show main menu."""
    console.print("\n[bold]MAIN MENU[/bold]")
    console.print("1. [green]▶ Run Paper Trading[/green] - AI-powered simulation")
    console.print("2. [yellow]📊 Run Backtester[/yellow] - Test strategies on historical data")
    console.print("3. [cyan]📈 Analyze Single Symbol[/cyan] - Get AI decision & market context")
    console.print("4. [magenta]🔎 Scan Market[/magenta] - Find high-probability trade candidates")
    console.print("5. [blue]⚙️ View Risk Manager[/blue] - Check position sizing & limits")
    console.print("6. [purple]📊 Dashboard[/purple] - Web monitoring interface")
    console.print("7. [green]💰 Tax Tracker[/green] - View tax obligations & reports")
    console.print("8. [cyan]📊 Quant Analysis[/cyan] - Correlation, regime, cointegration")
    console.print("9. [red]❌ Exit[/red]")
    choice = console.input("\n[bold]Select option (1-9):[/bold] ")
    return choice


def run_paper_trading_menu():
    """Menu for paper trading."""
    console.print("\n[bold]PAPER TRADING CONFIG[/bold]")
    iterations = console.input("Number of iterations [default 10]: ") or "10"
    use_ai = console.input("Use AI for decisions? (y/n) [default y]: ").lower() != 'n'

    try:
        iterations = int(iterations)
    except ValueError:
        iterations = 10

    console.print(f"\n[green]Starting paper trading... ({iterations} iterations)[/green]")

    trader = PaperTrader(initial_capital=100_000)
    mcp = MarketContextProvider()

    try:
        for i in range(1, iterations + 1):
            console.print(f"\n[cyan]--- Iteration {i}/{iterations} ---[/cyan]")

            # Show market context every 3 iterations
            if i % 3 == 1 and use_ai:
                overview = mcp.get_market_overview()
                if overview:
                    console.print("[dim]Market Status:[/dim]")
                    for market, data in list(overview.items())[:3]:
                        change = f"[green]+{data['change_pct']:.2f}%[/green]" if data['change_pct'] > 0 else f"[red]{data['change_pct']:.2f}%[/red]"
                        console.print(f"  {market}: {change}")

            # Run iteration
            result = trader.run_iteration(use_ai=use_ai)

            # Show result
            portfolio_val = f"[green]${result['portfolio_value']:,.0f}[/green]"
            daily_pnl = result['daily_pnl']
            pnl_color = "green" if daily_pnl >= 0 else "red"
            pnl_str = f"[{pnl_color}]{daily_pnl:+,.0f}[/{pnl_color}]"

            console.print(
                f"Portfolio: {portfolio_val} | "
                f"Positions: {result['positions_open']} | "
                f"Daily P&L: {pnl_str} | "
                f"Circuit: {result['circuit_state']}"
            )

            time.sleep(0.5)

        # Summary
        summary = trader.get_summary()
        console.print("\n[bold]PAPER TRADING SUMMARY[/bold]")
        table = Table(show_header=False, box=None)
        table.add_row("Initial Capital:", f"${summary['initial_capital']:,.2f}")
        table.add_row("Final Portfolio:", f"[green]${summary['current_capital']:,.2f}[/green]")
        table.add_row("Total Return:", f"[green]{summary['total_return']:+.2f}%[/green]")
        table.add_row("Daily P&L:", f"[green]{summary['daily_pnl']:+,.2f}[/green]")
        table.add_row("Open Positions:", f"{summary['open_positions']}")
        table.add_row("Circuit Breaker:", f"{summary['circuit_state']}")
        console.print(table)

        trader.close()

    except KeyboardInterrupt:
        console.print("\n[yellow]Trading interrupted by user[/yellow]")
        trader.close()


def run_backtester_menu():
    """Menu for backtesting."""
    console.print("\n[bold]BACKTEST CONFIG[/bold]")
    console.print("1. SMA Crossover (20/50)")
    console.print("2. RSI (14, oversold/overbought)")
    console.print("3. MACD (12/26/9)")
    strategy_choice = console.input("Select strategy (1-3) [default 1]: ") or "1"

    symbols_input = console.input("Enter symbols (comma-separated) [default SPY,AAPL]: ") or "SPY,AAPL"
    symbols = [s.strip().upper() for s in symbols_input.split(",")]

    strategies = {
        "1": ("SMA Crossover", SMACrossoverStrategy()),
        "2": ("RSI", RSIStrategy()),
        "3": ("MACD", MACDStrategy()),
    }

    strategy_name, strategy = strategies.get(strategy_choice, ("SMA Crossover", SMACrossoverStrategy()))

    console.print(f"\n[green]Running {strategy_name} backtest on {', '.join(symbols)}...[/green]")

    backtester = Backtester(strategy=strategy, initial_cash=100_000)
    results = backtester.run(symbols=symbols)

    if results:
        stats = results.get("stats", {})
        console.print("\n[bold]BACKTEST RESULTS[/bold]")
        table = Table()
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Strategy", strategy_name)
        table.add_row("Initial Capital", f"${stats.get('initial_capital', 0):,.2f}")
        table.add_row("Final Capital", f"${stats.get('final_value', 0):,.2f}")
        table.add_row("Total Return", f"{stats.get('total_return_pct', 0):+.2f}%")
        table.add_row("Max Drawdown", f"{stats.get('max_drawdown', 0):-.2f}%")
        table.add_row("Trades", f"{stats.get('trades', 0)}")
        table.add_row("Win Rate", f"{stats.get('win_rate', 0):.1f}%")
        table.add_row("Profit Factor", f"{stats.get('profit_factor', 0):.2f}x")

        console.print(table)


def analyze_symbol_menu():
    """Analyze a single symbol."""
    console.print("\n[bold]SYMBOL ANALYSIS[/bold]")
    symbol = console.input("Enter symbol (e.g., AAPL): ").upper()

    console.print(f"\n[cyan]Analyzing {symbol} with enhanced MCPs...[/cyan]")

    try:
        session = get_session()
        bar_repo = BarRepository(session)
        from data import BarProcessor

        # Get data
        bars = bar_repo.get_bars(symbol, limit=200)
        if not bars:
            console.print(f"[red]No data available for {symbol}[/red]")
            session.close()
            return

        df = BarProcessor.to_dataframe(bars)
        df = BarProcessor.enrich_bars(df)
        current_price = df.iloc[-1]["close"]

        # Get comprehensive market context (with enhanced MCPs)
        comprehensive_mcp = ComprehensiveMarketContext()
        enhanced_context = comprehensive_mcp.build_comprehensive_context(symbol)
        caution_flags = comprehensive_mcp.get_caution_flags(symbol)

        # Get AI decision
        ai = AIDecisionMaker(api_key=settings.groq_api_key)
        decision = ai.analyze_symbol(symbol, df, current_price)

        # Get trading logic assessment
        latest = df.iloc[-1]
        quality = EnhancedTradingLogic.rate_entry_quality(
            current_price, latest.get("sma_20"), latest.get("sma_50"), latest.get("rsi_14")
        )

        # Display results
        console.print(f"\n[bold]═══════════════════════════════════[/bold]")
        console.print(f"[bold cyan]{symbol} COMPREHENSIVE ANALYSIS[/bold cyan]")
        console.print(f"[bold]═══════════════════════════════════[/bold]")

        console.print(f"\n[bold]Price:[/bold] ${current_price:.2f}")
        console.print(f"[bold]Action:[/bold] [green]{decision.action}[/green]")
        console.print(f"[bold]Confidence:[/bold] {decision.confidence:.0%}")
        console.print(f"[bold]Entry Quality:[/bold] {quality['rating']}")

        # Show caution flags if any
        if caution_flags:
            console.print(f"\n[yellow][bold]⚠️ CAUTION FLAGS:[/bold]")
            for flag in caution_flags:
                console.print(f"  {flag}")

        console.print(f"\n[bold]AI Reasoning:[/bold]\n{decision.reasoning}")

        if decision.entry_price:
            console.print(f"\n[bold]Trading Levels:[/bold]")
            console.print(f"  Entry: ${decision.entry_price:.2f}")
            console.print(f"  Stop: ${decision.stop_loss:.2f}" if decision.stop_loss else "")
            console.print(f"  Target: ${decision.take_profit:.2f}" if decision.take_profit else "")

        console.print(f"\n[bold]Technical Indicators:[/bold]")
        console.print(f"  SMA20: ${latest.get('sma_20', 0):.2f}")
        console.print(f"  SMA50: ${latest.get('sma_50', 0):.2f}")
        console.print(f"  RSI14: {latest.get('rsi_14', 0):.1f}")
        console.print(f"  MACD: {latest.get('macd', 0):.4f}")

        # Show enhanced market context
        console.print(enhanced_context)

        session.close()

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


def show_risk_manager():
    """Show risk manager settings."""
    from risk import RiskManager

    risk_mgr = RiskManager(
        portfolio_value=100_000,
        risk_per_trade_pct=settings.max_risk_per_trade_pct,
        max_daily_loss_pct=settings.daily_loss_limit_pct,
    )

    console.print("\n[bold]RISK MANAGER SETTINGS[/bold]")
    table = Table()
    table.add_column("Parameter", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Portfolio Value", f"${100_000:,.2f}")
    table.add_row("Risk Per Trade", f"{settings.max_risk_per_trade_pct*100:.1f}%")
    table.add_row("Daily Loss Limit", f"{settings.daily_loss_limit_pct*100:.1f}%")
    table.add_row("Max Exposure", f"{settings.max_portfolio_exposure_pct*100:.0f}%")

    console.print(table)

    # Example position sizing
    console.print("\n[bold]EXAMPLE: Position Sizing[/bold]")
    entry = 100.0
    stop = 95.0
    position = risk_mgr.calculate_position_size(entry, stop)
    risk_amount = position * (entry - stop)

    console.print(f"Entry: ${entry:.2f}")
    console.print(f"Stop: ${stop:.2f}")
    console.print(f"Position Size: {position:.0f} shares")
    console.print(f"Risk Amount: ${risk_amount:,.2f}")


def scan_market_menu():
    """Scan market for trading opportunities."""
    console.print("\n[bold]MARKET SCANNER[/bold]")
    console.print("[dim]Scanning market for high-probability candidates...[/dim]")

    scanner = MarketScanner()
    results = scanner.run_full_scan(top_n=10)

    # Show summary
    console.print(scanner.get_scan_summary(results))

    # Ask if user wants to analyze any
    console.print("\n[bold]Top Opportunities to Analyze:[/bold]")
    top_opps = results.get("top_opportunities", [])

    for i, opp in enumerate(top_opps[:5], 1):
        console.print(f"  {i}. {opp['symbol']} (Score: {opp['score']})")

    choice = console.input("\nEnter symbol to analyze (or press Enter to skip): ").upper()

    if choice and choice in [opp["symbol"] for opp in top_opps]:
        # Analyze the selected symbol
        try:
            session = get_session()
            bar_repo = BarRepository(session)
            from data import BarProcessor

            bars = bar_repo.get_bars(choice, limit=200)
            if not bars:
                console.print(f"[red]No data available for {choice}[/red]")
                session.close()
                return

            df = BarProcessor.to_dataframe(bars)
            df = BarProcessor.enrich_bars(df)
            current_price = df.iloc[-1]["close"]

            # Get comprehensive context
            comprehensive_mcp = ComprehensiveMarketContext()
            enhanced_context = comprehensive_mcp.build_comprehensive_context(choice)
            caution_flags = comprehensive_mcp.get_caution_flags(choice)

            # Get AI decision
            ai = AIDecisionMaker(api_key=settings.groq_api_key)
            decision = ai.analyze_symbol(choice, df, current_price)

            # Display
            console.print(f"\n[bold cyan]═══════════════════════════════════[/bold cyan]")
            console.print(f"[bold cyan]{choice} - SCANNER DISCOVERY[/bold cyan]")
            console.print(f"[bold cyan]═══════════════════════════════════[/bold cyan]")

            console.print(f"\n[bold]Price:[/bold] ${current_price:.2f}")
            console.print(f"[bold]Action:[/bold] [green]{decision.action}[/green]")
            console.print(f"[bold]Confidence:[/bold] {decision.confidence:.0%}")

            if caution_flags:
                console.print(f"\n[yellow]⚠️ CAUTION FLAGS:[/yellow]")
                for flag in caution_flags:
                    console.print(f"  {flag}")

            console.print(f"\n[bold]AI Reasoning:[/bold]\n{decision.reasoning}")

            if decision.entry_price:
                console.print(f"\n[bold]Trading Levels:[/bold]")
                console.print(f"  Entry: ${decision.entry_price:.2f}")
                if decision.stop_loss:
                    console.print(f"  Stop: ${decision.stop_loss:.2f}")
                if decision.take_profit:
                    console.print(f"  Target: ${decision.take_profit:.2f}")

            session.close()

        except Exception as e:
            console.print(f"[red]Error analyzing {choice}: {e}[/red]")


def show_dashboard_info():
    """Show dashboard info."""
    console.print("\n[bold]WEB DASHBOARD[/bold]")
    console.print("The web dashboard is available at: [cyan]http://localhost:5000[/cyan]")
    console.print("\nTo start the dashboard:")
    console.print("  [yellow]bash scripts/run_dashboard.sh[/yellow]")
    console.print("\nFeatures:")
    console.print("  • Real-time portfolio monitoring")
    console.print("  • Open positions & P&L tracking")
    console.print("  • Trade history & performance metrics")
    console.print("  • 5-second auto-refresh")


def show_tax_tracker_menu():
    """Show tax tracking menu."""
    console.print("\n[bold]TAX TRACKING[/bold]")
    tax_tracker = TaxTracker()

    console.print("\n1. [green]Record a Trade[/green] - Log closed position for taxes")
    console.print("2. [yellow]View Tax Summary[/yellow] - See gains by year & type")
    console.print("3. [cyan]Form 8949 Data[/cyan] - Generate reportable transactions")
    console.print("4. [blue]Quarterly Estimate[/blue] - Calculate estimated payments")
    console.print("5. [magenta]Full Report[/magenta] - Generate complete tax report")
    console.print("6. [red]Back[/red]")

    choice = console.input("\n[bold]Select option (1-6):[/bold] ")

    if choice == "1":
        try:
            symbol = console.input("Symbol: ").upper()
            entry_date_str = console.input("Entry date (YYYY-MM-DD): ")
            exit_date_str = console.input("Exit date (YYYY-MM-DD): ")
            entry_price = float(console.input("Entry price: "))
            exit_price = float(console.input("Exit price: "))
            quantity = float(console.input("Quantity: "))

            from datetime import datetime
            entry_date = datetime.strptime(entry_date_str, "%Y-%m-%d")
            exit_date = datetime.strptime(exit_date_str, "%Y-%m-%d")

            event = tax_tracker.record_trade(symbol, entry_date, exit_date, entry_price, exit_price, quantity)
            console.print(f"\n[green]✓ Trade recorded: {symbol} {'+' if event.gain_loss > 0 else ''}{event.gain_loss:.2f}[/green]")
            console.print(f"  Holding period: {event.holding_period_days} days")
            console.print(f"  Classification: {'Long-term' if event.is_long_term else 'Short-term'} capital gain/loss")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

    elif choice == "2":
        year = int(console.input("Tax year: ") or str(datetime.now().year))
        summary = tax_tracker.get_tax_summary_by_year(year)
        console.print(f"\n[bold]TAX SUMMARY - {year}[/bold]")
        table = Table()
        table.add_column("Type", style="cyan")
        table.add_column("Amount", style="green")
        table.add_row("Short-term gains", f"${summary['short_term_gains']:+,.2f}")
        table.add_row("Long-term gains", f"${summary['long_term_gains']:+,.2f}")
        table.add_row("Total gains", f"${summary['total_gains']:+,.2f}")
        table.add_row("ST Est. Tax (24%)", f"${summary['st_estimated_tax']:,.2f}")
        table.add_row("LT Est. Tax (15%)", f"${summary['lt_estimated_tax']:,.2f}")
        table.add_row("Total Est. Tax", f"${summary['total_estimated_tax']:,.2f}")
        table.add_row("Trades", str(summary['num_trades']))
        console.print(table)

    elif choice == "3":
        year = int(console.input("Tax year: ") or str(datetime.now().year))
        form_8949 = tax_tracker.get_form_8949_data(year)
        console.print(f"\n[bold]FORM 8949 DATA - {year}[/bold]")
        if form_8949:
            table = Table()
            table.add_column("Description", style="cyan")
            table.add_column("Acquired", style="dim")
            table.add_column("Sold", style="dim")
            table.add_column("Gain/Loss", style="green")
            for line in form_8949:
                gl_color = "green" if line["gain_loss"] > 0 else "red"
                table.add_row(
                    line["description"],
                    line["date_acquired"],
                    line["date_sold"],
                    f"[{gl_color}]${line['gain_loss']:+,.2f}[/{gl_color}]"
                )
            console.print(table)
        else:
            console.print("[dim]No transactions for this year[/dim]")

    elif choice == "4":
        quarterly = tax_tracker.estimate_quarterly_tax()
        console.print(f"\n[bold]QUARTERLY ESTIMATED PAYMENTS[/bold]")
        table = Table(show_header=False, box=None)
        table.add_row("YTD Gains:", f"${quarterly['ytd_gains']:+,.2f}")
        table.add_row("Est. Annual Tax:", f"${quarterly['estimated_annual_tax']:,.2f}")
        table.add_row("Quarterly Payment (÷4):", f"${quarterly['quarterly_payment_estimate']:,.2f}")
        console.print(table)

    elif choice == "5":
        year = int(console.input("Tax year: ") or str(datetime.now().year))
        report = tax_tracker.generate_tax_report(year)
        console.print(report)


def show_quant_analysis_menu():
    """Show quantitative analysis menu."""
    console.print("\n[bold]QUANTITATIVE ANALYSIS[/bold]")
    console.print("[dim]Advanced statistical analysis of trading positions[/dim]\n")

    quant = QuantAnalysisEngine()

    console.print("1. [green]Analyze Symbol[/green] - Regime, correlations, cointegration")
    console.print("2. [yellow]Portfolio Risk[/yellow] - Correlation-based risk assessment")
    console.print("3. [cyan]Regime Detection[/cyan] - Current market state & changes")
    console.print("4. [blue]Cointegration Scanner[/blue] - Find mean-reverting pairs")
    console.print("5. [red]Back[/red]")

    choice = console.input("\n[bold]Select option (1-5):[/bold] ")

    if choice == "1":
        symbol = console.input("Enter symbol (e.g., AAPL): ").upper()
        console.print(f"\n[cyan]Analyzing {symbol}...[/cyan]")

        try:
            session = get_session()
            bar_repo = BarRepository(session)
            from data import BarProcessor

            bars = bar_repo.get_bars(symbol, limit=200)
            if not bars:
                console.print(f"[red]No data for {symbol}[/red]")
                session.close()
                return

            df = BarProcessor.to_dataframe(bars)
            prices = df["close"].tolist()

            analysis = quant.analyze_symbol(symbol, {symbol: prices}, prices[-1])
            report = quant.get_analysis_report(analysis)
            console.print(report)

            session.close()
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

    elif choice == "2":
        console.print("\n[cyan]Portfolio Risk Assessment (placeholder - requires position data)[/cyan]")
        positions = {"AAPL": 5000, "MSFT": 3000, "TSLA": 2000}
        risk = CorrelationAnalyzer.get_portfolio_correlation_risk(positions)
        table = Table(show_header=False, box=None)
        table.add_row("Risk Level:", f"[yellow]{risk['risk_level'].upper()}[/yellow]")
        table.add_row("Concentration:", f"{risk['concentration_ratio']:.1%}")
        table.add_row("Recommendation:", risk['recommendation'])
        console.print(table)

    elif choice == "3":
        symbol = console.input("Enter symbol (e.g., SPY): ").upper()
        try:
            session = get_session()
            bar_repo = BarRepository(session)
            from data import BarProcessor

            bars = bar_repo.get_bars(symbol, limit=200)
            if bars:
                df = BarProcessor.to_dataframe(bars)
                prices = df["close"].tolist()
                regime = RegimeDetector.detect_regime(prices)
                regime_change = RegimeDetector.detect_regime_change(prices)

                console.print(f"\n[bold]{symbol} Market Regime[/bold]")
                console.print(f"State: {regime['regime'].upper()}")
                console.print(f"Confidence: {regime['confidence']:.0%}")
                console.print(f"Volatility (annualized): {regime['volatility_annual']:.1%}")
                if regime_change['regime_change']:
                    console.print(f"\n[yellow]⚠️ Regime Change: {regime_change['previous_regime']} → {regime_change['current_regime']}[/yellow]")

            session.close()
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


# Import needed for quant menu
from ai_engine.quant_analyzer import CorrelationAnalyzer, RegimeDetector


def main():
    """Main CLI loop."""
    print_header()

    while True:
        choice = main_menu()

        if choice == "1":
            run_paper_trading_menu()
        elif choice == "2":
            run_backtester_menu()
        elif choice == "3":
            analyze_symbol_menu()
        elif choice == "4":
            scan_market_menu()
        elif choice == "5":
            show_risk_manager()
        elif choice == "6":
            show_dashboard_info()
        elif choice == "7":
            show_tax_tracker_menu()
        elif choice == "8":
            show_quant_analysis_menu()
        elif choice == "9":
            console.print("[yellow]Goodbye![/yellow]")
            break
        else:
            console.print("[red]Invalid option[/red]")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Exiting...[/yellow]")
        sys.exit(0)
