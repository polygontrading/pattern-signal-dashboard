# Pattern Signal Bot

Read-only research scanner for the HZG + Inside Bar strategy.

It fetches completed daily and weekly US-stock candles from the existing Futu OpenD gateway, detects approved variants, evaluates the specified pointy-low stop rule, stores an immutable signal audit trail in SQLite, and exposes a small JSON API for a future static dashboard.

No order-routing, broker-trading, or alerting code is included.

## Initial run

```powershell
python -m pattern_signal_bot.scan --bootstrap
```

This performs the initial ten-year candle load for each configured symbol. Later scheduled runs omit `--bootstrap` and update only recent history.

## Local API

```powershell
python -m pattern_signal_bot.server
```

Endpoints: `/api/health`, `/api/signals`, `/api/symbols`.
