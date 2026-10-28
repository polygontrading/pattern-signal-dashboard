from datetime import date, timedelta

from pattern_signal_bot.engine import Candle, Variant, backtest


def bar(day, high, low, volume=100):
    return Candle(date(2024, 1, 1) + timedelta(days=day), high - 1, high, low, high - 0.5, volume)


def test_detects_literal_hzg_inside_and_conservative_same_bar_stop():
    bars = [bar(i, 110, 100) for i in range(20)]
    bars += [bar(20, 120, 100), bar(21, 119, 101), bar(22, 118, 102), bar(23, 121, 99)]
    trades = backtest(bars, Variant("base"))
    assert len(trades) == 1
    assert trades[0].same_bar_ambiguous is True
    assert trades[0].initial_stop == 100


def test_rejects_when_inside_bar_range_escapes_mother():
    bars = [bar(i, 110, 100) for i in range(20)]
    bars += [bar(20, 120, 100), bar(21, 121, 101), bar(22, 118, 102), bar(23, 122, 101)]
    assert backtest(bars, Variant("base")) == []
