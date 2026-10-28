"""Box-theory arrow webhook receiver.

Box theory's live US signal is the proprietary 量價齊揚 (volume+price) arrow, which
fires inside TradingView. We can't recompute it server-side, so we ingest it: the
user points a TradingView alert at this endpoint, and each arrow becomes a signal
row on the same dashboard as the candlestick patterns.

The alert body is JSON the user configures on the TradingView alert, e.g.:
  {"secret":"...","symbol":"{{ticker}}","price":{{close}},"stop":0,"timeframe":"1D","time":"{{time}}"}

Set BOX_THEORY_WEBHOOK_SECRET in the environment to require the shared secret.
Research stats for the research columns are optional and come from config
(box_theory_reference_metrics); when absent the row shows its live trigger only.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .store import connect, record_scan

ROOT = Path(__file__).resolve().parents[1]
VARIANT_ID = "box_theory_arrow"
_WINDOW = {"trades": 0, "win_rate": None, "mean_return_pct": None, "total_return_pct": None}
EMPTY_METRICS = {"10": dict(_WINDOW), "5": dict(_WINDOW), "1": dict(_WINDOW)}
_TIMEFRAME = {"1D": "day", "D": "day", "day": "day", "1W": "week", "W": "week", "week": "week",
              "1M": "month", "M": "month", "month": "month"}

def build_signal(payload: dict, now: str | None = None, reference_metrics: dict | None = None) -> dict:
    """Map a TradingView box-theory arrow alert to a dashboard signal record.
    Required keys: symbol, price. Optional: stop, timeframe, time (the signal date)."""
    now = now or datetime.now(timezone.utc).isoformat()
    symbol = str(payload["symbol"]).strip()
    if "." not in symbol and "-" not in symbol:
        symbol = f"US.{symbol}"  # a bare TradingView ticker -> Futu-style US symbol
    entry = float(payload["price"])
    raw_stop = payload.get("stop")
    stop = float(raw_stop) if raw_stop not in (None, "", 0, "0") else entry
    timeframe = _TIMEFRAME.get(str(payload.get("timeframe", "1D")), "day")
    setup_date = str(payload.get("time", now))[:10]
    return {
        "scanned_at": now, "symbol": symbol, "timeframe": timeframe, "variant_id": VARIANT_ID,
        "setup_date": setup_date, "entry": entry, "initial_stop": stop, "qualified": True,
        "metrics": reference_metrics or EMPTY_METRICS, "provider": "tradingview",
    }

class Hook(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode() if length else "{}"
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            self.send_error(400, "invalid JSON"); return
        secret = os.getenv("BOX_THEORY_WEBHOOK_SECRET")
        if secret and str(payload.get("secret", "")) != secret:
            self.send_error(401, "bad secret"); return
        if "symbol" not in payload or "price" not in payload:
            self.send_error(400, "symbol and price are required"); return
        config = json.loads((ROOT / "config.json").read_text())
        signal = build_signal(payload, reference_metrics=config.get("box_theory_reference_metrics"))
        record_scan(connect(ROOT / config["database"]), signal)
        body = json.dumps({"recorded": True, "symbol": signal["symbol"], "setup_date": signal["setup_date"]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        return

if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 8788), Hook).serve_forever()
