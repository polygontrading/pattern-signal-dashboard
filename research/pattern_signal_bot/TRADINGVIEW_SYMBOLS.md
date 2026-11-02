# TradingView setup — box theory arrow alerts

Box theory's live US signal is the proprietary **量價齊揚 (green arrow)** on the
詩魂全能成量指標 indicator. The scanner can't recompute it, so TradingView pushes each
arrow to the bot's webhook, and it appears on the dashboard as a `box_theory_arrow`
row. (The candlestick patterns need no TradingView setup — Futu feeds them server-side.)

## 1. Alert body

On each alert, set **Notifications → Webhook URL** to `https://<api-origin>/webhook`
and paste this into the **Message** box (TradingView substitutes the `{{…}}` tokens):

```json
{"secret":"<your-shared-secret>","symbol":"{{ticker}}","price":{{close}},"stop":0,"timeframe":"1D","time":"{{time}}"}
```

- `secret` must match `BOX_THEORY_WEBHOOK_SECRET` on the server.
- `price` = the arrow bar's close (the box-theory trigger reference).
- `stop` = `0` lets the bot default the stop to the entry; set a real level if your
  alert can compute one.
- `timeframe` = `1D` for the daily arrow (use `1W` for weekly).
- Alert **Condition**: the indicator's `OBV量價齊揚` (green arrow). Set it to
  **"Once Per Bar Close"** so it's a completed-bar signal (no repaint).

## 2. Symbols (93)

Use the same universe the scanner covers, so both strategies span one list. Add the
arrow alert to each (TradingView Premium allows the volume; these are plain tickers):

```
MU, NVDA, META, SPCX, TSLA, SNDK, AAPL, AMD, INTC, MSFT,
AMZN, GOOGL, AVGO, GOOG, MRVL, LITE, PLTR, BE, ORCL, NBIS,
STX, DELL, MRNA, WDC, CRWV, MSTR, AMAT, NFLX, LRCX, LLY,
JPM, V, BRK.B, WMT, CRWD, GEV, MDT, QCOM, BAC, COST,
HOOD, UNH, CRM, PANW, GS, XOM, CAT, COHR, CSCO, JNJ,
CVX, TXN, BA, KLAC, MA, TMO, IREN, CRDO, NOW, HD,
COIN, ACN, GE, MRK, KO, MCD, CBRS, SHOP, NKE, SMCI,
SNOW, PG, IBM, RKLB, VLO, ALAB, ADI, ABBV, PEP, APP,
WFC, VZ, BKNG, NU, C, VRT, HPE, GLW, AMGN, MELI,
MS, UBER, T
```

Pending (add when ready): `ADBE, CIEN, SNPS, SATS, MPC, TWLO, INTU`

## Notes

- One alert per symbol per timeframe. Re-firing the same arrow on the same bar is
  idempotent in the store (no duplicate rows).
- The arrow already carries box theory's volume condition, so there's no separate VRR
  gate on the webhook — VRR is enforced server-side only for the candlestick variants.
- Non-US box theory (HK / Japan / crypto) uses the replica arrow and can be scanned
  server-side later; it doesn't need TradingView alerts.
