# Candlestick research rules

Research only; not trading instructions.

## HZG

1. Mother candle A has a body strictly greater than 50% of its full high-low range.
2. The bodies of B and C lie within A's body.
3. D breaks C's high. Entry is C's high and the initial stop is A's low.

## HZG + Inside Bars

Meet every HZG rule, and require B and C to be green, full-range Inside Bars of A:
`B/C high < A high` and `B/C low > A low`.

## Inside Bar

B is green and is a strict full-range Inside Bar of A. It is known only after B closes. A later candle breaking B's high is the entry; B's low is the initial stop.

## Common handling

All systems use completed-candle detection and a confirmed Low Pointy trail. A Low Pointy must be below the adjacent candles' lows. The stop only rises to a higher confirmed Low Pointy. When OHLC data cannot establish whether an entry-bar high happened before an entry-bar low/stop, the test counts the stop conservatively.

The completed research currently compares daily, weekly, and monthly bars, with 0.10% cost on each side. Fixed-horizon comparisons are being rebuilt with the same one-position-per-symbol rules as the Pointy system.
