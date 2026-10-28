from __future__ import annotations

from datetime import date

from .engine import Candle


def fetch(symbol: str, timeframe: str, start: date, end: date, host: str, port: int) -> list[Candle]:
    from futu import AuType, KLType, OpenQuoteContext, RET_OK
    kind = {"day": KLType.K_DAY, "week": KLType.K_WEEK, "month": KLType.K_MON}[timeframe]
    q = OpenQuoteContext(host=host, port=port)
    try:
        result, data, page = q.request_history_kline(symbol, start=start.isoformat(), end=end.isoformat(), ktype=kind, autype=AuType.QFQ, max_count=1000)
        if result != RET_OK:
            raise RuntimeError(f"Futu request failed for {symbol} {timeframe}: {data}")
        pages = [data]
        while page is not None:
            result, data, page = q.request_history_kline(symbol, start=start.isoformat(), end=end.isoformat(), ktype=kind, autype=AuType.QFQ, max_count=1000, page_req_key=page)
            if result != RET_OK:
                raise RuntimeError(f"Futu page failed for {symbol} {timeframe}: {data}")
            pages.append(data)
        frame = __import__("pandas").concat(pages).drop_duplicates(subset=["time_key"]).sort_values("time_key")
        return [Candle(date.fromisoformat(str(row.time_key)[:10]), float(row.open), float(row.high), float(row.low), float(row.close), float(row.volume)) for row in frame.itertuples()]
    finally:
        q.close()
