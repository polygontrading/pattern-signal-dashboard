"""Tests for the two validated changes: gap-aware stop-buy fills and the
box-theory volume confirmation (VRR) on the breakout bar."""
from datetime import date, timedelta

from pattern_signal_bot.engine import Candle, Variant, backtest, _vrr

def c(day, o, h, l, cl, v=100.0):
    return Candle(date(2024, 1, 1) + timedelta(days=day), o, h, l, cl, v)

def _inside_bars(breakout_open, breakout_vol):
    """20 flat bars, then an inside-bar setup whose breakout bar D has the given
    open and volume. VRR window (5 bars before D) averages volume 100."""
    bars = [c(i, 108, 112, 104, 110) for i in range(20)]
    bars.append(c(20, 102, 120, 100, 118))                       # A: wide mother
    bars.append(c(21, 105, 113, 104, 112))                       # B: inside, green
    bars.append(c(22, breakout_open, 118, 105, 117, breakout_vol))  # D: breakout, high > 113
    bars.append(c(23, 108, 110, 100, 101))                       # E: trips the B-low stop
    return bars

def test_vrr_window_is_volume_over_prior_average():
    bars = _inside_bars(110, 300)
    assert _vrr(bars, 22, 5) == 3.0  # 300 / mean(100,100,100,100,100)

def test_raw_inside_fires_regardless_of_volume():
    assert len(backtest(_inside_bars(110, 50), Variant("inside", "inside"))) == 1

def test_vrr_filter_blocks_low_volume_breakout():
    assert backtest(_inside_bars(110, 50), Variant("iv", "inside", min_vrr=2.0)) == []

def test_vrr_filter_allows_volume_surge():
    assert len(backtest(_inside_bars(110, 300), Variant("iv", "inside", min_vrr=2.0))) == 1

def test_gap_up_fills_at_open_not_level():
    # Level is B.high = 113; the breakout bar opens above it at 116.
    trade = backtest(_inside_bars(116, 300), Variant("iv", "inside", min_vrr=2.0))[0]
    assert trade.entry == 116

def test_normal_breakout_fills_at_level():
    # Opens below the level, so the stop-buy fills at the level (113), not the open.
    trade = backtest(_inside_bars(110, 300), Variant("iv", "inside", min_vrr=2.0))[0]
    assert trade.entry == 113
