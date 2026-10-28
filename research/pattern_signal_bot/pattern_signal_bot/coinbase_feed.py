"""Unauthenticated Coinbase Exchange spot-candle feed for research only."""
from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .engine import Candle


BASE_URL = "https://api.exchange.coinbase.com/products"
DAILY_SECONDS = 86_400
MAX_BUCKETS = 300


def _utc(day: date) -> str:
    return datetime.combine(day, time.min, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def fetch_daily(product: str, start: date, end: date) -> list[Candle]:
    """Fetch closed UTC daily BTC/crypto candles, paginating Coinbase's 300-bar cap."""
    out: dict[date, Candle] = {}
    cursor = start
    while cursor < end:
        chunk_end = min(cursor + timedelta(days=MAX_BUCKETS), end)
        query = urlencode({"granularity": DAILY_SECONDS, "start": _utc(cursor), "end": _utc(chunk_end)})
        request = Request(f"{BASE_URL}/{product}/candles?{query}", headers={"User-Agent": "pattern-signal-research/1.0"})
        with urlopen(request, timeout=30) as response:  # nosec B310: fixed HTTPS Coinbase endpoint
            rows = json.loads(response.read().decode("utf-8"))
        for timestamp, low, high, open_, close, volume in rows:
            session = datetime.fromtimestamp(timestamp, tz=timezone.utc).date()
            if session < end:
                out[session] = Candle(session, float(open_), float(high), float(low), float(close), float(volume))
        cursor = chunk_end
    return [out[key] for key in sorted(out)]


def weekly_from_daily(bars: list[Candle], completed_before: date) -> list[Candle]:
    groups: dict[date, list[Candle]] = {}
    for bar in bars:
        week = bar.session - timedelta(days=bar.session.weekday())
        groups.setdefault(week, []).append(bar)
    complete = []
    for week, values in sorted(groups.items()):
        if week + timedelta(days=7) > completed_before:
            continue
        complete.append(Candle(week, values[0].open, max(x.high for x in values), min(x.low for x in values),
                               values[-1].close, sum(x.volume for x in values)))
    return complete


def monthly_from_daily(bars: list[Candle], completed_before: date) -> list[Candle]:
    groups: dict[tuple[int, int], list[Candle]] = {}
    for bar in bars: groups.setdefault((bar.session.year, bar.session.month), []).append(bar)
    return [Candle(values[0].session, values[0].open, max(x.high for x in values), min(x.low for x in values), values[-1].close, sum(x.volume for x in values))
            for (_, month), values in sorted(groups.items()) if not (values[0].session.year == completed_before.year and month == completed_before.month)]
