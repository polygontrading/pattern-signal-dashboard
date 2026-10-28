from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .engine import Candle


SCHEMA = """
CREATE TABLE IF NOT EXISTS candles (
 symbol TEXT NOT NULL, timeframe TEXT NOT NULL, session TEXT NOT NULL,
 open REAL NOT NULL, high REAL NOT NULL, low REAL NOT NULL, close REAL NOT NULL, volume REAL NOT NULL,
 provider TEXT NOT NULL, PRIMARY KEY(symbol, timeframe, session)
);
CREATE TABLE IF NOT EXISTS scans (
 id INTEGER PRIMARY KEY, scanned_at TEXT NOT NULL, symbol TEXT NOT NULL, timeframe TEXT NOT NULL,
 variant_id TEXT NOT NULL, setup_date TEXT NOT NULL, entry REAL NOT NULL, initial_stop REAL NOT NULL,
 qualified INTEGER NOT NULL, metrics_json TEXT NOT NULL, provider TEXT NOT NULL,
 UNIQUE(symbol, timeframe, variant_id, setup_date)
);
"""


def connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def upsert_candles(conn: sqlite3.Connection, symbol: str, timeframe: str, bars: list[Candle], provider: str) -> None:
    conn.executemany(
        "INSERT INTO candles VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(symbol,timeframe,session) DO UPDATE SET open=excluded.open,high=excluded.high,low=excluded.low,close=excluded.close,volume=excluded.volume,provider=excluded.provider",
        [(symbol, timeframe, b.session.isoformat(), b.open, b.high, b.low, b.close, b.volume, provider) for b in bars],
    )
    conn.commit()


def load_candles(conn: sqlite3.Connection, symbol: str, timeframe: str) -> list[Candle]:
    rows = conn.execute("SELECT * FROM candles WHERE symbol=? AND timeframe=? ORDER BY session", (symbol, timeframe)).fetchall()
    from datetime import date
    return [Candle(date.fromisoformat(r["session"]), r["open"], r["high"], r["low"], r["close"], r["volume"]) for r in rows]


def record_scan(conn: sqlite3.Connection, payload: dict) -> None:
    conn.execute(
        "INSERT INTO scans(scanned_at,symbol,timeframe,variant_id,setup_date,entry,initial_stop,qualified,metrics_json,provider) VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(symbol,timeframe,variant_id,setup_date) DO NOTHING",
        (payload["scanned_at"], payload["symbol"], payload["timeframe"], payload["variant_id"], payload["setup_date"], payload["entry"], payload["initial_stop"], int(payload["qualified"]), json.dumps(payload["metrics"]), payload["provider"]),
    )
    conn.commit()
