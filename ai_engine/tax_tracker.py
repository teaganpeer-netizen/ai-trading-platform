"""
Tax obligation tracker for trading activity.
Calculates short-term vs long-term capital gains, generates tax reports.
"""

import logging
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TaxableEvent:
    """Record of a taxable trade event."""
    symbol: str
    entry_date: datetime
    exit_date: datetime
    entry_price: float
    exit_price: float
    quantity: float
    proceeds: float
    cost_basis: float
    gain_loss: float
    holding_period_days: int
    is_long_term: bool  # True if held > 365 days
    tax_year: int


class TaxTracker:
    """Tracks tax obligations and generates reports."""

    LONG_TERM_THRESHOLD_DAYS = 365

    def __init__(self):
        self.events: list[TaxableEvent] = []

    def record_trade(
        self,
        symbol: str,
        entry_date: datetime,
        exit_date: datetime,
        entry_price: float,
        exit_price: float,
        quantity: float,
    ) -> TaxableEvent:
        """Record a closed trade for tax purposes."""
        cost_basis = entry_price * quantity
        proceeds = exit_price * quantity
        gain_loss = proceeds - cost_basis

        holding_period_days = (exit_date - entry_date).days
        is_long_term = holding_period_days > self.LONG_TERM_THRESHOLD_DAYS

        tax_year = exit_date.year

        event = TaxableEvent(
            symbol=symbol,
            entry_date=entry_date,
            exit_date=exit_date,
            entry_price=entry_price,
            exit_price=exit_price,
            quantity=quantity,
            proceeds=round(proceeds, 2),
            cost_basis=round(cost_basis, 2),
            gain_loss=round(gain_loss, 2),
            holding_period_days=holding_period_days,
            is_long_term=is_long_term,
            tax_year=tax_year,
        )

        self.events.append(event)
        logger.info(f"Tax event recorded: {symbol} {'+' if gain_loss > 0 else ''}{gain_loss:.2f}")

        return event

    def get_tax_summary_by_year(self, tax_year: int) -> dict:
        """Get tax summary for a specific year."""
        year_events = [e for e in self.events if e.tax_year == tax_year]

        short_term = [e for e in year_events if not e.is_long_term]
        long_term = [e for e in year_events if e.is_long_term]

        st_gain_loss = sum(e.gain_loss for e in short_term)
        lt_gain_loss = sum(e.gain_loss for e in long_term)
        total_gain_loss = st_gain_loss + lt_gain_loss

        # Tax rates (US 2024 - these should be updated annually)
        # Short-term = ordinary income (varies 10-37%)
        # Long-term = preferential (0%, 15%, 20%)
        st_tax_estimate = st_gain_loss * 0.24  # Assume 24% bracket (mid-range)
        lt_tax_estimate = lt_gain_loss * 0.15  # Assume 15% long-term rate

        return {
            "tax_year": tax_year,
            "short_term_gains": round(st_gain_loss, 2),
            "long_term_gains": round(lt_gain_loss, 2),
            "total_gains": round(total_gain_loss, 2),
            "st_estimated_tax": round(st_tax_estimate, 2),
            "lt_estimated_tax": round(lt_tax_estimate, 2),
            "total_estimated_tax": round(st_tax_estimate + lt_tax_estimate, 2),
            "num_trades": len(year_events),
            "st_trades": len(short_term),
            "lt_trades": len(long_term),
        }

    def get_form_8949_data(self, tax_year: int) -> list[dict]:
        """Generate data for Form 8949 (Sales of Capital Assets)."""
        year_events = [e for e in self.events if e.tax_year == tax_year]

        form_8949_lines = []
        for event in year_events:
            form_8949_lines.append({
                "description": f"{event.quantity:.0f} shares of {event.symbol}",
                "date_acquired": event.entry_date.strftime("%m/%d/%Y"),
                "date_sold": event.exit_date.strftime("%m/%d/%Y"),
                "cost_basis": event.cost_basis,
                "sales_proceeds": event.proceeds,
                "gain_loss": event.gain_loss,
                "long_term": event.is_long_term,
            })

        return form_8949_lines

    def get_realized_gains_summary(self) -> dict:
        """Get summary of all realized gains by year."""
        years = set(e.tax_year for e in self.events)
        summaries = {}

        for year in sorted(years):
            summaries[year] = self.get_tax_summary_by_year(year)

        return summaries

    def get_unrealized_gains(self, current_prices: dict[str, float]) -> dict:
        """Calculate unrealized gains on current open positions."""
        # This would typically be calculated from the portfolio
        # For now, returns structure ready for portfolio integration
        return {
            "positions": [],
            "total_unrealized": 0.0,
            "note": "Populate from portfolio data",
        }

    def estimate_quarterly_tax(self) -> dict:
        """Estimate quarterly estimated tax payments (Form 1040-ES)."""
        # Aggregate all gains YTD
        current_year = datetime.now().year
        ytd_summary = self.get_tax_summary_by_year(current_year)

        # Quarterly payment = 25% of annual estimate (simplified)
        quarterly_st = ytd_summary["st_estimated_tax"] * 0.25
        quarterly_lt = ytd_summary["lt_estimated_tax"] * 0.25

        return {
            "tax_year": current_year,
            "ytd_gains": ytd_summary["total_gains"],
            "estimated_annual_tax": ytd_summary["total_estimated_tax"],
            "quarterly_payment_estimate": round(quarterly_st + quarterly_lt, 2),
            "note": "Consult tax professional — rates vary by bracket",
        }

    def generate_tax_report(self, tax_year: int) -> str:
        """Generate a human-readable tax report."""
        summary = self.get_tax_summary_by_year(tax_year)
        form_8949 = self.get_form_8949_data(tax_year)

        report = f"\n{'='*60}\n"
        report += f"TAX REPORT - {tax_year}\n"
        report += f"{'='*60}\n\n"

        report += f"SHORT-TERM CAPITAL GAINS:\n"
        report += f"  Trades: {summary['st_trades']}\n"
        report += f"  Total Gain/Loss: ${summary['short_term_gains']:+,.2f}\n"
        report += f"  Est. Tax (24% bracket): ${summary['st_estimated_tax']:,.2f}\n\n"

        report += f"LONG-TERM CAPITAL GAINS:\n"
        report += f"  Trades: {summary['lt_trades']}\n"
        report += f"  Total Gain/Loss: ${summary['long_term_gains']:+,.2f}\n"
        report += f"  Est. Tax (15% rate): ${summary['lt_estimated_tax']:,.2f}\n\n"

        report += f"TOTAL:\n"
        report += f"  Total Trades: {summary['num_trades']}\n"
        report += f"  Total Gain/Loss: ${summary['total_gains']:+,.2f}\n"
        report += f"  Estimated Tax Liability: ${summary['total_estimated_tax']:,.2f}\n\n"

        report += f"FORM 8949 DATA:\n"
        report += f"  {len(form_8949)} reportable transactions\n"
        if form_8949:
            for i, line in enumerate(form_8949[:3], 1):  # Show first 3
                report += f"  {i}. {line['description']}: ${line['gain_loss']:+,.2f}\n"
            if len(form_8949) > 3:
                report += f"  ... and {len(form_8949) - 3} more\n"

        report += f"\n{'='*60}\n"
        report += "⚠️  These are estimates. Consult a tax professional.\n"
        report += "Use Form 8949 data to complete Schedule D (Form 1040).\n"
        report += f"{'='*60}\n"

        return report
