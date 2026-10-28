"""Publish a credential-free scanner snapshot to the GitHub Pages source repo.

The dashboard is intentionally static: only derived signal data and aggregate
research statistics are published. Provider credentials and raw candles stay on
the server.
"""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .store import connect

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "git@github.com:polygontrading/pattern-signal-dashboard.git"
CHECKOUT = Path("/opt/pattern-signal-dashboard-repo")
DEPLOY_KEY = Path("/root/.ssh/pattern_signal_dashboard_deploy")

def _git(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["GIT_SSH_COMMAND"] = f"ssh -i {DEPLOY_KEY} -o IdentitiesOnly=yes"
    return subprocess.run(["git", *args], cwd=CHECKOUT, env=env, check=True,
                          capture_output=True, text=True)

def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def _ensure_checkout() -> None:
    if CHECKOUT.exists():
        _git("pull", "--ff-only", "origin", "main")
        return
    env = os.environ.copy()
    env["GIT_SSH_COMMAND"] = f"ssh -i {DEPLOY_KEY} -o IdentitiesOnly=yes"
    subprocess.run(["git", "clone", "--branch", "main", REPOSITORY, str(CHECKOUT)],
                   env=env, check=True, capture_output=True, text=True)

def publish() -> bool:
    _ensure_checkout()
    config = json.loads((ROOT / "config.json").read_text())
    db = connect(ROOT / config["database"])
    # Candlestick pattern variants plus ingested webhook variants (box-theory arrow).
    active_variants = [item["id"] for item in config["variants"]] + config.get("webhook_variants", [])
    placeholders = ",".join("?" for _ in active_variants)
    rows = db.execute(
        f"SELECT * FROM scans WHERE qualified=1 AND variant_id IN ({placeholders}) "
        "ORDER BY setup_date DESC, scanned_at DESC LIMIT 200",
        active_variants,
    ).fetchall()
    signals = []
    for row in rows:
        item = dict(row)
        item["metrics"] = json.loads(item.pop("metrics_json"))
        signals.append(item)
    latest = db.execute("SELECT MAX(session) AS latest FROM candles").fetchone()["latest"]
    _write_json(CHECKOUT / "data" / "signals.json", signals)
    _write_json(CHECKOUT / "data" / "health.json", {
        "ok": True,
        "service": "pattern-signal-bot",
        "provider": "Futu",
        "latest_candle": latest,
        "published_at": datetime.now(timezone.utc).isoformat(),
        "universe": {
            "symbols": config["symbols"] + config.get("crypto_symbols", []),
            "pending_stock_symbols": config.get("pending_stock_symbols", []),
            "timeframes": config["timeframes"],
        },
    })
    changed = _git("status", "--porcelain", "--", "data").stdout.strip()
    if not changed:
        return False
    _git("add", "data")
    _git("-c", "user.name=Pattern Signal Bot", "-c", "user.email=pattern-signal-bot@users.noreply.github.com",
         "commit", "-m", "Refresh signal snapshot")
    _git("push", "origin", "main")
    return True

if __name__ == "__main__":
    print(json.dumps({"published": publish()}))
