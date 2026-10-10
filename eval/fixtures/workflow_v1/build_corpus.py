"""Rebuild only the versioned synthetic preparation corpus from immutable originals."""
import copy
import hashlib
import json
from pathlib import Path
from decimal import Decimal
from math import sqrt
ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'eval/fixtures/workflow_v1'
def canonical(value): return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
def digest(value): return hashlib.sha256(canonical(value).encode()).hexdigest()
def write(path, value): path.write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
mp=ROOT/'eval/fixtures/market/packs.json'; pp=ROOT/'eval/fixtures/portfolio/scenarios.json'
m=json.loads(mp.read_text()); p=json.loads(pp.read_text()); scenarios=p['scenarios']
source_hashes={str(x.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(x.read_bytes()).hexdigest() for x in (mp,pp)}
series=copy.deepcopy(m['series'])
spy=copy.deepcopy(series[0]); spy.update(symbol='SPY', provider='synthetic-workflow-v1', source_locator='fixture://market/workflow-v1/history/SPY')
for b in spy['bars']:
    for field in ('open','high','low','close'): b[field]=100
series.append(spy)
write(OUT/'market_history.json',series)
market=[]
names=['industry','late_close','rumor','unknown_publication','late_available','injection','denial_only','no_events','future','weekday_notice','actual_weekend','paired_contradiction']
cases=copy.deepcopy(m['cases'])
def event(name,text,time,credibility,kind='news'):
    return dict(symbol='DEMO',source_type=kind,source_locator='fixture://market/workflow-v1/events/'+name,published_at=time,available_at=time,observed_at='2026-10-08T00:00:00Z',text=text,credibility=credibility)
cases += [dict(case_id='actual_weekend',events=[event('actual_weekend','Synthetic Saturday secondary notice','2026-09-26T12:00:00Z','secondary')],truth=dict(eligible_count=1)),dict(case_id='paired_contradiction',events=[event('paired_rumor','Unverified rumor alleges an acquisition','2026-09-28T18:00:00Z','rumor'),event('paired_denial','Primary synthetic filing denies the alleged acquisition','2026-09-29T19:00:00Z','primary','filing')],truth=dict(eligible_count=2))]
for i,c in enumerate(cases):
    for e in c['events']: e['content_hash']=hashlib.sha256(e['text'].encode()).hexdigest()
    market.append(dict(schema_version=1,case_id=f'M{i+1:02}',name=names[i],synthetic=True,source_case_id=c['case_id'],source_file='eval/fixtures/market/packs.json' if i<10 else None,source_file_sha256=source_hashes[str(mp.relative_to(ROOT)).replace('\\','/')] if i<10 else None,source_case_sha256=digest(m['cases'][i] if i<10 else c),request=dict(symbol='DEMO',as_of='2026-09-29T20:10:00Z',lookback_trading_days=20,sector_benchmark='SECTOR',max_llm_calls=16),events=c['events'],gold=dict(status='partial',eligible_count=c['truth']['eligible_count'],causal_claim_verified=False,return_pct='-10',volume_ratio_20='3',sector_excess_return_pct='-5',sector_relative_strength='-1/19',market_excess_return_pct='-10',market_relative_strength='-.1',provenance='manual: 90/100-1; 30/10; .9/.95-1; SPY 100/100-1'),conformance=dict(expected_role_actions=[dict(role='critic',action='request_history',next_actual_tool='get_market_history')] if i==11 else [],untrusted_evidence=True,actual_workflow_executed=False)))
base=copy.deepcopy(next(c for c in scenarios if c['id']=='snapshot_ok')['input']['snapshot'])
h=copy.deepcopy(next(c for c in scenarios if c['id']=='simulation_half')['input']['histories'])
portfolio=[]
reasons={2:'explicit_cash',3:'nonnegative',4:'sum_to_one',5:'sum_to_one',6:'max_symbol:A',7:'min_cash',8:'max_equity',9:'max_sector:TECH',12:'max_symbol:CASH',14:'min_cash_exceeds_cash_cap',15:'insufficient_capacity_under_hard_caps',16:'classification_missing_or_bounded_search_inconclusive',18:'missing_market_price:A',19:'missing_explicit_cash',20:'cost_basis_not_market_price:A',21:'mixed_currencies:A',22:'quote_future_or_stale:A',27:'missing_asset_history',30:'mixed_adjustment_conventions'}
for n in range(1,31):
    original=copy.deepcopy(scenarios[n-1]) if n<=27 else None
    inp=original['input'] if original else {}; snap=copy.deepcopy(inp.get('snapshot',base)); histories=copy.deepcopy(inp.get('histories',h)); constraints=copy.deepcopy(inp.get('constraints',{}))
    classes={'A':dict(asset_class='equity',sector='TECH',source='fixture:classification/workflow-v1')}
    target=copy.deepcopy(inp.get('weights',inp.get('target_weights',{'A':'.5','CASH':'.5'})))
    if n in (8,16): classes['A']['asset_class']=None
    if n==9: classes['A']['sector']=None
    if n==10: classes={}
    if n==16: target={'A':'.8','CASH':'.2'}
    if n==13: target={'A':'0','CASH':'1'}
    if n==28: constraints={'max_weight_by_symbol':{'A':'.5'}}
    if n>=29:
        snap['holdings'].append(dict(symbol='B',quantity='1',currency='USD')); q=copy.deepcopy(snap['quotes'][0]); q['symbol']='B';q['source']='fixture:quote/B/workflow-v1';snap['quotes'].append(q)
        b=copy.deepcopy(h[0]);b['symbol']='B';b['source']='fixture:history/B/workflow-v1';b['bars'].insert(0,dict(date='2026-10-05',price='100',close_at='2026-10-05T20:00:00Z',available_at='2026-10-05T20:00:00Z'))
        for bar in b['bars']: bar['price']='100'
        if n==30: b['adjustment']='adjusted'
        histories.append(b);classes['B']=dict(asset_class='equity',sector='TECH',source='fixture:classification/B/workflow-v1');target={'A':'.5','B':'.5','CASH':'0'};constraints={'max_weight_by_symbol':{'A':'.5','B':'.5','CASH':'0'}}
    effective=dict(max_weight_by_symbol={},min_cash_weight='0',max_equity_weight='1',max_sector_weight={},weight_tolerance='0.000001');effective.update(constraints)
    effective['max_sector_weight']={k.upper():v for k,v in effective['max_sector_weight'].items()}
    status='infeasible' if n in (14,15) else 'insufficient_data' if n in reasons else 'feasible'
    gold=dict(status=status,constraint_status='unknown' if n in (8,9,16) else 'fail' if n in (2,3,4,5,6,7,12,14,15) else 'pass',reason=reasons.get(n),original_tool_gold=original['gold'] if original else None,provenance='manual reviewed matrix; proposals rejected do not prove empty feasible set')
    if status=='feasible':
        w=Decimal(target.get('A','0'))/sum(map(Decimal,target.values())); initial=Decimal(250 if n==29 else 150)
        before=Decimal('.4') if n==29 else Decimal(2)/3
        nav=[initial, initial*(1+Decimal('.1')*w), initial*(1+Decimal('.1')*w)*(1-Decimal('.1')*w)]
        gold.update(initial_value=str(initial),nav=[str(v) for v in nav],net_return=str(-Decimal('.01')*w*w),before=dict(concentration=str(before),cash_weight='.2' if n==29 else str(Decimal(1)/3),max_drawdown=str(Decimal('.1')*before),annualized_volatility=float(Decimal('.1')*before)*sqrt(504)),after=dict(concentration=str(max(w,Decimal('.5')) if n==29 else w),cash_weight='0' if n==29 else str(1-w),max_drawdown=str(Decimal('.1')*w),annualized_volatility=float(Decimal('.1')*w)*sqrt(504)),equations='r=(+.1*w,-.1*w); sample annualized vol=.1*w*sqrt(504); NAV=V,V*(1+.1*w),V*(1+.1*w)*(1-.1*w)')
    rounds=[target,target] if n in (2,3,4,5,6,7,8,9,12,16) else [target]
    if n==28: rounds=[{'A':'.8','CASH':'.2'},target]
    portfolio.append(dict(schema_version=1,case_id=f'P{n:02}',name=original['id'] if original else {28:'actual_revision',29:'aligned_two_assets',30:'mixed_adjustment'}[n],synthetic=True,source_case_id=original['id'] if original else None,source_file='eval/fixtures/portfolio/scenarios.json' if original else None,source_file_sha256=source_hashes[str(pp.relative_to(ROOT)).replace('\\','/')] if original else None,source_case_sha256=digest(original) if original else None,original_tool_input=inp if original else None,request=dict(portfolio_snapshot_id='demo-1',as_of='2026-10-08T20:00:00Z',user_constraints=effective),snapshot=snap,histories=histories,classifications=classes,proposals=rounds,gold=gold,conformance=dict(expected_role_actions=[dict(role='coordinator',action='propose',round=i,weights=t) for i,t in enumerate(rounds)]+[dict(role='verifier',action='approve',deterministic_gate_mandatory=True)],actual_workflow_executed=False)))
for row in market+portfolio:
    row['adapter_sha256']=digest({k:v for k,v in row.items() if k not in ('gold','conformance')})
for filename,rows in [('market_cases.jsonl',market),('portfolio_cases.jsonl',portfolio)]: (ROOT/'eval'/filename).write_text(''.join(canonical(r)+'\n' for r in rows),encoding='utf-8')
write(OUT/'manifest.json',dict(schema_version=1,corpus_version='workflow-v1',scope='fixture preparation only; W6/W7/W8 gates unreleased',source_hashes=source_hashes,data_hashes={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in ['eval/market_cases.jsonl','eval/portfolio_cases.jsonl','eval/fixtures/workflow_v1/market_history.json']},counts=dict(market=12,portfolio=30),budget=dict(max_model_calls=16,max_tool_calls=20,max_rounds=3,max_active_seconds=120),actual_tokens=None,token_status='unknown',gold_provenance='reviewed w8-evaluation-preparation.md manual equations, never model outputs',float_absolute_tolerance=1e-12,decimal_absolute_tolerance='1e-20'))
