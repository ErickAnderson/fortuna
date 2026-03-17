"""Fortuna — Seed database with sample portfolio data."""

import database as db
from contextlib import closing


def seed():
    """Seed the database with sample portfolio data for demo purposes."""
    db.init_db()

    # Check if already seeded
    with closing(db.get_connection()) as conn:
        count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    if count > 0:
        print("Database already seeded. Skipping.")
        return

    # --- Brokers ---
    broker_id = db.upsert_broker("SampleBroker", 9.50)

    # --- Positions with target weights ---
    positions = {
        "BHP": 30.0,
        "CBA": 25.0,
        "CSL": 25.0,
        "WDS": 20.0,
    }
    position_ids = {}
    for ticker, weight in positions.items():
        position_ids[ticker] = db.upsert_position(ticker, weight)

    # --- Sample transactions ---
    transactions = [
        # (date, ticker, type, qty, price, fee, broker_id)
        ("2026-01-10", "BHP", "buy", 20, 45.50, 9.50, broker_id),
        ("2026-01-15", "CBA", "buy", 10, 120.00, 9.50, broker_id),
        ("2026-02-01", "CSL", "buy", 5, 280.00, 9.50, broker_id),
        ("2026-02-10", "BHP", "buy", 15, 44.80, 9.50, broker_id),
        ("2026-02-20", "WDS", "buy", 50, 18.25, 9.50, broker_id),
        ("2026-03-01", "CBA", "buy", 8, 122.50, 9.50, broker_id),
    ]

    for txn_date, ticker, txn_type, qty, price, fee, broker_id in transactions:
        db.add_transaction(
            position_id=position_ids[ticker],
            txn_type=txn_type,
            txn_date=txn_date,
            qty=qty,
            price=price,
            fee=fee,
            broker_id=broker_id,
        )

    print("Database seeded successfully!")
    print(f"  - {len(positions)} positions")
    print(f"  - {len(transactions)} transactions")
    print(f"  - 1 broker (SampleBroker)")

    # Verify
    summary = db.get_portfolio_summary()
    print("\nPortfolio summary:")
    for pos in summary:
        print(f"  {pos['ticker']:8s} | qty: {pos['qty']:>6.0f} | avg: ${pos['avg_price']:>8.4f} | cost: ${pos['total_cost']:>10.2f}")


if __name__ == "__main__":
    seed()
