import json
from pathlib import Path
from pattern_signal_bot.engine import Variant, _setup
from pattern_signal_bot.store import connect, load_candles

ROOT=Path('/opt/pattern-signal-bot'); cfg=json.loads((ROOT/'config.json').read_text()); db=connect(ROOT/cfg['database'])
H={'day':[63,126,252,504],'week':[13,26,52,104],'month':[3,6,12,24]}; COST=.001
def net(px,entry): return (px/entry)*(1-COST)/(1+COST)-1
def signals(bars,v):
    return [s for i in range(20,len(bars)-2) if (s:=_setup(bars,i,v))]
def fixed(bars,s,h,stop=False):
    e,entry,sl=s; end=e+h
    if end>=len(bars): return None
    if stop:
        for j in range(e,len(bars[:end+1])):
            if bars[j].low<=sl: return net(sl,entry)
    return net(bars[end].close,entry)
for tf in cfg['timeframes']:
 print('\n'+tf.upper())
 for spec in cfg['variants']:
  v=Variant(**spec); allsig=[]
  for sym in cfg['symbols']+cfg.get('crypto_symbols',[]): allsig += [(load_candles(db,sym,tf),x) for x in signals(load_candles(db,sym,tf),v)]
  print(spec['id'],'signals',len(allsig))
  for h in H[tf]:
   a=[fixed(b,s,h,False) for b,s in allsig]; a=[x for x in a if x is not None]
   z=[fixed(b,s,h,True) for b,s in allsig]; z=[x for x in z if x is not None]
   def fmt(x): return 'n=%d mean=%.2f%% win=%.1f%%'%(len(x),100*sum(x)/len(x),100*sum(y>0 for y in x)/len(x)) if x else 'n=0'
   print('h',h,'no_stop',fmt(a),'initial_stop',fmt(z))
