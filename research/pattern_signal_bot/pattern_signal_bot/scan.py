from __future__ import annotations

import argparse
import json
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .engine import Variant, backtest, performance, _body_inside, _green, _long_body, _range_inside
from .coinbase_feed import fetch_daily as fetch_coinbase_daily, weekly_from_daily, monthly_from_daily
from .futu_feed import fetch
from .store import connect, load_candles, record_scan, upsert_candles


ROOT = Path(__file__).resolve().parents[1]
LOG = logging.getLogger(__name__)


def latest_setup(bars, variant):
    if variant.pattern == "inside":
        if len(bars) < 23: return None
        a, b, d = bars[-3:]
        return (d, b.high, b.low) if _green(b) and _range_inside(a, b) and d.high > b.high else None
    if len(bars) < 24: return None
    a, b, c, d = bars[-4:]
    valid = _long_body(a) and _body_inside(a, b) and _body_inside(a, c)
    if variant.pattern == "hzg_inside":
        valid = valid and _green(b) and _green(c) and _range_inside(a, b) and _range_inside(a, c)
    return (d, c.high, a.low) if valid and d.high > c.high else None


def qualifies(metrics: dict, minimum: int) -> bool:
    """Require a meaningful long sample, a positive five-year check, and no
    negative one-year evidence when that short sample exists."""
    long, medium, short = metrics["10"], metrics["5"], metrics["1"]
    if long["trades"] < minimum or long["mean_return_pct"] is None or long["mean_return_pct"] <= 0:
        return False
    if medium["trades"] < max(5, minimum // 2) or medium["mean_return_pct"] is None or medium["mean_return_pct"] <= 0:
        return False
    return short["trades"] == 0 or (short["mean_return_pct"] is not None and short["mean_return_pct"] >= 0)


def run(bootstrap: bool, only_symbols: set[str] | None = None) -> list[dict]:
    config = json.loads((ROOT / "config.json").read_text())
    db = connect(ROOT / config["database"])
    today = date.today()
    start = date(today.year - config["history_years"], today.month, today.day) if bootstrap else today - timedelta(days=45)
    variants = [Variant(**x) for x in config["variants"]]
    results = []
    assets = [(symbol, "futu") for symbol in config["symbols"]]
    assets.extend((symbol, "coinbase") for symbol in config.get("crypto_symbols", []))
    if only_symbols:
        assets = [asset for asset in assets if asset[0] in only_symbols]
    for symbol, provider in assets:
        try:
            crypto_daily = None
            if provider == "coinbase":
                # Fetch daily once; weekly bars are deterministically aggregated from it.
                crypto_start = start - timedelta(days=7) if "week" in config["timeframes"] else start
                crypto_daily = fetch_coinbase_daily(symbol, crypto_start, today)
            for timeframe in config["timeframes"]:
                if provider == "coinbase":
                    bars = crypto_daily if timeframe == "day" else (weekly_from_daily(crypto_daily, today) if timeframe == "week" else monthly_from_daily(crypto_daily, today))
                else:
                    bars = fetch(symbol, timeframe, start, today,
                                 host=config["provider"]["host"], port=config["provider"]["port"])
                    if timeframe == "week":
                        week_start = today - timedelta(days=today.weekday())
                        bars = [bar for bar in bars if bar.session < week_start]
                    elif timeframe == "month":
                        bars = [bar for bar in bars if (bar.session.year, bar.session.month) < (today.year, today.month)]
                upsert_candles(db, symbol, timeframe, bars, provider)
                if timeframe == "week":
                    week_start = today - timedelta(days=today.weekday())
                    db.execute("DELETE FROM candles WHERE symbol=? AND timeframe=? AND session>=?", (symbol, timeframe, week_start.isoformat()))
                    db.commit()
                elif timeframe == "month":
                    month_start = date(today.year, today.month, 1)
                    db.execute("DELETE FROM candles WHERE symbol=? AND timeframe=? AND session>=?", (symbol, timeframe, month_start.isoformat()))
                    db.commit()
                history = load_candles(db, symbol, timeframe)
                candidates = []
                for variant in variants:
                    setup = latest_setup(history, variant)
                    if not setup:
                        continue
                    d, entry, stop = setup
                    prior = [x for x in history if x.session < d.session]
                    metrics = {str(year): performance(backtest(prior, variant), d.session, year) for year in (10, 5, 1)}
                    candidates.append((variant, d, entry, stop, metrics))
                eligible = [x for x in candidates if qualifies(x[4], config["minimum_historical_trades"])]
                winner = max(eligible, key=lambda x: (x[4]["10"]["mean_return_pct"], x[4]["5"]["mean_return_pct"], x[4]["10"]["trades"]), default=None)
                for variant, d, entry, stop, metrics in candidates:
                    qualified = winner is not None and variant.id == winner[0].id
                    payload = {"scanned_at": datetime.now(timezone.utc).isoformat(), "symbol": symbol, "timeframe": timeframe,
                               "variant_id": variant.id, "setup_date": d.session.isoformat(), "entry": entry, "initial_stop": stop,
                               "qualified": qualified, "metrics": metrics, "provider": provider}
                    record_scan(db, payload)
                    results.append(payload)
        except Exception as error:
            LOG.exception("Skipping %s after a provider error: %s", symbol, error)
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--bootstrap", action="store_true")
    parser.add_argument("--only-symbol", action="append", help="Refresh one configured symbol without touching the rest")
    args = parser.parse_args()
    print(json.dumps(run(args.bootstrap, set(args.only_symbol or [])), indent=2))
