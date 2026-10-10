"""Read-only durable origin and admitted REQUEST authority checks (ADR-0005)."""
from sqlalchemy import select
from pydantic import ValidationError
from db.models.financial_mas import FinancialRelation
from .contracts import FinancialExecutionAuthorization, CrossMASEnvelope


class FinancialExecutionAuthorizationError(ValueError):
    code = 'financial_execution_authorization_denied'
    status_code = 409


class FinancialExecutionExpired(RuntimeError):
    code = 'cross_execution_expired'


def origin(meta):
    inputs = meta.creation_inputs
    if 'execution_authorization' not in inputs:
        return None
    # Explicit null/malformed stored JSON cannot silently downgrade to legacy.
    try:
        return FinancialExecutionAuthorization.model_validate(inputs['execution_authorization'])
    except (ValidationError, TypeError, ValueError) as exc:
        raise FinancialExecutionAuthorizationError('invalid persisted execution authorization') from exc


def admitted_deadline(dispatcher, session, run, meta):
    authorization = origin(meta)
    if authorization is None or authorization.purpose == 'independent':
        return None
    rows = session.scalars(select(FinancialRelation).where(
        FinancialRelation.conversation_id == run.conversation_id)).all()
    matches = [row for row in rows if row.envelope.get('message_id') == authorization.request_message_id]
    if len(matches) != 1:
        raise FinancialExecutionAuthorizationError('exact admitted REQUEST is missing or ambiguous')
    row = matches[0]
    try:
        envelope = CrossMASEnvelope.model_validate(row.envelope)
        source, source_meta = dispatcher._load(session, authorization.source_run_id)
        valid = (row.relation_type == 'cross_admitted'
            and row.source_run_id == authorization.source_run_id
            and row.target_run_id == run.id
            and row.conversation_id == run.conversation_id == source.conversation_id
            == meta.conversation_id == source_meta.conversation_id
            and row.correlation_id == meta.correlation_id == source_meta.correlation_id == envelope.correlation_id
            and source_meta.mas_kind == envelope.origin_mas == 'portfolio_rebalance'
            and meta.mas_kind == envelope.target_mas == 'market_investigation'
            and envelope.run_id == source.id
            and envelope.message_type == 'MARKET_EVIDENCE_REQUEST'
            and envelope.causation_id is None
            and envelope.idempotency_key == row.idempotency_key
            and source_meta.creation_inputs.get('execution_profile') == meta.creation_inputs.get('execution_profile')
            and envelope.as_of == dispatcher._request(meta).as_of == dispatcher._request(source_meta).as_of
            and envelope.created_at <= dispatcher.clock())
    except (KeyError, ValidationError, TypeError, ValueError) as exc:
        raise FinancialExecutionAuthorizationError('invalid admitted REQUEST authority') from exc
    if not valid:
        raise FinancialExecutionAuthorizationError('admitted REQUEST does not authorize this exact target')
    return envelope.deadline_at


def validate_legacy_queue(dispatcher, session, run, meta):
    """At most 32 immutable retry edges; root must be uncorrelated legacy creation."""
    seen = set()
    edges = 0
    identity = (run.conversation_id, meta.conversation_id, meta.correlation_id,
        meta.request, meta.mas_kind, meta.creation_inputs.get('execution_profile'))
    while True:
        if run.id in seen or origin(meta) is not None:
            raise FinancialExecutionAuthorizationError('cyclic or nonlegacy retry ancestry')
        seen.add(run.id)
        if identity != (run.conversation_id, meta.conversation_id, meta.correlation_id,
                meta.request, meta.mas_kind, meta.creation_inputs.get('execution_profile')):
            raise FinancialExecutionAuthorizationError('retry ancestry identity mismatch')
        inputs = meta.creation_inputs
        if run.conversation_id != meta.conversation_id:
            raise FinancialExecutionAuthorizationError('run membership conversation mismatch')
        if (inputs.get('request') != meta.request or inputs.get('mas_kind') != meta.mas_kind
                or inputs.get('retry_parent_id') != run.parent_run_id):
            raise FinancialExecutionAuthorizationError('retry ancestry immutable input mismatch')
        if run.parent_run_id is None:
            if inputs.get('requested_correlation_id') is not None:
                raise FinancialExecutionAuthorizationError('legacy root has ambiguous explicit correlation')
            return
        if inputs.get('requested_correlation_id') != meta.correlation_id:
            raise FinancialExecutionAuthorizationError('retry inherited correlation mismatch')
        edges += 1
        if edges > 32:
            raise FinancialExecutionAuthorizationError('retry ancestry exceeds 32 edges')
        try:
            run, meta = dispatcher._load(session, run.parent_run_id)
        except KeyError as exc:
            raise FinancialExecutionAuthorizationError('retry ancestor missing') from exc
