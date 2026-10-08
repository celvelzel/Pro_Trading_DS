"""Financial lifecycle and persistence authority using AgentRun CAS and fencing."""
from __future__ import annotations
import asyncio
import hashlib
import json
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Callable
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from db.models.agent import AgentRun, AgentEvent, Conversation, ToolCall, ToolResult
from db.models.financial_mas import FinancialRun, FinancialInvocation, FinancialArtifact, FinancialRelation
from agent.tools.registry import ToolRegistry
from agent.tools.executor import ToolExecutor
from agent.schemas import ToolResultEnvelope
from .contracts import *
from .runtime import WorkflowRegistry, SpecialistInvoker, workflow_registry, financial_tool_registry

TERMINAL = frozenset({'completed', 'failed', 'cancelled', 'expired'})


def utcnow():
    return datetime.now(timezone.utc)


def aware(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class FinancialConflict(RuntimeError):
    status_code = 409


class BudgetExhausted(RuntimeError):
    code = 'budget_exhausted'


class RunInterrupted(FinancialConflict):
    pass


class _NoClaim(Exception):
    """Rollback a duplicate/no-op delivery without changing its persisted version."""


class _ExistingRelation(Exception):
    def __init__(self, snapshot):
        self.snapshot = snapshot


class FinancialMASDispatcher:
    def __init__(self, session_factory: Callable, drivers: WorkflowRegistry | None = None, tools: ToolRegistry | None = None, *, clock=utcnow, lease_seconds=30):
        if lease_seconds <= 0:
            raise ValueError('lease_seconds must be positive')
        self.sessions = session_factory
        self.drivers = drivers if drivers is not None else workflow_registry
        self.tools = tools if tools is not None else financial_tool_registry
        self.clock = clock
        self.lease_seconds = lease_seconds

    def is_financial(self, run_id: str) -> bool:
        with self.sessions() as session:
            return session.get(FinancialRun, run_id) is not None

    def create(self, conversation_id: str, request: MarketInvestigationRequest | PortfolioReviewRequest, *, idempotency_key: str, mode='review', budget: RunBudget | None = None, correlation_id: str | None = None, _retry_parent_id: str | None = None) -> AgentRun:
        if mode not in {'review', 'auto'}:
            raise ValueError('invalid mode')
        kind = 'market_investigation' if isinstance(request, MarketInvestigationRequest) else 'portfolio_rebalance'
        self.drivers.get(kind)  # Disabled/unregistered workflow cannot create a queued run.
        limits = (budget or RunBudget()).model_copy(deep=True)
        if any((limits.model_calls, limits.tool_calls, limits.rounds, limits.hops, limits.followups)):
            raise ValueError('new run budget counters must be zero')
        if isinstance(request, MarketInvestigationRequest):
            limits.max_model_calls = min(limits.max_model_calls, request.max_llm_calls)
        data = request.model_dump(mode='json')
        creation_inputs = {'mas_kind': kind, 'request': data, 'mode': mode,
                           'budget': limits.model_dump(mode='json'),
                           'requested_correlation_id': correlation_id,
                           'retry_parent_id': _retry_parent_id}
        with self.sessions() as session:
            existing = session.scalar(select(FinancialRun).where(FinancialRun.conversation_id == conversation_id, FinancialRun.idempotency_key == idempotency_key))
            if existing:
                if existing.creation_inputs != creation_inputs:
                    raise FinancialConflict('idempotency key has different input')
                if _retry_parent_id is not None and session.get(AgentRun, existing.run_id).parent_run_id != _retry_parent_id:
                    raise FinancialConflict('retry key belongs to an existing non-retry run')
                return self._detach(session, session.get(AgentRun, existing.run_id))
            if session.get(Conversation, conversation_id) is None:
                raise ValueError('conversation does not exist')
            run = AgentRun(id=str(uuid.uuid4()), conversation_id=conversation_id, parent_run_id=_retry_parent_id, status='queued', mode=mode, goal=f'{kind} read-only analysis', version=1, checkpoint={})
            session.add(run)
            session.flush()
            state = MarketState() if kind == 'market_investigation' else PortfolioState()
            meta = FinancialRun(run_id=run.id, conversation_id=conversation_id, mas_kind=kind, idempotency_key=idempotency_key, correlation_id=correlation_id if correlation_id is not None else str(uuid.uuid4()), request=data, creation_inputs=creation_inputs, budget=limits.model_dump(), checkpoint=Checkpoint(state=state).model_dump(mode='json'), active_seconds=0, next_event_seq=1)
            session.add(meta)
            self._event(session, run, meta, 'mas.created', {'mas_kind': kind})
            if _retry_parent_id is not None:
                self._event(session, run, meta, 'mas.retry_linked', {'parent_run_id': _retry_parent_id})
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                existing = session.scalar(select(FinancialRun).where(FinancialRun.conversation_id == conversation_id, FinancialRun.idempotency_key == idempotency_key))
                if existing is None or existing.creation_inputs != creation_inputs:
                    raise FinancialConflict('concurrent creation conflict')
                if _retry_parent_id is not None and session.get(AgentRun, existing.run_id).parent_run_id != _retry_parent_id:
                    raise FinancialConflict('concurrent retry key conflict')
                return self._detach(session, session.get(AgentRun, existing.run_id))
            return self._detach(session, run)

    @staticmethod
    def _detach(session, run):
        session.refresh(run)
        session.expunge(run)
        return run

    def snapshot(self, run_id: str) -> dict:
        with self.sessions() as session:
            run, meta = self._load(session, run_id)
            return {'run_id': run.id, 'conversation_id': run.conversation_id, 'status': run.status, 'version': run.version, 'mas_kind': meta.mas_kind, 'correlation_id': meta.correlation_id, 'request': meta.request, 'checkpoint': meta.checkpoint, 'budget': meta.budget, 'active_seconds': self._elapsed(meta), 'final_answer': run.final_answer, 'error_code': run.error_code}

    def _load(self, session, run_id):
        run = session.get(AgentRun, run_id)
        meta = session.get(FinancialRun, run_id)
        if run is None or meta is None:
            raise KeyError(run_id)
        return run, meta

    def _elapsed(self, meta):
        return meta.active_seconds + (max(0, (self.clock() - aware(meta.active_since)).total_seconds()) if meta.active_since else 0)

    @contextmanager
    def _mutation(self, run_id, *, version=None, token=None):
        with self.sessions() as session:
            run, meta = self._load(session, run_id)
            expected = run.version if version is None else version
            if expected != run.version or (token is not None and (meta.claim_token != token or not meta.lease_until or aware(meta.lease_until) <= self.clock())):
                raise FinancialConflict('stale version or worker claim')
            # The write obtains the DB row lock (SQLite write serialization / PostgreSQL row lock).
            changed = session.execute(update(AgentRun).where(AgentRun.id == run_id, AgentRun.version == expected).values(version=expected + 1), execution_options={'synchronize_session': False}).rowcount
            if changed != 1:
                session.rollback()
                raise FinancialConflict('stale version')
            # Reload metadata after the authority lock; another intervention may have fenced us.
            session.refresh(meta)
            if token is not None and (meta.claim_token != token or aware(meta.lease_until) <= self.clock()):
                session.rollback()
                raise FinancialConflict('stale worker claim')
            run.version = expected + 1
            try:
                yield session, run, meta
                session.commit()
            except BaseException:
                session.rollback()
                raise

    def _event(self, session, run, meta, event_type, payload):
        session.add(AgentEvent(run_id=run.id, conversation_id=run.conversation_id, seq=meta.next_event_seq, schema_version=1, event_type=event_type, request_id=str(uuid.uuid4()), payload=payload))
        meta.next_event_seq += 1

    def _stop_clock(self, meta):
        meta.active_seconds = self._elapsed(meta)
        meta.active_since = None

    def _release(self, meta):
        meta.claim_token = None
        meta.lease_until = None

    def _intervene(self, run_id, version, action):
        with self._mutation(run_id, version=version) as (session, run, meta):
            if run.status in TERMINAL:
                raise FinancialConflict('run is terminal')
            if action == 'cancel':
                self._stop_clock(meta)
                run.status = 'cancelled'
            elif action == 'pause':
                if run.status == 'paused':
                    raise FinancialConflict('already paused')
                meta.resume_phase = run.status
                self._stop_clock(meta)
                run.status = 'paused'
            elif action == 'resume':
                if run.status != 'paused':
                    raise FinancialConflict('run is not paused')
                run.status = meta.resume_phase or 'queued'
                meta.resume_phase = None
            elif action == 'approve':
                if run.status != 'waiting_user':
                    raise FinancialConflict('run is not waiting for approval')
                run.status = 'executing'
            self._release(meta)  # User intervention fences any pending external call.
            self._event(session, run, meta, 'mas.' + action, {'status': run.status})
        return self.get_run(run_id)

    def approve(self, run_id: str, version: int):
        return self._intervene(run_id, version, 'approve')

    def pause(self, run_id: str, version: int):
        return self._intervene(run_id, version, 'pause')

    def resume(self, run_id: str, version: int):
        return self._intervene(run_id, version, 'resume')

    def cancel(self, run_id: str, version: int):
        return self._intervene(run_id, version, 'cancel')

    def get_run(self, run_id):
        with self.sessions() as session:
            run, _ = self._load(session, run_id)
            return self._detach(session, run)

    @staticmethod
    def _relation_snapshot(row):
        return {'relation_id': row.id, 'conversation_id': row.conversation_id,
                'source_run_id': row.source_run_id, 'target_run_id': row.target_run_id,
                'correlation_id': row.correlation_id, 'relation_type': row.relation_type,
                'idempotency_key': row.idempotency_key, 'envelope': row.envelope}

    def relations(self, run_id: str) -> list[dict]:
        with self.sessions() as session:
            self._load(session, run_id)
            rows = session.scalars(select(FinancialRelation).where(
                (FinancialRelation.source_run_id == run_id) | (FinancialRelation.target_run_id == run_id)
            ).order_by(FinancialRelation.id)).all()
            return [self._relation_snapshot(row) for row in rows]

    def link_runs(self, source_run_id: str, target_run_id: str, *, version: int,
                  relation_type: str, idempotency_key: str,
                  envelope: CrossMASEnvelope | None = None) -> dict:
        if source_run_id == target_run_id:
            raise ValueError('relation needs distinct runs')
        if not relation_type or len(relation_type) > 32 or not idempotency_key or len(idempotency_key) > 128:
            raise ValueError('invalid relation identifiers')
        if envelope is not None:
            envelope = CrossMASEnvelope.model_validate(envelope.model_dump())
        data = envelope.model_dump(mode='json') if envelope else {}
        try:
            with self._mutation(source_run_id, version=version) as (session, source, source_meta):
                target, target_meta = self._load(session, target_run_id)
                if source.conversation_id != target.conversation_id:
                    raise ValueError('cross-conversation relation denied')
                if source_meta.correlation_id != target_meta.correlation_id:
                    raise ValueError('relation correlation mismatch')
                if source_meta.mas_kind == target_meta.mas_kind:
                    raise ValueError('cross-MAS relation requires different kinds')
                if self._request(source_meta).as_of != self._request(target_meta).as_of:
                    raise ValueError('relation timepoint mismatch')
                existing = session.scalar(select(FinancialRelation).where(
                    FinancialRelation.conversation_id == source.conversation_id,
                    FinancialRelation.idempotency_key == idempotency_key))
                if existing:
                    if (existing.source_run_id, existing.target_run_id, existing.relation_type, existing.envelope) != (source_run_id, target_run_id, relation_type, data):
                        raise FinancialConflict('relation key has different payload')
                    raise _ExistingRelation(self._relation_snapshot(existing))
                if source.status in TERMINAL and envelope and envelope.message_type.endswith('_REQUEST'):
                    raise FinancialConflict('terminal run cannot issue new requests')
                if envelope:
                    if envelope.run_id != source_run_id or envelope.origin_mas != source_meta.mas_kind or envelope.target_mas != target_meta.mas_kind:
                        raise ValueError('envelope ownership/kind mismatch')
                    if envelope.correlation_id != source_meta.correlation_id or envelope.idempotency_key != idempotency_key:
                        raise ValueError('envelope correlation/key mismatch')
                    if envelope.as_of != self._request(source_meta).as_of:
                        raise ValueError('envelope timepoint mismatch')
                    if envelope.deadline_at <= self.clock() or envelope.created_at > self.clock():
                        raise ValueError('envelope is expired or created in the future')
                    if envelope.payload_ref:
                        artifact = session.get(FinancialArtifact, envelope.payload_ref.artifact_id)
                        if artifact is None or artifact.run_id != source_run_id or artifact.conversation_id != source.conversation_id:
                            raise ValueError('artifact ownership mismatch')
                        if artifact.schema_version != envelope.payload_ref.schema_version or aware(artifact.as_of) != envelope.as_of:
                            raise ValueError('artifact version/timepoint mismatch')
                        target_request = self._request(target_meta)
                        if isinstance(target_request, MarketInvestigationRequest) and target_request.symbol not in artifact.symbols:
                            raise ValueError('artifact target symbol mismatch')
                row = FinancialRelation(id=str(uuid.uuid4()), conversation_id=source.conversation_id,
                    source_run_id=source_run_id, target_run_id=target_run_id,
                    correlation_id=source_meta.correlation_id, relation_type=relation_type,
                    idempotency_key=idempotency_key, envelope=data)
                session.add(row)
                self._event(session, source, source_meta, 'cross_mas.linked',
                    {'relation_id': row.id, 'target_run_id': target_run_id, 'relation_type': relation_type})
                result = self._relation_snapshot(row)
            return result
        except _ExistingRelation as existing:
            return existing.snapshot

    def retry(self, run_id: str, version: int, *, idempotency_key: str):
        with self.sessions() as session:
            run, meta = self._load(session, run_id)
            if run.version != version or run.status not in TERMINAL:
                raise FinancialConflict('retry needs current terminal run')
            request = self._request(meta)
            budget = RunBudget.model_validate(meta.budget).model_copy(update={'model_calls': 0, 'tool_calls': 0, 'rounds': 0, 'hops': 0, 'followups': 0})
            conversation_id, mode, correlation_id = run.conversation_id, run.mode, meta.correlation_id
        with self.sessions() as session:
            existing = session.scalar(select(FinancialRun).where(FinancialRun.conversation_id == conversation_id, FinancialRun.idempotency_key == idempotency_key))
            if existing:
                existing_run = session.get(AgentRun, existing.run_id)
                if existing_run.parent_run_id != run_id:
                    raise FinancialConflict('retry key belongs to an existing non-retry run')
        child = self.create(conversation_id, request, idempotency_key=idempotency_key, mode=mode, budget=budget, correlation_id=correlation_id, _retry_parent_id=run_id)
        if child.id == run_id:
            raise FinancialConflict('retry must create a different run')
        if child.parent_run_id != run_id:
            raise FinancialConflict('retry key belongs to another parent')
        return self.get_run(child.id)

    @staticmethod
    def _request(meta):
        return (MarketInvestigationRequest if meta.mas_kind == 'market_investigation' else PortfolioReviewRequest).model_validate(meta.request)

    async def start(self, run_id: str) -> AgentRun:
        token = str(uuid.uuid4())
        try:
            with self._mutation(run_id) as (session, run, meta):
                if run.status in TERMINAL or run.status in {'paused', 'waiting_user'}:
                    raise _NoClaim()
                if meta.claim_token and meta.lease_until and aware(meta.lease_until) > self.clock():
                    raise _NoClaim()
                if run.mode == 'review' and run.status in {'queued', 'planning'}:
                    run.status = 'waiting_user'
                    self._stop_clock(meta)
                    self._event(session, run, meta, 'mas.review_required', {})
                else:
                    run.status = 'executing'
                    meta.claim_token = token
                    meta.lease_until = self.clock() + timedelta(seconds=self.lease_seconds)
                    if meta.active_since is None:
                        meta.active_since = self.clock()
                    self._event(session, run, meta, 'mas.started', {})
                kind = meta.mas_kind
            if self.get_run(run_id).status == 'waiting_user':
                return self.get_run(run_id)
            driver = self.drivers.get(kind)
            context = RuntimeContext(self, run_id, token, driver)
            context.check_budget()
            artifact = await driver.execute(context, context.state)
            if artifact is not None:
                context.complete(artifact)
            else:
                # Driver must explicitly preserve state; release an unfinished delivery.
                with self._mutation(run_id, token=token) as (session, run, meta):
                    self._release(meta)
                    self._event(session, run, meta, 'mas.checkpoint', {})
        except _NoClaim:
            pass
        except FinancialConflict:
            # Cancel/pause/concurrent delivery owns the result now; stale worker cannot write.
            pass
        except Exception as exc:
            try:
                with self._mutation(run_id, token=token) as (session, run, meta):
                    run.status = 'failed'
                    run.error_code = getattr(exc, 'code', 'financial_execution_failed')
                    self._stop_clock(meta)
                    self._release(meta)
                    self._event(session, run, meta, 'mas.failure', {'code': run.error_code})
            except FinancialConflict:
                pass
        return self.get_run(run_id)


class RuntimeContext:
    def __init__(self, dispatcher, run_id, token, driver):
        self.dispatcher, self.run_id, self.token, self.driver = dispatcher, run_id, token, driver
        self.invoker = SpecialistInvoker(driver.specialists)
        with dispatcher.sessions() as session:
            _, meta = dispatcher._load(session, run_id)
            self.request = dispatcher._request(meta)
            self.state = Checkpoint.model_validate(meta.checkpoint).state
            self.conversation_id = meta.conversation_id

    def _guard(self, run, meta):
        if run.status != 'executing':
            raise RunInterrupted('run is no longer executing')
        if self.dispatcher._elapsed(meta) >= RunBudget.model_validate(meta.budget).max_active_seconds:
            raise BudgetExhausted('active deadline exhausted')

    def check_budget(self):
        with self.dispatcher._mutation(self.run_id, token=self.token) as (_, run, meta):
            self._guard(run, meta)

    async def external(self, awaitable):
        pending = asyncio.ensure_future(awaitable)
        try:
            while True:
                with self.dispatcher.sessions() as session:
                    run, meta = self.dispatcher._load(session, self.run_id)
                    self._guard(run, meta)
                    remaining = RunBudget.model_validate(meta.budget).max_active_seconds - self.dispatcher._elapsed(meta)
                done, _ = await asyncio.wait({pending}, timeout=min(remaining, self.dispatcher.lease_seconds / 3))
                if done:
                    return pending.result()
                # Renew only while we still own the claim; pause/cancel fences this renewal.
                with self.dispatcher._mutation(self.run_id, token=self.token) as (_, run, meta):
                    self._guard(run, meta)
                    meta.lease_until = self.dispatcher.clock() + timedelta(seconds=self.dispatcher.lease_seconds)
        finally:
            if not pending.done():
                pending.cancel()
                await asyncio.gather(pending, return_exceptions=True)

    def reserve(self, kind, role, invocation_key, *, tool_name=None, payload=None, input_hash=None):
        if input_hash is None:
            input_hash = hashlib.sha256(json.dumps({'tool': tool_name, 'payload': payload}, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        with self.dispatcher._mutation(self.run_id, token=self.token) as (session, run, meta):
            self._guard(run, meta)
            row = session.scalar(select(FinancialInvocation).where(FinancialInvocation.run_id == self.run_id, FinancialInvocation.invocation_key == invocation_key))
            if row and (row.kind != kind or row.role != role or row.input_hash != input_hash):
                raise FinancialConflict('invocation key changes role, kind or input')
            if row and row.status == 'succeeded':
                return row.output
            budget = RunBudget.model_validate(meta.budget)
            counter = 'model_calls' if kind == 'model' else 'tool_calls'
            if getattr(budget, counter) >= getattr(budget, 'max_' + counter):
                raise BudgetExhausted(counter + ' exhausted')
            setattr(budget, counter, getattr(budget, counter) + 1)
            meta.budget = budget.model_dump()
            setattr(run, counter, getattr(budget, counter))
            if row:
                row.attempts += 1
                row.status = 'reserved'
                row.error_code = None
            else:
                row = FinancialInvocation(run_id=self.run_id, invocation_key=invocation_key, role=role, kind=kind, input_hash=input_hash, status='reserved', attempts=1)
                session.add(row)
            if kind == 'tool':
                call_id = str(uuid.uuid4())
                call = ToolCall(id=call_id, call_id=call_id, run_id=self.run_id, tool_name=tool_name, status='running', input_data=payload, request_id=str(uuid.uuid4()))
                session.add(call)
                session.flush()
                row.tool_call_id = call.id
            self.dispatcher._event(session, run, meta, 'mas.invoked', {'role': role, 'kind': kind, 'invocation_key': invocation_key})
        return None

    def record_result(self, invocation_key, output):
        with self.dispatcher._mutation(self.run_id, token=self.token) as (session, run, meta):
            self._guard(run, meta)
            row = session.scalar(select(FinancialInvocation).where(FinancialInvocation.run_id == self.run_id, FinancialInvocation.invocation_key == invocation_key))
            if not row or row.status != 'reserved':
                raise FinancialConflict('invocation is not reserved')
            row.status, row.output = 'succeeded', output
            if row.kind == 'tool':
                envelope = ToolResultEnvelope.model_validate(output)
                call = session.get(ToolCall, row.tool_call_id)
                call.status = envelope.status.value
                call.error_code = envelope.error.code if envelope.error else None
                session.add(ToolResult(tool_call_id=call.id, data=envelope.data, citations=[c.model_dump(mode='json') if isinstance(c, BaseModel) else c for c in envelope.citations], duration_ms=envelope.duration_ms, cached=envelope.cached))
            event = {'role': row.role, 'kind': row.kind, 'invocation_key': invocation_key}
            if row.kind == 'model':
                event.update({key: output[key] for key in ('action', 'summary', 'evidence_ids', 'missing_checks') if key in output})
            self.dispatcher._event(session, run, meta, 'mas.returned', event)

    def record_failure(self, invocation_key, code):
        with self.dispatcher._mutation(self.run_id, token=self.token) as (session, run, meta):
            row = session.scalar(select(FinancialInvocation).where(FinancialInvocation.run_id == self.run_id, FinancialInvocation.invocation_key == invocation_key))
            if row:
                row.status, row.error_code = 'failed', code
                if row.tool_call_id:
                    call = session.get(ToolCall, row.tool_call_id)
                    call.status, call.error_code = 'failed', code
            self.dispatcher._event(session, run, meta, 'mas.invocation_failed', {'invocation_key': invocation_key, 'code': code})

    async def invoke(self, role: str, invocation_key: str, task: BaseModel) -> BaseModel:
        return await self.invoker.invoke(self, role, invocation_key, task)

    async def tool(self, role: str, invocation_key: str, name: str, payload: BaseModel):
        # Also enforce permission here: drivers cannot bypass SpecialistInvoker.tool.
        spec = self.driver.specialists.get(role)
        tool = self.dispatcher.tools.get(name)
        if name not in spec.allowed_tools or not tool.read_only or tool.side_effect:
            raise PermissionError('unauthorized financial tool')
        data = payload.model_dump(mode='json')
        cached = self.reserve('tool', role, invocation_key, tool_name=name, payload=data)
        if cached is not None:
            return ToolResultEnvelope.model_validate(cached)
        try:
            with self.dispatcher.sessions() as session:
                invocation = session.scalar(select(FinancialInvocation).where(FinancialInvocation.run_id == self.run_id, FinancialInvocation.invocation_key == invocation_key))
                call = session.get(ToolCall, invocation.tool_call_id)
                call_id = call.call_id
            result = await self.external(ToolExecutor(self.dispatcher.tools).execute(name, data, call_id=call_id))
            self.record_result(invocation_key, result.model_dump(mode='json'))
            return result
        except Exception as exc:
            self.record_failure(invocation_key, getattr(exc, 'code', 'tool_failed'))
            raise

    def tool_result_ref(self, invocation_key: str) -> ToolResultRef:
        with self.dispatcher.sessions() as session:
            invocation = session.scalar(select(FinancialInvocation).where(
                FinancialInvocation.run_id == self.run_id,
                FinancialInvocation.invocation_key == invocation_key))
            if invocation is None or invocation.kind != 'tool' or invocation.status != 'succeeded':
                raise KeyError('persisted tool result not found in run')
            call = session.get(ToolCall, invocation.tool_call_id)
            if call is None or call.run_id != self.run_id:
                raise KeyError('tool call not found in run')
            result = session.scalar(select(ToolResult).where(ToolResult.tool_call_id == call.id))
            if result is None:
                raise KeyError('persisted tool result not found in run')
            return ToolResultRef(run_id=self.run_id, tool_call_id=call.id,
                                 tool_result_id=result.id, tool_name=call.tool_name,
                                 tool_version=call.tool_version)

    def checkpoint(self, state: MarketState | PortfolioState, *, action='handoff', evidence_ids: list[str] | None = None):
        expected = 'market_investigation' if isinstance(state, MarketState) else 'portfolio_rebalance'
        if expected != self.driver.kind:
            raise ValueError('wrong domain state')
        state = type(state).model_validate(state.model_dump())
        with self.dispatcher._mutation(self.run_id, token=self.token) as (session, run, meta):
            self._guard(run, meta)
            cp = Checkpoint.model_validate(meta.checkpoint)
            cp.state = state
            meta.checkpoint = cp.model_dump(mode='json')
            run.checkpoint = meta.checkpoint
            self.dispatcher._event(session, run, meta, 'mas.' + action, {'phase': state.phase, 'evidence_ids': evidence_ids or []})
        self.state = state

    def consume_budget(self, counter: str):
        if counter not in {'rounds', 'hops', 'followups'}:
            raise ValueError('unsupported budget counter')
        with self.dispatcher._mutation(self.run_id, token=self.token) as (session, run, meta):
            self._guard(run, meta)
            budget = RunBudget.model_validate(meta.budget)
            if getattr(budget, counter) >= getattr(budget, 'max_' + counter):
                raise BudgetExhausted(counter + ' exhausted')
            setattr(budget, counter, getattr(budget, counter) + 1)
            meta.budget = budget.model_dump()
            self.dispatcher._event(session, run, meta, 'mas.budget_reserved', {'counter': counter})

    def complete(self, artifact):
        artifact = type(artifact).model_validate(artifact.model_dump())
        expected = MarketInvestigationArtifact if self.driver.kind == 'market_investigation' else PortfolioProposalArtifact
        if not isinstance(artifact, expected) or artifact.producing_run_id != self.run_id or artifact.as_of != self.request.as_of:
            raise ValueError('artifact ownership or timepoint mismatch')
        if isinstance(artifact, MarketInvestigationArtifact) and artifact.symbol != self.request.symbol:
            raise ValueError('artifact requested symbol mismatch')
        if isinstance(artifact, PortfolioProposalArtifact) and artifact.snapshot_id != self.request.portfolio_snapshot_id:
            raise ValueError('artifact requested holdings snapshot mismatch')
        with self.dispatcher._mutation(self.run_id, token=self.token) as (session, run, meta):
            self._guard(run, meta)
            from .artifact_store import ArtifactStore
            stored = ArtifactStore.put_in_transaction(session, run, meta, 'final', artifact)
            cp = Checkpoint.model_validate(meta.checkpoint)
            if stored.id not in cp.artifact_ids:
                cp.artifact_ids.append(stored.id)
            meta.checkpoint = cp.model_dump(mode='json')
            run.checkpoint = meta.checkpoint
            run.status = 'completed'
            run.final_answer = artifact.model_dump_json()
            self.dispatcher._stop_clock(meta)
            self.dispatcher._release(meta)
            self.dispatcher._event(session, run, meta, 'mas.artifact_created', {'artifact_id': stored.id, 'schema_version': 1})
            self.dispatcher._event(session, run, meta, 'mas.completed', {'artifact_id': stored.id})
