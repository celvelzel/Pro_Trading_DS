from datetime import date
from decimal import Decimal
import pytest
from lobster_quant.src.core.allocation_simulator import AllocationSimulator

D=[date(2026,10,i) for i in (6,7,8)]
H={'A':dict(zip(D,[100,110,99]))}


def test_half_cash_daily_rebalance_hand_math():
    result=AllocationSimulator().simulate(H,{'A':'.5','CASH':'.5'},100)
    assert [float(p['net_value']) for p in result['path']] == pytest.approx([100,105,99.75])
    assert float(result['total_return']) == pytest.approx(-.0025)


def test_buy_hold_differs_from_daily_rebalance():
    result=AllocationSimulator().simulate(H,{'A':'.5','CASH':'.5'},100,10)
    assert float(result['path'][-1]['net_value']) == pytest.approx(99.5)


def test_initial_fee_is_self_financing_and_not_ignored():
    result=AllocationSimulator().simulate({'A':dict.fromkeys(D,100)},{'A':1,'CASH':0},100,fee_bps=100,slippage_bps=100)
    assert float(result['path'][0]['net_value']) == pytest.approx(100/1.02)
    assert float(result['total_cost']) == pytest.approx(100-100/1.02)
    assert float(result['path'][-1]['net_value']) == pytest.approx(100/1.02)


def test_rebalance_cost_uses_buys_and_sells():
    result=AllocationSimulator().simulate(H,{'A':'.5','CASH':'.5'},100,fee_bps=100)
    initial_nav=100/1.005
    pre=initial_nav*1.05
    post=(pre-.01*initial_nav*.55)/(.995)
    assert float(result['path'][1]['net_value']) == pytest.approx(post)
    assert float(result['path'][1]['cost']) == pytest.approx(pre-post)


def test_alignment_and_prefix_no_lookahead():
    full=AllocationSimulator().simulate(H,{'A':1,'CASH':0},100)
    prefix=AllocationSimulator().simulate({'A':{D[0]:100,D[1]:110}},{'A':1,'CASH':0},100)
    assert prefix['path']==full['path'][:2]
    r=AllocationSimulator().simulate({'A':H['A'],'B':{D[0]:100,D[2]:100}}, {'A':'.5','B':'.5','CASH':0},100)
    assert [p['date'] for p in r['path']]==[D[0],D[2]]
    assert float(r['path'][-1]['net_value']) == pytest.approx(99.5)


def test_cash_only_uses_explicit_calendar():
    r=AllocationSimulator().simulate(H,{'A':0,'CASH':1},100,fee_bps=200)
    assert all(p['net_value']==100 for p in r['path'])
    assert r['total_cost']==0


@pytest.mark.parametrize('weights',[{'A':1},{'A':-1,'CASH':2},{'A':.8,'CASH':.8},{'A':float('inf'),'CASH':0},{'A':float('nan'),'CASH':0}])
def test_invalid_weights(weights):
    with pytest.raises(ValueError): AllocationSimulator().simulate(H,weights,100)


@pytest.mark.parametrize('kwargs',[{'initial_value':0},{'initial_value':-1},{'initial_value':float('nan')},{'initial_value':100,'rebalance_every':0},{'initial_value':100,'fee_bps':10000},{'initial_value':100,'slippage_bps':-1}])
def test_invalid_simulation_inputs(kwargs):
    with pytest.raises(ValueError): AllocationSimulator().simulate(H,{'A':1,'CASH':0},**kwargs)


def test_tolerated_weight_rounding_cannot_create_wealth():
    r=AllocationSimulator().simulate({'A':dict.fromkeys(D,100)},{'A':'.5','CASH':'.500000001'},100)
    assert all(float(p['net_value'])==pytest.approx(100,abs=1e-12) for p in r['path'])
