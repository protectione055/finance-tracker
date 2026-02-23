#!/usr/bin/env python3
"""Generate spending summary from finance-tracker SQLite DB."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate spending summary from finance-tracker database.")
    parser.add_argument("--db", default="./data/finance.db", help="Path to SQLite database")
    parser.add_argument("--days", type=int, default=30, help="Lookback days")
    parser.add_argument("--top", type=int, default=10, help="Top N merchants")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.days <= 0 or args.top <= 0:
        raise SystemExit("--days and --top must be > 0")

    db = Path(args.db)
    if not db.exists():
        raise SystemExit(f"DB not found: {db}")

    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row

    totals = conn.execute(
        """
        SELECT
          COALESCE(SUM(CASE WHEN transaction_type IN ('consumption','transfer_out','fee') THEN amount ELSE 0 END), 0) AS expense,
          COALESCE(SUM(CASE WHEN transaction_type IN ('income','transfer_in','refund','interest','dividend') THEN amount ELSE 0 END), 0) AS income,
          COUNT(*) AS tx_count
        FROM transactions
        WHERE transaction_time >= datetime('now', ?)
        """,
        (f"-{args.days} days",),
    ).fetchone()

    top_rows = conn.execute(
        """
        SELECT COALESCE(NULLIF(counterparty_name, ''), 'UNKNOWN') AS merchant,
               COUNT(*) AS tx_count,
               ROUND(SUM(amount), 2) AS total_amount
        FROM transactions
        WHERE transaction_time >= datetime('now', ?)
          AND transaction_type IN ('consumption','transfer_out','fee')
        GROUP BY merchant
        ORDER BY total_amount DESC
        LIMIT ?
        """,
        (f"-{args.days} days", args.top),
    ).fetchall()

    print(f"[Spending Report] Last {args.days} days")
    print("=" * 48)
    print(f"Transactions: {int(totals['tx_count'])}")
    print(f"Total Expense: {float(totals['expense']):.2f}")
    print(f"Total Income:  {float(totals['income']):.2f}")
    print(f"Net Cashflow:  {float(totals['income']) - float(totals['expense']):.2f}")
    print("\nTop Merchants by Expense")
    print("-" * 48)
    if not top_rows:
        print("No expense transactions found.")
    else:
        for i, row in enumerate(top_rows, start=1):
            print(f"{i:>2}. {row['merchant']:<20} {row['total_amount']:>10.2f} ({row['tx_count']} tx)")

    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
