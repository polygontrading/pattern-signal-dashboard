from futu import OpenQuoteContext, RET_OK

q = OpenQuoteContext(host="127.0.0.1", port=11111)
try:
    result, quota = q.get_history_kl_quota(get_detail=False)
    print(quota if result == RET_OK else f"ERROR {quota}")
finally:
    q.close()
