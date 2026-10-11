"""Capture latest US/USD data once; workers only replay the frozen dataset."""
from __future__ import annotations
import hashlib
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Literal
from pydantic import Field
from agent.financial_config import ROOT, model_config, FinancialRoleModel, FinancialModelConfig
from agent.shared import FinancialModel, ArtifactStore
from agent.financial import build_financial_dispatcher
from agent.integration import CrossMASRouter
from agent.tools.market_history import (HistorySeries, HistoryBar, FixtureHistoryBackend,
    MarketDependencies, Symbol)
from agent.tools.market_events import EventRecord, FixtureEventBackend, EventDependencies
from agent.tools.portfolio_snapshot import SnapshotRecord, Holding, ValuationQuote
from agent.tools.portfolio_risk import AssetHistory, HistoryBar as RiskBar
from agent.tools.allocation import AssetClassification
from db.models import FinancialDataset

PREFIX = 'live-financial-v1:'


class CapturedInputs(FinancialModel):
    dataset_id: str
    conversation_id: str
    as_of: datetime
    model_identity: str
    workflow: Literal['market', 'portfolio', 'combined']
    market_symbol: str | None = None
    sector_benchmark: str | None = None
    snapshot: SnapshotRecord | None = None
    market_histories: list[HistorySeries]
    risk_histories: list[AssetHistory]
    events: list[EventRecord] = Field(default_factory=list)
    classifications: dict[str, AssetClassification] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)


def _hash(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def save_dataset(sessions, data):
    payload = data.model_dump(mode='json')
    with sessions() as session:
        session.add(FinancialDataset(id=data.dataset_id, conversation_id=data.conversation_id,
            payload=payload, content_hash=_hash(payload)))
        session.commit()


def load_dataset(sessions, dataset_id, conversation_id=None):
    # Only UUID-named server-side datasets may select a trusted live profile.
    try:
        if str(uuid.UUID(dataset_id)) != dataset_id:
            raise ValueError()
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError('真实数据快照 ID 不正确。') from exc
    with sessions() as session:
        row = session.get(FinancialDataset, dataset_id)
        if row is None or (conversation_id is not None and row.conversation_id != conversation_id):
            raise KeyError('真实数据快照不存在或不属于此会话。')
        if row.content_hash != _hash(row.payload):
            raise ValueError('真实数据快照校验失败。')
        data = CapturedInputs.model_validate(row.payload)
        if data.dataset_id != row.id or data.conversation_id != row.conversation_id:
            raise ValueError('真实数据快照身份不匹配。')
        return data


def read_holdings(directory=None):
    """No PortfolioStore construction: it supplies virtual default cash."""
    # Match the existing Portfolio API's data/portfolio directory in its API process.
    path = Path(directory or os.getenv('FINANCIAL_PORTFOLIO_DIR', 'data/portfolio'))
    try:
        positions = json.loads((path / 'positions.json').read_text(encoding='utf-8-sig'))
        cash = json.loads((path / 'cash.json').read_text(encoding='utf-8-sig'))
    except (OSError, ValueError) as exc:
        raise ValueError('请先在持仓页保存实际持仓和实际现金；缺失文件不会使用默认现金。') from exc
    if not isinstance(positions, list) or not isinstance(cash, dict) or 'balance' not in cash:
        raise ValueError('持仓或现金文件格式不正确。')
    holdings = []
    for p in positions:
        if not isinstance(p, dict):
            raise ValueError('持仓记录格式不正确。')
        name = str(p.get('symbol', '')).strip().upper()
        if name.endswith(('.HK', '.SS', '.SZ', '.BJ')) or name.isdigit():
            raise ValueError('第一版真实组合仅支持美股 / USD；请勿混用其他币种。')
        # Currency absent in legacy US position files means explicit USD-only input scope.
        if p.get('currency', 'USD') != 'USD':
            raise ValueError('真实组合当前仅支持 USD。')
        holdings.append(Holding(symbol=name, quantity=p.get('shares'), currency='USD'))
    if len({h.symbol for h in holdings}) != len(holdings):
        raise ValueError('真实持仓包含重复标的。')
    if len(holdings) > 30:
        raise ValueError('单次最多支持 30 个持仓标的。')
    try:
        amount = Decimal(str(cash['balance']))
        if not amount.is_finite() or amount < 0 or cash.get('currency', 'USD') != 'USD':
            raise ValueError()
    except Exception as exc:
        raise ValueError('请提供明确、非负的 USD 现金余额。') from exc
    return holdings, amount


class YahooCapture:
    """Latest observations, not a historical knowledge archive or exchange feed."""
    def __init__(self):
        self.limitations = ['Yahoo 行情可能延迟；不是交易所实时流。',
            '复权历史为当前获取的回顾数据；仅用于本快照时点的历史模拟。',
            '当前提案的历史模拟是固定权重回顾情景，不代表历史当时生成的策略或未来收益。']

    def fetch(self, symbol):
        import pandas as pd
        import yfinance as yf
        import exchange_calendars as xcals
        ticker = yf.Ticker(symbol)
        daily = ticker.history(period='1y', interval='1d', auto_adjust=False,
            back_adjust=False, repair=False, timeout=12, raise_errors=True)
        if daily.empty or not {'Open', 'High', 'Low', 'Close', 'Volume', 'Adj Close'} <= set(daily.columns):
            raise ValueError('缺少原始或复权日线：' + symbol)
        meta = ticker.history_metadata
        if meta.get('currency') != 'USD' or meta.get('exchangeTimezoneName') != 'America/New_York':
            raise ValueError('行情不是可验证的美股 USD 数据：' + symbol)
        calendar = xcals.get_calendar('XNYS')
        observed = datetime.now(timezone.utc)
        bars, risk = [], []
        for index, row in daily.iterrows():
            day = index.date()
            session = pd.Timestamp(day)
            if not calendar.is_session(session):
                continue
            close_at = calendar.session_close(session).to_pydatetime()
            if close_at > observed:
                continue  # Never use today's still-forming daily bar.
            bars.append(HistoryBar(session_date=day, close_at=close_at, available_at=observed,
                **{k: float(row[col]) for k, col in [('open','Open'),('high','High'),
                    ('low','Low'),('close','Close'),('volume','Volume')]}))
            risk.append(RiskBar(date=close_at.date(), close_at=close_at, available_at=observed,
                price=Decimal(str(row['Adj Close']))))
        if len(bars) < 21:
            raise ValueError('完整交易日日线不足 21 条：' + symbol)
        bars.sort(key=lambda b: b.session_date)
        risk.sort(key=lambda b: b.date)
        sessions = calendar.sessions_in_range(pd.Timestamp(bars[0].session_date),
            pd.Timestamp(observed.astimezone(calendar.tz).date()))
        completed = [d.date() for d in sessions if calendar.session_close(d).to_pydatetime() <= observed]
        if not completed or bars[-1].session_date != completed[-1]:
            raise ValueError('最近已收盘交易日数据缺失：' + symbol)
        # Latest completed regular-session minute for valuation, with actual bar time.
        minute = ticker.history(period='5d', interval='1m', auto_adjust=False,
            prepost=False, timeout=12, raise_errors=True)
        quote_observed = datetime.now(timezone.utc)
        eligible = [(i.to_pydatetime().astimezone(timezone.utc)+timedelta(minutes=1), row)
            for i, row in minute.iterrows() if i.tzinfo is not None
            and i.to_pydatetime().astimezone(timezone.utc)+timedelta(minutes=1) <= quote_observed]
        if not eligible:
            raise ValueError('最新分钟行情不可用：' + symbol)
        effective, quote_row = max(eligible, key=lambda v: v[0])
        required_close = calendar.session_close(pd.Timestamp(completed[-1])).to_pydatetime()
        if effective < required_close-timedelta(minutes=5) or quote_observed-effective > timedelta(days=7):
            raise ValueError('最新估值行情过期：' + symbol)
        if calendar.is_session(pd.Timestamp(quote_observed.astimezone(calendar.tz).date())):
            session = pd.Timestamp(quote_observed.astimezone(calendar.tz).date())
            opening, closing = calendar.session_open(session).to_pydatetime(), calendar.session_close(session).to_pydatetime()
            if opening+timedelta(minutes=20) < quote_observed < closing and quote_observed-effective > timedelta(minutes=20):
                raise ValueError('交易时段内最新行情延迟超过 20 分钟：' + symbol)
        quote = ValuationQuote(symbol=symbol, price=Decimal(str(quote_row['Close'])), currency='USD',
            effective_at=effective, available_at=quote_observed, source='yahoo:1m:latest-observed')
        kind = 'equity' if meta.get('instrumentType') == 'EQUITY' else None
        classification = AssetClassification(asset_class=kind, source='yahoo:history-metadata')
        history = HistorySeries(symbol=symbol, provider='yfinance', source_locator=f'https://finance.yahoo.com/quote/{symbol}/history/',
            currency='USD', exchange='US', exchange_timezone='America/New_York', adjustment='raw',
            point_in_time_safe=True, bars=bars, expected_sessions=completed)
        adjusted = AssetHistory(symbol=symbol, currency='USD', source='yahoo:adj-close:captured-now',
            adjustment='adjusted', exchange_timezone='America/New_York', bars=tuple(risk))
        events = []
        try:
            for item in ticker.news[:20]:
                content = item.get('content', {})
                pub = content.get('pubDate')
                url = (content.get('canonicalUrl') or {}).get('url')
                text = '\n'.join(v for v in [content.get('title'), content.get('summary')] if isinstance(v,str))
                if pub and isinstance(url,str) and url.startswith(('https://','http://')) and text:
                    published = datetime.fromisoformat(pub.replace('Z','+00:00'))
                    if published.tzinfo is not None:
                        events.append(EventRecord(symbol=symbol, source_type='news', source_locator=url,
                            published_at=published, available_at=datetime.now(timezone.utc),
                            observed_at=datetime.now(timezone.utc), text=text[:20000], credibility='secondary'))
        except Exception:
            self.limitations.append('新闻接口不可用或发布时间缺失：' + symbol)
        return history, adjusted, quote, classification, events


def capture_inputs(conversation_id, workflow, symbol='MU', sector_benchmark=None, *, source=None, directory=None):
    config = model_config()
    if not config.ready:
        raise ValueError('请先填写独立的金融 MAS 模型配置，再准备真实数据。')
    source = source or YahooCapture()
    holdings, cash = read_holdings(directory) if workflow != 'market' else ([], None)
    symbol = symbol.strip().upper()
    # Typed symbol validation, before external data calls.
    from pydantic import TypeAdapter
    symbol = TypeAdapter(Symbol).validate_python(symbol)
    if sector_benchmark:
        sector_benchmark = TypeAdapter(Symbol).validate_python(sector_benchmark.strip().upper())
    names = {h.symbol for h in holdings}
    if workflow == 'combined' and symbol not in names:
        raise ValueError('Combined 调查标的必须属于你的持仓。')
    if workflow != 'portfolio':
        names.update([symbol, 'SPY'])
        if sector_benchmark:
            names.add(sector_benchmark)
    if not names:
        names.add('SPY')  # A sourced calendar for cash-only simulation.
    if len(names) > 32:
        raise ValueError('单次行情最多支持 32 个标的。')
    histories, risks, quotes, classes, events = [], [], [], {}, []
    for name in sorted(names):
        raw, adjusted, quote, classification, news = source.fetch(name)
        histories.append(raw); risks.append(adjusted); quotes.append(quote)
        classes[name] = classification; events.extend(news)
    overrides_path = Path(os.getenv('FINANCIAL_CLASSIFICATIONS_FILE', str(ROOT/'financial-classifications.json')))
    if overrides_path.is_file():
        try:
            overrides = json.loads(overrides_path.read_text(encoding='utf-8-sig'))
            for name in names:
                if name in overrides:
                    classes[name] = AssetClassification.model_validate(overrides[name])
        except (ValueError, TypeError, OSError) as exc:
            raise ValueError('资产分类配置不正确。') from exc
    as_of = datetime.now(timezone.utc)
    identifier = str(uuid.uuid4())
    held_names = {h.symbol for h in holdings}
    snapshot = SnapshotRecord(snapshot_id='user-'+identifier, source='local-user-portfolio:USD',
        effective_at=as_of, currency='USD', cash=cash,
        holdings=tuple(h.model_copy(update={'sector':classes[h.symbol].sector,
            'classification_source':classes[h.symbol].source}) for h in holdings),
        quotes=tuple(q for q in quotes if q.symbol in held_names)) if workflow != 'market' else None
    limitations = list(source.limitations)
    if snapshot:
        limitations.append('来源为用户保存的持仓；未与券商账户对账。')
    if not events:
        limitations.append('本次没有取得可用新闻；不会补造事件证据。')
    missing_classes = sorted(name for name in held_names if not classes[name].asset_class or not classes[name].sector)
    if missing_classes:
        limitations.append('资产/行业分类不完整：'+', '.join(missing_classes)+'；相关条件无法确认时返回 unknown。')
    return CapturedInputs(dataset_id=identifier, conversation_id=conversation_id, as_of=as_of,
        model_identity=config.identity(), workflow=workflow,
        market_symbol=symbol if workflow != 'portfolio' else None, sector_benchmark=sector_benchmark,
        snapshot=snapshot, market_histories=histories, risk_histories=risks,
        events=events, classifications=classes, limitations=limitations)


def live_assembly(sessions, profile, enabled=('market_investigation','portfolio_rebalance'), *, require_model=True):
    if not profile.startswith(PREFIX):
        raise ValueError('Unsupported financial execution profile')
    data = load_dataset(sessions, profile[len(PREFIX):])
    loader = lambda sid: data.snapshot.model_copy(deep=True) if data.snapshot and data.snapshot.snapshot_id == sid else None
    if not enabled:
        from agent.shared import FinancialMASDispatcher
        return FinancialMASDispatcher(sessions, execution_profile=profile), None
    try:
        config = model_config()
    except ValueError:
        if require_model:
            raise
        config = FinancialModelConfig()
    valid = config.ready and config.identity() == data.model_identity
    if require_model and not valid:
        raise ValueError('金融模型配置缺失或已变更；请重新准备数据快照。')
    providers = {kind:{role:FinancialRoleModel(config,role) if valid else UnavailableRoleModel() for role in roles} for kind,roles in (
        ('market_investigation',('coordinator','price_volume','macro_sector','event','critic')),
        ('portfolio_rebalance',('coordinator','opportunity','risk','constraint','verifier')))}
    route = None
    deps = None
    if 'portfolio_rebalance' in enabled:
        from agent.portfolio_mas import PortfolioDependencies
        deps = PortfolioDependencies(loader, lambda snapshot, at: tuple(h.model_copy(deep=True)
            for h in data.risk_histories if h.symbol in {v.symbol for v in snapshot.holdings} or not snapshot.holdings),
            data.classifications, snapshot_max_age_seconds=604800)
    dispatcher = build_financial_dispatcher(sessions, enabled=enabled, demo=False,
        execution_profile=profile, providers=providers,
        market_dependencies=MarketDependencies(FixtureHistoryBackend(data.market_histories)),
        event_dependencies=EventDependencies(FixtureEventBackend(data.events) if data.events else None),
        portfolio_dependencies=deps, portfolio_artifact_resolver=lambda *args:route.artifact_resolver(*args))
    route = CrossMASRouter(dispatcher, ArtifactStore(sessions), loader, execution_profile=profile)
    return dispatcher, route


class UnavailableRoleModel:
    """Keep lifecycle/cancellation available; fail execution through runtime CAS."""
    async def complete(self, messages, *, request_id=None):
        from agent.llm import ModelProviderError
        raise ModelProviderError('financial_provider_unavailable', 'Financial provider configuration changed or is unavailable')
