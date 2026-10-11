"""Synthetic read-only financial workflows, independent of General lifecycle."""
from datetime import datetime, timezone
import logging
import os

from fastapi import APIRouter, BackgroundTasks, HTTPException

from agent.financial import build_financial_dispatcher
from agent.financial_demo import DEMO_SNAPSHOT_ID, demo_snapshot_loader
from agent.integration import CrossMASRequest, CrossMASRouter
from agent.shared import ArtifactRef, ArtifactStore, FinancialConflict, MarketInvestigationArtifact
from agent.shared.dispatch import aware
from api.models.financial import (FinancialCreateResponse, FinancialRunAction,
    FinancialRunResponse, MarketRunResult, PortfolioRunResult, FinancialWorkflowRequest,
    FinancialLivePrepare, FinancialConstraintInput, FinancialConnectionCheck)
from db.models import Conversation, FinancialArtifact
from db.session import sync_session_factory

router = APIRouter()
logger = logging.getLogger(__name__)
TERMINAL = {'completed', 'failed', 'cancelled', 'expired'}


@router.get('/connection')
def connection_status():
    from agent.financial_config import model_config
    try:
        config = model_config()
        return {'configured': config.ready, 'model': config.model, 'scope': 'US/USD',
            'data_provider': 'Yahoo latest observations (may be delayed)',
            'message': '独立金融模型已配置；尚未测试连接。' if config.ready else '请填写 financial-mas.json 独立模型配置。'}
    except ValueError:
        return {'configured': False, 'model': '', 'scope': 'US/USD', 'data_provider': 'Yahoo',
            'message': '金融模型配置格式不正确。'}


@router.post('/connection/check')
async def check_connection(payload: FinancialConnectionCheck):
    from agent.financial_config import model_config
    from agent.llm import ModelProviderError
    try:
        config = model_config()
        if not config.ready:
            raise HTTPException(503, '请先填写独立金融模型配置。')
        if payload.check_model:
            await config.provider().complete([{'role':'system','content':'Return JSON only: {"ok": true}.'},
                {'role':'user','content':'Connection check; no portfolio data.'}])
        return {'configured':True, 'model':config.model,'scope':'US/USD',
            'data_provider':'Yahoo latest observations (may be delayed)',
            'message':'模型连接成功。行情连接将在准备数据时逐标的检查。'}
    except ModelProviderError as exc:
        raise HTTPException(502, '模型连接失败，请检查服务地址、模型和密钥；密钥不会返回页面。') from exc
    except ValueError as exc:
        raise HTTPException(422, '金融模型配置格式不正确。') from exc


@router.post('/constraints/parse')
async def parse_constraint_input(payload: FinancialConstraintInput):
    from agent.financial_constraints import parse_constraints
    from agent.llm import ModelProviderError
    try:
        return await parse_constraints(payload.text, [s.strip().upper() for s in payload.symbols],
            [s.strip().upper() for s in payload.sectors], payload.use_llm)
    except ModelProviderError as exc:
        raise HTTPException(503, '模型解析不可用；可使用规则解析或手动填写约束。') from exc
    except ValueError as exc:
        raise HTTPException(422, '模型没有返回有效约束，请重新描述或手动填写。') from exc


@router.post('/live/prepare')
def prepare_live(payload: FinancialLivePrepare):
    from agent.financial_live import capture_inputs, save_dataset
    from agent.tools.portfolio_snapshot import get_portfolio_snapshot, SnapshotInput
    with sync_session_factory() as session:
        if session.get(Conversation, payload.conversation_id) is None:
            raise HTTPException(404, 'Conversation not found')
    try:
        data = capture_inputs(payload.conversation_id,payload.workflow,payload.symbol,payload.sector_benchmark)
        if data.snapshot:
            checked = get_portfolio_snapshot(SnapshotInput(snapshot_id=data.snapshot.snapshot_id,
                as_of=data.as_of,max_age_seconds=604800), lambda sid:data.snapshot)
            if checked.status != 'ok':
                raise ValueError('真实持仓快照缺少必要数据：'+', '.join(checked.reasons))
        save_dataset(sync_session_factory, data)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        logger.warning('Financial live capture unavailable', extra={'error_type':type(exc).__name__})
        raise HTTPException(502, '真实行情获取失败；请稍后重试。没有使用演示数据或成本价替代。') from exc
    quotes = {q.symbol:q for q in data.snapshot.quotes} if data.snapshot else {}
    return {'dataset_id':data.dataset_id,'conversation_id':data.conversation_id,
        'as_of':data.as_of,'snapshot_id':data.snapshot.snapshot_id if data.snapshot else None,
        'symbols':[h.symbol for h in data.snapshot.holdings] if data.snapshot else [h.symbol for h in data.market_histories],
        'sectors':sorted({c.sector for c in data.classifications.values() if c.sector}),
        'cash':str(data.snapshot.cash) if data.snapshot else None, 'currency':'USD',
        'holdings':[{'symbol':h.symbol,'quantity':str(h.quantity),
            'price':str(quotes[h.symbol].price),'price_at':quotes[h.symbol].effective_at,
            'source':quotes[h.symbol].source} for h in data.snapshot.holdings] if data.snapshot else [],
        'limitations':data.limitations}


def _assembly(enabled=('market_investigation', 'portfolio_rebalance'), profile=None):
    if profile and profile != 'synthetic-demo-v1':
        from agent.financial_live import live_assembly
        return live_assembly(sync_session_factory, profile, enabled, require_model=bool(enabled))
    route = None
    dispatcher = build_financial_dispatcher(sync_session_factory, enabled=enabled,
        portfolio_artifact_resolver=lambda *args: route.artifact_resolver(*args))
    route = CrossMASRouter(dispatcher, ArtifactStore(sync_session_factory),
        demo_snapshot_loader, execution_profile='synthetic-demo-v1')
    return dispatcher, route


def _snapshot(dispatcher, run_id):
    try:
        return dispatcher.snapshot(run_id)
    except KeyError as exc:
        raise HTTPException(404, 'Financial run not found') from exc


def _paired(dispatcher, run_id):
    return any(relation['relation_type'] in {'combined', 'cross_admitted'}
        for relation in dispatcher.relations(run_id))


def _dispatch(run_id, paired, background):
    from workers.agent_tasks import run_agent, run_financial_pair
    task = run_financial_pair if paired else run_agent
    if os.getenv('REDIS_URL'):
        try:
            task.delay(run_id)
            return
        except Exception:
            logger.warning('Financial queue publication failed; using local background delivery', exc_info=True)
    # Sync callable runs in FastAPI's thread pool, outside the request event loop.
    background.add_task(task.run, run_id)


def _has_market_evidence(dispatcher, snapshot):
    relations = dispatcher.relations(snapshot['run_id'])
    selected = {relation['envelope'].get('causation_id') for relation in relations
        if relation['relation_type'] == 'artifact_selection'
        and relation['source_run_id'] == snapshot['run_id']}
    for relation in relations:
        envelope = relation['envelope']
        if (relation['relation_type'] != 'cross_admitted'
                or relation['target_run_id'] != snapshot['run_id']
                or envelope.get('message_type') != 'MARKET_EVIDENCE_READY'
                or not envelope.get('payload_ref')):
            continue
        try:
            ref = ArtifactRef.model_validate(envelope['payload_ref'])
            artifact = ArtifactStore(sync_session_factory).get(ref.artifact_id,
                conversation_id=snapshot['conversation_id'],
                as_of=datetime.fromisoformat(snapshot['request']['as_of']),
                schema_version=ref.schema_version)
            producer = dispatcher.snapshot(relation['source_run_id'])
            scope = {item.symbol for item in demo_snapshot_loader(snapshot['request']['portfolio_snapshot_id']).holdings}
            if (isinstance(artifact, MarketInvestigationArtifact)
                    and artifact.producing_run_id == producer['run_id']
                    and producer['mas_kind'] == 'market_investigation'
                    and artifact.symbol == producer['request']['symbol']
                    and artifact.symbol in scope
                    and artifact.as_of == datetime.fromisoformat(snapshot['request']['as_of'])
                    and (envelope['message_id'] in selected
                         or datetime.fromisoformat(envelope['deadline_at']) > datetime.now(timezone.utc))):
                return True
        except (KeyError, ValueError, AttributeError):
            continue
    return False


def _result(dispatcher, run_id):
    snapshot = _snapshot(dispatcher, run_id)
    run = dispatcher.get_run(run_id)
    artifact = ref = None
    ids = snapshot['checkpoint']['artifact_ids']
    if ids:
        if len(ids) != 1:
            raise HTTPException(409, 'Invalid final artifact references')
        ref = ArtifactRef(artifact_id=ids[0])
        as_of = datetime.fromisoformat(snapshot['request']['as_of'])
        try:
            with sync_session_factory() as session:
                row = session.get(FinancialArtifact, ref.artifact_id)
                if (row is None or row.run_id != run_id or row.mas_kind != snapshot['mas_kind']
                        or row.conversation_id != snapshot['conversation_id']
                        or row.schema_version != ref.schema_version or aware(row.as_of) != as_of):
                    raise ValueError('Artifact row ownership mismatch')
            artifact = ArtifactStore(sync_session_factory).get(ref.artifact_id,
                conversation_id=snapshot['conversation_id'], as_of=as_of,
                schema_version=ref.schema_version)
            if artifact.producing_run_id != run_id or artifact.as_of != as_of:
                raise ValueError('Artifact content ownership mismatch')
        except (KeyError, ValueError) as exc:
            raise HTTPException(409, 'Invalid immutable artifact') from exc
    limitations = list(artifact.limitations) if artifact else []
    relations = dispatcher.relations(run_id)
    if any(relation['relation_type'] == 'cross_admitted'
            and relation['target_run_id'] == run_id
            and relation['envelope'].get('message_type') == 'SYSTEM_UNAVAILABLE'
            for relation in relations):
        limitations.append('SYSTEM_UNAVAILABLE')
    if (snapshot['mas_kind'] == 'portfolio_rebalance' and snapshot['status'] in TERMINAL
            and any(r['relation_type'] == 'combined' for r in relations)
            and not _has_market_evidence(dispatcher, snapshot)):
        limitations.append('market_evidence_unavailable')
    try:
        model = MarketRunResult if snapshot['mas_kind'] == 'market_investigation' else PortfolioRunResult
        live = (snapshot['execution_profile'] or '').startswith('live-financial-v1:')
        if live:
            from agent.financial_live import load_dataset, PREFIX
            data = load_dataset(sync_session_factory, snapshot['execution_profile'][len(PREFIX):], snapshot['conversation_id'])
            limitations.extend(data.limitations)
        return model(**{key: snapshot[key] for key in
            ('run_id', 'conversation_id', 'correlation_id', 'mas_kind', 'status', 'version', 'error_code')},
            mode=run.mode, artifact_ref=ref, artifact=artifact,
            validation_outcome=artifact.status if artifact else 'pending',
            limitations=list(dict.fromkeys(limitations)), data_source='user' if live else 'demo')
    except ValueError as exc:
        raise HTTPException(409, 'Invalid financial result') from exc


def _create(payload, workflow, background):
    dataset_id = getattr(payload, 'dataset_id', None)
    profile = None
    data = None
    if dataset_id:
        from agent.financial_live import load_dataset, PREFIX
        try:
            data = load_dataset(sync_session_factory, dataset_id, payload.conversation_id)
        except KeyError as exc:
            raise HTTPException(404, '真实数据快照不存在或不属于此会话。') from exc
        except ValueError as exc:
            raise HTTPException(422, '真实数据快照无效。') from exc
        profile = PREFIX+dataset_id
        if data.workflow != workflow:
            raise HTTPException(422, '工作流与准备的数据快照不一致。')
        if payload.market and (payload.market.as_of != data.as_of or payload.market.symbol != data.market_symbol
                or payload.market.sector_benchmark != data.sector_benchmark):
            raise HTTPException(422, '调查范围或时间与真实数据快照不一致。')
        if payload.portfolio and (not data.snapshot or payload.portfolio.portfolio_snapshot_id != data.snapshot.snapshot_id
                or payload.portfolio.as_of != data.as_of):
            raise HTTPException(422, '真实持仓快照或时间不一致。')
        if payload.portfolio:
            from agent.financial_constraints import constraint_issues
            issues = constraint_issues(payload.portfolio.user_constraints, [h.symbol for h in data.snapshot.holdings])
            if issues:
                raise HTTPException(422, ' '.join(issues))
    required = {'market': (True, False), 'portfolio': (False, True), 'combined': (True, True)}[workflow]
    if (payload.market is not None, payload.portfolio is not None) != required:
        raise HTTPException(422, 'Input does not match selected workflow')
    for present, budget in ((payload.market, payload.market_budget), (payload.portfolio, payload.portfolio_budget)):
        if present and any((budget.model_calls, budget.tool_calls, budget.rounds, budget.hops, budget.followups)):
            raise HTTPException(422, 'New workflow budget counters must be zero')
    if payload.portfolio:
        snapshot = data.snapshot if data else demo_snapshot_loader(payload.portfolio.portfolio_snapshot_id)
        if (snapshot is None or (not data and payload.portfolio.portfolio_snapshot_id != DEMO_SNAPSHOT_ID)
                or snapshot.effective_at != payload.portfolio.as_of):
            raise HTTPException(422, 'Only the immutable synthetic snapshot and timepoint are supported')
        if workflow == 'combined':
            if payload.market_budget.max_hops == 0 or payload.portfolio_budget.max_hops == 0:
                raise HTTPException(422, 'Combined requires a positive hop budget for both runs')
            if payload.market.symbol not in {item.symbol for item in snapshot.holdings}:
                raise HTTPException(422, 'Market symbol is outside the synthetic snapshot')
    with sync_session_factory() as session:
        if session.get(Conversation, payload.conversation_id) is None:
            raise HTTPException(404, 'Conversation not found')
    enabled = tuple(kind for kind, present in
        (('market_investigation', payload.market), ('portfolio_rebalance', payload.portfolio)) if present)
    try:
        dispatcher, route = _assembly(enabled, profile)
    except (ValueError, KeyError) as exc:
        raise HTTPException(503, '金融模型配置缺失或已变更；请重新准备数据快照。') from exc
    try:
        pair = route.create(CrossMASRequest.model_validate(payload.model_dump(exclude={'dataset_id'})))
    except (FinancialConflict, ValueError) as exc:
        raise HTTPException(409, str(exc)) from exc
    ids = [value for value in (pair.market_run_id, pair.portfolio_run_id) if value]
    summaries = []
    for value in ids:
        snapshot = dispatcher.snapshot(value)
        summaries.append({key: snapshot[key] for key in ('run_id', 'mas_kind', 'status', 'version')})
    response = FinancialCreateResponse(conversation_id=pair.conversation_id,
        correlation_id=pair.correlation_id, market_run_id=pair.market_run_id,
        portfolio_run_id=pair.portfolio_run_id,
        runs=summaries)
    _dispatch(ids[0], workflow == 'combined', background)
    return response


@router.post('/market-investigations', status_code=202, response_model=FinancialCreateResponse)
def create_market(payload: FinancialWorkflowRequest, background: BackgroundTasks):
    return _create(payload, 'market', background)


@router.post('/portfolio-reviews', status_code=202, response_model=FinancialCreateResponse)
def create_portfolio(payload: FinancialWorkflowRequest, background: BackgroundTasks):
    return _create(payload, 'portfolio', background)


@router.post('/combined-reviews', status_code=202, response_model=FinancialCreateResponse)
def create_combined(payload: FinancialWorkflowRequest, background: BackgroundTasks):
    return _create(payload, 'combined', background)


@router.get('/runs/{run_id}', response_model=FinancialRunResponse)
def get_result(run_id: str):
    dispatcher, _ = _assembly(())
    return _result(dispatcher, run_id)


def _cancellation_peers(dispatcher, run_id, relations):
    """Only persisted Combined or exact admitted REQUEST authority grants delivery."""
    peers = set()
    for relation in relations:
        source, target = relation['source_run_id'], relation['target_run_id']
        if relation['relation_type'] == 'combined':
            peers.add(target if run_id == source else source)
        elif (relation['relation_type'] == 'cross_admitted'
                and relation['envelope'].get('message_type') == 'MARKET_EVIDENCE_REQUEST'):
            try:
                followup = dispatcher.snapshot(target)
                origin = followup['execution_authorization']
                if (not origin or origin['purpose'] != 'cross_followup'
                        or origin['source_run_id'] != source
                        or origin['request_message_id'] != relation['envelope'].get('message_id')):
                    raise ValueError('Cancellation peer has no exact follow-up authority')
                # W6 validates the complete persisted direction, endpoints,
                # correlation, profile and immutable REQUEST origin, read-only.
                dispatcher.validate_queue_eligibility(target)
            except (KeyError, ValueError) as exc:
                raise HTTPException(409, 'Invalid admitted follow-up cancellation peer') from exc
            peers.add(target if run_id == source else source)
    return sorted(peers)


def _action(run_id, payload, action, background):
    dispatcher, _ = _assembly(())
    snapshot = _snapshot(dispatcher, run_id)
    try:
        dispatcher, _ = _assembly((), snapshot['execution_profile'])
        if snapshot['execution_profile'] is None:
            raise ValueError('missing profile')
    except (KeyError, ValueError) as exc:
        raise HTTPException(409, 'Financial API execution profile is unavailable') from exc
    relations = dispatcher.relations(run_id)
    combined = next((r for r in relations if r['relation_type'] == 'combined'), None)
    cancellation_peers = _cancellation_peers(dispatcher, run_id, relations) if action == 'cancel' else []
    if action in {'approve', 'resume'} and combined and snapshot['mas_kind'] == 'portfolio_rebalance':
        if dispatcher.snapshot(combined['source_run_id'])['status'] not in TERMINAL:
            raise HTTPException(409, 'Paired Market must resolve before Portfolio approval or resume')
    try:
        getattr(dispatcher, action)(run_id, payload.expected_version)
    except FinancialConflict as exc:
        raise HTTPException(409, str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(404, 'Financial run not found') from exc
    if action in {'approve', 'resume'}:
        _dispatch(run_id, _paired(dispatcher, run_id), background)
    elif action == 'cancel':
        for peer in cancellation_peers:
            if dispatcher.snapshot(peer)['status'] not in TERMINAL:
                _dispatch(peer, True, background)
    return _result(dispatcher, run_id)


@router.post('/runs/{run_id}/approve', response_model=FinancialRunResponse)
def approve(run_id: str, payload: FinancialRunAction, background: BackgroundTasks):
    return _action(run_id, payload, 'approve', background)


@router.post('/runs/{run_id}/pause', response_model=FinancialRunResponse)
def pause(run_id: str, payload: FinancialRunAction, background: BackgroundTasks):
    return _action(run_id, payload, 'pause', background)


@router.post('/runs/{run_id}/resume', response_model=FinancialRunResponse)
def resume(run_id: str, payload: FinancialRunAction, background: BackgroundTasks):
    return _action(run_id, payload, 'resume', background)


@router.post('/runs/{run_id}/cancel', response_model=FinancialRunResponse)
def cancel(run_id: str, payload: FinancialRunAction, background: BackgroundTasks):
    return _action(run_id, payload, 'cancel', background)
