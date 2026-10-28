from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable


@dataclass(frozen=True)
class Candle:
    session: date
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class Variant:
    id: str
    pattern: str


@dataclass(frozen=True)
class Trade:
    variant_id: str
    entry_date: date
    entry: float
    initial_stop: float
    exit_date: date | None
    exit_price: float | None
    return_pct: float | None
    status: str
    same_bar_ambiguous: bool


def _body_inside(mother: Candle, candle: Candle) -> bool:
    """HZG uses candle bodies, not full high-low ranges."""
    mother_low, mother_high = sorted((mother.open, mother.close))
    candle_low, candle_high = sorted((candle.open, candle.close))
    return candle_low >= mother_low and candle_high <= mother_high


def _range_inside(mother: Candle, candle: Candle) -> bool:
    return candle.high < mother.high and candle.low > mother.low


def _long_body(candle: Candle) -> bool:
    return candle.high > candle.low and abs(candle.close - candle.open) / (candle.high - candle.low) > 0.5


def _green(candle: Candle) -> bool:
    return candle.close > candle.open


def _is_pointy_low(candles: list[Candle], index: int) -> bool:
    return candles[index].low < candles[index - 1].low and candles[index].low < candles[index + 1].low


def _setup(bars: list[Candle], i: int, variant: Variant):
    if variant.pattern == "inside":
        if i + 2 >= len(bars): return None
        a, b, d = bars[i:i+3]
        return (i+2, b.high, b.low) if _green(b) and _range_inside(a, b) and d.high > b.high else None
    if i + 3 >= len(bars): return None
    a, b, c, d = bars[i:i+4]
    valid = _long_body(a) and _body_inside(a, b) and _body_inside(a, c)
    if variant.pattern == "hzg_inside":
        valid = valid and _green(b) and _green(c) and _range_inside(a, b) and _range_inside(a, c)
    return (i+3, c.high, a.low) if valid and d.high > c.high else None


def backtest(candles: Iterable[Candle], variant: Variant, cost_per_side: float = 0.001) -> list[Trade]:
    bars, trades, i = list(candles), [], 20
    while i < len(bars) - 2:
        setup = _setup(bars, i, variant)
        if not setup:
            i += 1; continue
        entry_i, entry, stop = setup; initial_stop = stop
        if bars[entry_i].low <= stop:
            trades.append(Trade(variant.id, bars[entry_i].session, entry, initial_stop, bars[entry_i].session, stop,
                (stop/entry)*(1-cost_per_side)/(1+cost_per_side)-1, "closed", True)); i = entry_i+1; continue
        exit_i = None
        for j in range(entry_i+1, len(bars)):
            if bars[j].low <= stop: exit_i = j; break
            k = j-1
            if k > 0 and _is_pointy_low(bars, k) and bars[k].low > stop: stop = bars[k].low
        if exit_i is None:
            trades.append(Trade(variant.id, bars[entry_i].session, entry, initial_stop, None, None, None, "open", False)); break
        trades.append(Trade(variant.id, bars[entry_i].session, entry, initial_stop, bars[exit_i].session, stop,
            (stop/entry)*(1-cost_per_side)/(1+cost_per_side)-1, "closed", False)); i = exit_i+1
    return trades


def performance(trades: list[Trade], as_of: date, years: int) -> dict:
    cutoff = date(as_of.year - years, as_of.month, as_of.day)
    closed = [t for t in trades if t.status == "closed" and t.entry_date >= cutoff and t.exit_date and t.exit_date <= as_of]
    if not closed:
        return {"trades": 0, "win_rate": None, "mean_return_pct": None, "total_return_pct": None}
    returns = [t.return_pct for t in closed if t.return_pct is not None]
    compounded = 1.0
    for value in returns:
        compounded *= 1 + value
    return {
        "trades": len(returns),
        "win_rate": sum(value > 0 for value in returns) / len(returns),
        "mean_return_pct": sum(returns) / len(returns),
        "total_return_pct": compounded - 1,
    }
