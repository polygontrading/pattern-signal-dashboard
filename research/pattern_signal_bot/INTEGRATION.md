# Pattern Signal Bot — Box Theory integration

This patch extends the existing `pattern_signal_bot` so the volume-confirmed
"combined method" and box theory run on the **same** dashboard, rather than as a
separate bot. It implements the two findings validated this cycle:

1. **Gap-aware entry fill** — the backtest filled at the exact breakout level, which
   overstates the edge because breakout bars often gap above it. A stop-buy fills at
   the level *or at the open on a gap-up, never better*. This roughly halves the raw
   patterns' apparent edge (correctly).
2. **Volume confirmation (VRR)** — requiring a volume surge on the breakout bar
   (`volume ≥ k × SMA(volume, period)`) is the single biggest quality lever. It turns
   the weak inside-bar breakout into a real edge and is out-of-sample robust.

## What validation showed (US, gap-aware, 0.10%/side)

Per-trade edge in R (reward/initial-risk):

| Variant          | all-era | TRAIN ≤2019 | TEST 2020–22 | HOLDOUT 2023+ |
|------------------|--------:|------------:|-------------:|--------------:|
| inside (raw)     |   0.03  |      —      |      —       |      —        |
| hzg (raw)        |   0.11  |      —      |      —       |      —        |
| hzg_inside (raw) |   0.16  |      —      |      —       |      —        |
| inside_vrr15     |   0.44  |    0.47     |    0.69      |    0.36       |
| inside_vrr20     |   0.83  |    1.01     |    0.43      |    0.66       |
| hzg_vrr15        |   0.31  |    0.30     |    0.19      |    0.72       |
| hzg_vrr20        |   0.24  |    0.29     |    0.22      |    0.28       |

Robust threshold zone is **VRR 1.5–2.0**. VRR ≥ 2.5 is positive in-sample but goes
**negative in the 2023+ holdout** — do not raise the threshold above 2.0.
`verify_local.py` reproduces these numbers against the patched engine.

> Validation used volume recovered from OBV (`vol = |ΔOBV|`) because the TradingView
> CSV exports ship an empty Volume column. In production the Futu / Coinbase feeds
> already carry real volume, so the live scanner computes VRR directly — no change
> needed.

## Files in this patch

Drop these into `research/pattern_signal_bot/` (the inner package is
`research/pattern_signal_bot/pattern_signal_bot/`):

| File | Change |
|------|--------|
| `pattern_signal_bot/engine.py`          | **Changed.** `Variant` gains `min_vrr` (default 0 = off) and `vrr_period` (default 5). New `_vrr()`. `_setup()` enforces the VRR gate on the breakout bar. `backtest()` fills gap-aware (`max(level, open)`). `pattern` now defaults to `"base"` so `Variant("id")` still constructs. |
| `pattern_signal_bot/scan.py`            | **Changed.** `latest_setup()` now delegates to the engine's `_setup()`, so the live screen and the backtest apply byte-identical rules (incl. VRR). Nothing else changed. |
| `pattern_signal_bot/publish_snapshot.py`| **Changed (one line).** Publishes qualified scans whose variant is in `config.variants` **or** `config.webhook_variants`, so box-theory arrows reach the dashboard. |
| `pattern_signal_bot/webhook.py`         | **New.** HTTP receiver for TradingView box-theory arrow alerts → signal rows (`variant_id = box_theory_arrow`). Pure `build_signal()` is unit-tested. |
| `config.json`                           | **Changed.** Adds the four VRR variants, `webhook_variants`, and `box_theory_reference_metrics`. Symbol universe unchanged. |
| `pattern_signal_bot/store.py`, `__init__.py` | Unchanged from upstream; included only so the package is complete/testable. |
| `tests/test_combined.py`                | **New.** 6 tests: VRR window math, VRR gate blocks/allows, gap-up fills at open, normal fills at level. |

## Deploy

```bash
# on the Hostinger box, in research/pattern_signal_bot/
python -m pattern_signal_bot.scan --bootstrap     # one-time: build 10y history + metrics
python -m pattern_signal_bot.scan                 # daily (systemd timer already exists)
python -m pattern_signal_bot.publish_snapshot     # push snapshot to the Pages repo
```

The existing `deploy/pattern-signal-scan.timer` keeps running the daily scan; no
systemd change is needed for the candlestick side.

### Box theory arrow webhook

```bash
export BOX_THEORY_WEBHOOK_SECRET=<shared-secret>
python -m pattern_signal_bot.webhook              # listens on 127.0.0.1:8788
```

Put it behind the same reverse proxy as the API, add a systemd unit modelled on
`deploy/pattern-signal-api.service`, then point a TradingView alert at
`https://<api-origin>/webhook` (see `TRADINGVIEW_SYMBOLS.md` for the alert body).
Each arrow becomes a `box_theory_arrow` row the next time `publish_snapshot` runs.

## Decisions to make

- **Trim the raw variants (recommended).** `inside` (0.03 R) and `hzg` (0.11 R) are
  essentially noise once filled honestly. The scanner's winner-picker prefers the VRR
  variants *when a volume surge is present*, but with no surge it can still surface a
  weak raw setup (e.g. a 0.02% 10-year mean). To only ever show volume-confirmed or
  strict-structural setups, delete `{"id":"inside",...}` and `{"id":"hzg",...}` from
  `config.json`, keeping `hzg_inside` (0.16 R stands alone) and the four VRR variants.
- **`box_theory_reference_metrics`** is `null`, so arrow rows show their live trigger
  and "Insufficient data" in the research columns (honest — the arrow is a live
  signal; its backtest lives in the box-theory project). To fill the 10Y column, set
  it to `{"10": {"trades": N, "win_rate": W, "mean_return_pct": R}, "5": {"trades":0}, "1": {"trades":0}}`
  from your box-theory backtest.

## Caveats

- **Survivorship** still applies: the 93-name universe is today's liquid large-caps,
  no ex-ante rule picked them, delisted names absent. Same open issue as box theory.
  Clearing it needs a point-in-time universe (Polygon) — tracked separately.
- **Pre-existing failing test.** `tests/test_engine.py::test_detects_literal_hzg_inside…`
  was already red upstream: its fixture's mother candle fails `_long_body` (body
  0.5 / range 20 = 0.025, needs > 0.5), so it yields 0 trades on both the original and
  the patched engine. This patch does **not** change behaviour for the existing
  variants; `test_rejects_when_inside_bar_range_escapes_mother` still passes. Fix the
  fixture (give A a real long body) separately if you want that test green.
