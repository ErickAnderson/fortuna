"""Fortuna — SQLite database layer."""

import sqlite3
import os
from contextlib import closing
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "fortuna.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    with closing(get_connection()) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS brokers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                default_fee REAL NOT NULL DEFAULT 0.0
            );

            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL UNIQUE,
                target_weight REAL NOT NULL DEFAULT 0.0
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                position_id INTEGER NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('buy', 'sell')),
                date TEXT NOT NULL,
                qty REAL NOT NULL,
                price REAL NOT NULL,
                fee REAL NOT NULL DEFAULT 0.0,
                broker_id INTEGER,
                FOREIGN KEY (position_id) REFERENCES positions(id),
                FOREIGN KEY (broker_id) REFERENCES brokers(id)
            );

            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                position_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                verdict TEXT,
                price_target REAL,
                summary TEXT,
                full_analysis TEXT,
                accuracy_score REAL,
                accuracy_notes TEXT,
                FOREIGN KEY (position_id) REFERENCES positions(id)
            );
        """)
        conn.commit()


# --- Broker CRUD ---

def get_brokers() -> list[dict]:
    with closing(get_connection()) as conn:
        rows = conn.execute("SELECT * FROM brokers ORDER BY name").fetchall()
        return [dict(r) for r in rows]


def get_broker_by_id(broker_id: int) -> dict | None:
    with closing(get_connection()) as conn:
        row = conn.execute("SELECT * FROM brokers WHERE id = ?", (broker_id,)).fetchone()
        return dict(row) if row else None


def upsert_broker(name: str, default_fee: float) -> int:
    with closing(get_connection()) as conn:
        conn.execute(
            "INSERT INTO brokers (name, default_fee) VALUES (?, ?) "
            "ON CONFLICT(name) DO UPDATE SET default_fee = excluded.default_fee",
            (name, default_fee),
        )
        conn.commit()
        row = conn.execute("SELECT id FROM brokers WHERE name = ?", (name,)).fetchone()
        return row["id"]


# --- Position CRUD ---

def get_positions() -> list[dict]:
    with closing(get_connection()) as conn:
        rows = conn.execute("SELECT * FROM positions ORDER BY ticker").fetchall()
        return [dict(r) for r in rows]


def get_position_by_ticker(ticker: str) -> dict | None:
    with closing(get_connection()) as conn:
        row = conn.execute("SELECT * FROM positions WHERE ticker = ?", (ticker,)).fetchone()
        return dict(row) if row else None


def upsert_position(ticker: str, target_weight: float) -> int:
    with closing(get_connection()) as conn:
        conn.execute(
            "INSERT INTO positions (ticker, target_weight) VALUES (?, ?) "
            "ON CONFLICT(ticker) DO UPDATE SET target_weight = excluded.target_weight",
            (ticker, target_weight),
        )
        conn.commit()
        row = conn.execute("SELECT id FROM positions WHERE ticker = ?", (ticker,)).fetchone()
        return row["id"]


def delete_position(position_id: int):
    with closing(get_connection()) as conn:
        conn.execute("DELETE FROM transactions WHERE position_id = ?", (position_id,))
        conn.execute("DELETE FROM analyses WHERE position_id = ?", (position_id,))
        conn.execute("DELETE FROM positions WHERE id = ?", (position_id,))
        conn.commit()


def update_target_weight(position_id: int, target_weight: float):
    with closing(get_connection()) as conn:
        conn.execute(
            "UPDATE positions SET target_weight = ? WHERE id = ?",
            (target_weight, position_id),
        )
        conn.commit()


# --- Transaction CRUD ---

def get_transactions(position_id: int | None = None) -> list[dict]:
    with closing(get_connection()) as conn:
        if position_id is not None:
            rows = conn.execute(
                """SELECT t.*, p.ticker, b.name as broker_name
                   FROM transactions t
                   JOIN positions p ON t.position_id = p.id
                   LEFT JOIN brokers b ON t.broker_id = b.id
                   WHERE t.position_id = ?
                   ORDER BY t.date DESC""",
                (position_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT t.*, p.ticker, b.name as broker_name
                   FROM transactions t
                   JOIN positions p ON t.position_id = p.id
                   LEFT JOIN brokers b ON t.broker_id = b.id
                   ORDER BY t.date DESC"""
            ).fetchall()
        return [dict(r) for r in rows]


def add_transaction(
    position_id: int,
    txn_type: str,
    txn_date: str,
    qty: float,
    price: float,
    fee: float,
    broker_id: int | None,
) -> int:
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            """INSERT INTO transactions (position_id, type, date, qty, price, fee, broker_id)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (position_id, txn_type, txn_date, qty, price, fee, broker_id),
        )
        conn.commit()
        return cursor.lastrowid


def delete_transaction(txn_id: int):
    with closing(get_connection()) as conn:
        conn.execute("DELETE FROM transactions WHERE id = ?", (txn_id,))
        conn.commit()


def update_transaction(
    txn_id: int,
    txn_date: str,
    qty: float,
    price: float,
    fee: float,
    broker_id: int | None,
):
    with closing(get_connection()) as conn:
        conn.execute(
            """UPDATE transactions SET date = ?, qty = ?, price = ?, fee = ?, broker_id = ?
               WHERE id = ?""",
            (txn_date, qty, price, fee, broker_id, txn_id),
        )
        conn.commit()


# --- Analysis CRUD ---

def get_analyses(position_id: int | None = None) -> list[dict]:
    with closing(get_connection()) as conn:
        if position_id is not None:
            rows = conn.execute(
                """SELECT a.*, p.ticker
                   FROM analyses a
                   JOIN positions p ON a.position_id = p.id
                   WHERE a.position_id = ?
                   ORDER BY a.date DESC""",
                (position_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT a.*, p.ticker
                   FROM analyses a
                   JOIN positions p ON a.position_id = p.id
                   ORDER BY a.date DESC"""
            ).fetchall()
        return [dict(r) for r in rows]


def add_analysis(
    position_id: int,
    verdict: str,
    price_target: float | None,
    summary: str,
    full_analysis: str,
) -> int:
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            """INSERT INTO analyses (position_id, date, verdict, price_target, summary, full_analysis)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (position_id, datetime.now().isoformat(), verdict, price_target, summary, full_analysis),
        )
        conn.commit()
        return cursor.lastrowid


def update_analysis_accuracy(analysis_id: int, score: float, notes: str):
    with closing(get_connection()) as conn:
        conn.execute(
            "UPDATE analyses SET accuracy_score = ?, accuracy_notes = ? WHERE id = ?",
            (score, notes, analysis_id),
        )
        conn.commit()


# --- Portfolio calculations ---

def get_portfolio_summary() -> list[dict]:
    """Calculate full portfolio state from positions + transactions."""
    with closing(get_connection()) as conn:
        positions = conn.execute("SELECT * FROM positions ORDER BY ticker").fetchall()

        results = []
        for pos in positions:
            buys = conn.execute(
                """SELECT COALESCE(SUM(qty), 0) as total_qty,
                          COALESCE(SUM(qty * price), 0) as total_cost,
                          COALESCE(SUM(fee), 0) as total_fees
                   FROM transactions
                   WHERE position_id = ? AND type = 'buy'""",
                (pos["id"],),
            ).fetchone()

            sells = conn.execute(
                """SELECT COALESCE(SUM(qty), 0) as total_qty,
                          COALESCE(SUM(qty * price), 0) as total_proceeds,
                          COALESCE(SUM(fee), 0) as total_fees
                   FROM transactions
                   WHERE position_id = ? AND type = 'sell'""",
                (pos["id"],),
            ).fetchone()

            net_qty = buys["total_qty"] - sells["total_qty"]
            avg_buy_price = buys["total_cost"] / buys["total_qty"] if buys["total_qty"] > 0 else 0.0
            total_cost = avg_buy_price * net_qty
            total_fees = buys["total_fees"] + sells["total_fees"]

            results.append({
                "id": pos["id"],
                "ticker": pos["ticker"],
                "target_weight": pos["target_weight"],
                "qty": net_qty,
                "avg_price": round(avg_buy_price, 4),
                "total_cost": round(total_cost, 2),
                "total_fees": round(total_fees, 2),
            })

        return results
