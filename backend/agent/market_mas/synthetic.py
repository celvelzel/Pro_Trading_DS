"""Stateless synthetic demo policy, never a real research/model-quality claim."""
import json
from agent.llm import ModelResponse
from .driver import ROLES


class SyntheticMarketModel:
    def __init__(self, role):
        if role not in ROLES:
            raise ValueError('unknown synthetic market role')
        self.role = role

    async def complete(self, messages, *, request_id=None):
        content = messages[-1]['content']
        task = json.loads(content.removeprefix('<task_data>').removesuffix('</task_data>'))
        if task['role'] != self.role:
            raise ValueError('synthetic provider role mismatch')
        evidence = task['evidence']
        events = [e for e in evidence if e['source_type'] != 'market_tool']
        challenged = [e for e in events if any(word in (e.get('excerpt') or '').lower()
            for word in ('rumor', 'denied', 'contradict', 'unverified', 'ignore', 'instruction'))]
        checks = []
        hypotheses = []
        if self.role == 'critic':
            if challenged:
                checks = ['history']
            elif not events:
                checks = ['events']
            elif not any(f['name'].startswith('sector.') for f in task['numeric_facts']):
                checks = ['sector']
        if self.role in ('event', 'critic') and events:
            hypotheses = [{'explanation': 'Company event association',
                'support_ids': [] if challenged else [e['id'] for e in events],
                'against_ids': [e['id'] for e in challenged], 'disposition': 'unverified'}]
        return ModelResponse(kind='result', payload={'role': self.role,
            'action': 'challenge' if checks else 'finding',
            'summary': 'Synthetic demo assessment of supplied evidence; authenticity and causality unverified.',
            'evidence_ids': [e['id'] for e in evidence], 'missing_checks': checks,
            'hypotheses': hypotheses}, provider_request_id=request_id)
