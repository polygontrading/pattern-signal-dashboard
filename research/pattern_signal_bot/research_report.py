import json
from pathlib import Path
from pattern_signal_bot.engine import Variant, backtest, performance
from pattern_signal_bot.store import connect, load_candles

root = Path('/opt/pattern-signal-bot')
cfg = json.loads((root/'config.json').read_text()); db = connect(root/cfg['database'])
symbols = cfg['symbols'] + cfg.get('crypto_symbols', [])
for tf in cfg['timeframes']:
    print('\n'+tf.upper())
    for spec in cfg['variants']:
        rows=[]
        for s in symbols:
            bars=load_candles(db,s,tf)
            if not bars: continue
            m=performance(backtest(bars,Variant(**spec)),bars[-1].session,10)
            if m['trades']:
                rows.append((s,m['trades'],m['mean_return_pct'],m['win_rate'],m['total_return_pct']))
        pos=sum(x[2]>0 for x in rows)
        mean=sum(x[2] for x in rows)/len(rows) if rows else None
        print(spec['id'], 'products',len(rows),'positive',pos,'mean',mean)
        print('top',[(x[0],round(x[2]*100,2),x[1]) for x in sorted(rows,key=lambda x:x[2],reverse=True)[:5]])
