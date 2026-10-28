import sqlite3

conn = sqlite3.connect("/opt/pattern-signal-bot/pattern_signal.sqlite3")
print(conn.execute("SELECT symbol,timeframe,COUNT(*) FROM candles GROUP BY symbol,timeframe ORDER BY symbol,timeframe").fetchall())
print("signals", conn.execute("SELECT COUNT(*) FROM scans").fetchone()[0])
