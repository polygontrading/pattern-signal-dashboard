from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .engine import Variant, backtest
from .store import connect, load_candles

ROOT = Path(__file__).resolve().parents[1]


class Api(BaseHTTPRequestHandler):
    def do_GET(self):
        db = connect(ROOT / "pattern_signal.sqlite3")
        request = urlparse(self.path)
        route, query = request.path, parse_qs(request.query)
        if route == "/api/health":
            latest = db.execute("SELECT MAX(session) AS latest FROM candles").fetchone()["latest"]
            payload = {"ok": True, "service": "pattern-signal-bot", "latest_candle": latest}
        elif route == "/api/signals":
            rows = db.execute("SELECT * FROM scans WHERE qualified=1 ORDER BY setup_date DESC, scanned_at DESC LIMIT 200").fetchall()
            payload = [{**dict(r), "metrics": json.loads(r["metrics_json"])} for r in rows]
        elif route == "/api/trades":
            symbol = query.get("symbol", [None])[0]
            timeframe = query.get("timeframe", [None])[0]
            variant_id = query.get("variant", [None])[0]
            if not all((symbol, timeframe, variant_id)):
                self.send_error(400, "symbol, timeframe, and variant are required")
                return
            config = json.loads((ROOT / "config.json").read_text())
            definition = next((x for x in config["variants"] if x["id"] == variant_id), None)
            if definition is None:
                self.send_error(404, "unknown variant")
                return
            payload = [{"entry_date": x.entry_date, "entry": x.entry, "initial_stop": x.initial_stop,
                        "exit_date": x.exit_date, "exit_price": x.exit_price, "return_pct": x.return_pct,
                        "status": x.status, "same_bar_ambiguous": x.same_bar_ambiguous}
                       for x in backtest(load_candles(db, symbol, timeframe), Variant(**definition))]
        elif route == "/api/symbols":
            payload = [dict(r) for r in db.execute("SELECT symbol,timeframe,MAX(session) AS latest_session FROM candles GROUP BY symbol,timeframe ORDER BY symbol,timeframe")]
        else:
            self.send_error(404)
            return
        body = json.dumps(payload, default=str).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        origin = os.getenv("PATTERN_DASHBOARD_ORIGIN")
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        return


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 8787), Api).serve_forever()
