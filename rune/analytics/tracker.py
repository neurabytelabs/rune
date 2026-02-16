"""
💰 RUNE Cost Tracker — LLM usage cost tracking with SQLite persistence.
"""
import sqlite3
import os
from datetime import datetime, date
from typing import Dict, Optional


# Prices: (input_per_million, output_per_million)
MODEL_PRICES: Dict[str, tuple[float, float]] = {
    # xAI
    "grok-4-1-fast-reasoning": (0.20, 0.50),
    "grok-code-fast-1": (0.20, 1.50),
    "grok-4-fast": (0.20, 0.50),
    "grok-3": (3.00, 15.00),
    "grok-3-mini": (0.30, 0.50),
    # Google
    "gemini-3-pro": (1.25, 10.00),
    "gemini-3-pro-high": (2.50, 20.00),
    "gemini-3-flash": (0.15, 0.60),
    "gemini-3-pro-image": (1.25, 10.00),
    # Anthropic
    "claude-opus-4": (15.00, 75.00),
    "claude-opus-4-6": (15.00, 75.00),
    "claude-opus-4-6-thinking": (15.00, 75.00),
    "claude-sonnet-4-5": (3.00, 15.00),
    "claude-sonnet-4-5-thinking": (3.00, 15.00),
    "claude-haiku-4": (0.80, 4.00),
    # OpenAI
    "gpt-5.2": (5.00, 15.00),
    "gpt-5.2-codex": (5.00, 15.00),
    "gpt-5.2-pro": (20.00, 80.00),
    "gpt-5.1": (3.00, 12.00),
    "gpt-5.1-codex": (3.00, 12.00),
    "gpt-5": (5.00, 15.00),
    "gpt-5-pro": (20.00, 80.00),
    "gpt-4o": (5.00, 15.00),
    "gpt-4o-mini": (0.15, 0.60),
    "o3": (10.00, 40.00),
    "o3-mini": (1.10, 4.40),
    "o4-mini": (1.10, 4.40),
}


def _calc_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost in USD for given token counts."""
    prices = MODEL_PRICES.get(model)
    if not prices:
        # Try prefix match
        for key, val in MODEL_PRICES.items():
            if model.startswith(key) or key.startswith(model):
                prices = val
                break
    if not prices:
        return 0.0
    inp_price, out_price = prices
    return (input_tokens * inp_price / 1_000_000) + (output_tokens * out_price / 1_000_000)


class CostTracker:
    """Track LLM API usage costs with SQLite persistence."""

    def __init__(self, db_path: str = "~/.rune/history.db") -> None:
        self.db_path = os.path.expanduser(db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._create_table()

    def _create_table(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model TEXT NOT NULL,
                input_tokens INTEGER NOT NULL,
                output_tokens INTEGER NOT NULL,
                cost_usd REAL NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        self._conn.commit()

    def track(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Record usage and return calculated cost."""
        cost = _calc_cost(model, input_tokens, output_tokens)
        self._conn.execute(
            "INSERT INTO usage (model, input_tokens, output_tokens, cost_usd, timestamp) VALUES (?, ?, ?, ?, ?)",
            (model, input_tokens, output_tokens, cost, datetime.now().isoformat()),
        )
        self._conn.commit()
        return cost

    def get_total_cost(self) -> float:
        """Total cost across all usage."""
        row = self._conn.execute("SELECT COALESCE(SUM(cost_usd), 0) as total FROM usage").fetchone()
        return row["total"]

    def get_breakdown(self) -> Dict[str, dict]:
        """Cost breakdown by model."""
        rows = self._conn.execute("""
            SELECT model,
                   COUNT(*) as calls,
                   SUM(input_tokens) as total_in,
                   SUM(output_tokens) as total_out,
                   SUM(cost_usd) as total_cost
            FROM usage GROUP BY model ORDER BY total_cost DESC
        """).fetchall()
        return {
            r["model"]: {
                "calls": r["calls"],
                "input_tokens": r["total_in"],
                "output_tokens": r["total_out"],
                "cost_usd": round(r["total_cost"], 6),
            }
            for r in rows
        }

    def get_daily_report(self, target_date: Optional[str] = None) -> str:
        """Generate a daily usage report string."""
        day = target_date or date.today().isoformat()
        rows = self._conn.execute("""
            SELECT model,
                   COUNT(*) as calls,
                   SUM(input_tokens) as total_in,
                   SUM(output_tokens) as total_out,
                   SUM(cost_usd) as total_cost
            FROM usage
            WHERE timestamp LIKE ?
            GROUP BY model ORDER BY total_cost DESC
        """, (f"{day}%",)).fetchall()

        if not rows:
            return f"📊 {day}: No usage recorded."

        lines = [f"📊 Daily Cost Report — {day}", ""]
        lines.append(f"  {'Model':<30} {'Calls':>6} {'In':>10} {'Out':>10} {'Cost':>10}")
        lines.append(f"  {'─'*30} {'─'*6} {'─'*10} {'─'*10} {'─'*10}")

        total_cost = 0.0
        total_in = 0
        total_out = 0
        for r in rows:
            lines.append(
                f"  {r['model']:<30} {r['calls']:>6} {r['total_in']:>10,} {r['total_out']:>10,} ${r['total_cost']:>9.4f}"
            )
            total_cost += r["total_cost"]
            total_in += r["total_in"]
            total_out += r["total_out"]

        lines.append(f"  {'─'*30} {'─'*6} {'─'*10} {'─'*10} {'─'*10}")
        lines.append(f"  {'TOTAL':<30} {'':>6} {total_in:>10,} {total_out:>10,} ${total_cost:>9.4f}")
        return "\n".join(lines)

    def close(self) -> None:
        self._conn.close()
