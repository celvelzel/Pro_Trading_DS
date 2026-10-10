"""Independent hand-computed references for portfolio-level risk."""
from datetime import date
from decimal import Decimal
import pytest
from lobster_quant.src.core.portfolio_risk import PortfolioRiskAnalyzer, align_prices

D = [date(2026,10,i) for i in (6,7,8)]

def test_known_path_cash_concentration_volatility_drawdown():
    result = PortfolioRiskAnalyzer().analyze({'A':100}, 100, {'A':dict(zip(D,[100,110,99]))}, 252)
    assert result['weights'] == {'A':Decimal('.5'),'CASH':Decimal('.5')}
    assert result['annualized_volatility'] == pytest.approx((.05**2*2)**.5 * 252**.5)
    assert result['max_drawdown'] == pytest.approx(.05)
    assert result['cash_weight'] == Decimal('.5')
    assert result['concentration'] == Decimal('.5')


def test_alignment_uses_dates_not_positions():
    days, prices, dropped = align_prices({'A':dict(zip(D,[100,110,99])), 'B':{D[0]:50,D[2]:55,date(2026,10,9):500}})
    assert days == [D[0],D[2]]
    assert prices['A'] == [Decimal(100),Decimal(99)]
    assert dropped == 2


def test_zero_volatility_and_undefined_correlation():
    result = PortfolioRiskAnalyzer().analyze({'A':50,'B':50},0,{'A':dict.fromkeys(D,100),'B':dict.fromkeys(D,200)})
    assert result['annualized_volatility'] == result['max_drawdown'] == 0
    assert result['correlations']['A|B'] is None
    assert 'undefined_correlation:A|B' in result['warnings']


def test_correlated_warning_and_concentration():
    result = PortfolioRiskAnalyzer().analyze({'A':90,'B':10},0,{'A':dict(zip(D,[100,110,99])),'B':dict(zip(D,[200,220,198]))})
    assert result['correlations']['A|B'] == pytest.approx(1)
    assert 'high_single_asset_concentration' in result['warnings']
    assert 'high_correlation:A|B' in result['warnings']


def test_cash_only_has_exact_zero_risk():
    r=PortfolioRiskAnalyzer().analyze({},100,{})
    assert r['weights']=={'CASH':Decimal(1)}
    assert r['annualized_volatility']==0


@pytest.mark.parametrize('bad',[-1,0,float('nan'),float('inf')])
def test_invalid_prices_rejected(bad):
    with pytest.raises(ValueError):
        PortfolioRiskAnalyzer().analyze({'A':100},0,{'A':dict(zip(D,[100,bad,110]))})


@pytest.mark.parametrize('values,cash,histories',[({},0,{}),({'A':-1},10,{}),({'A':100},0,{}),({'A':100},0,{'A':{D[0]:100}})])
def test_missing_or_invalid_data(values,cash,histories):
    with pytest.raises(ValueError): PortfolioRiskAnalyzer().analyze(values,cash,histories)
