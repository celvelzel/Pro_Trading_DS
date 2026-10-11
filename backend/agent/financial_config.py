"""Separate financial model configuration; secrets never enter API responses."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlparse
from pydantic import BaseModel, ConfigDict, Field
from agent.llm import OpenAICompatibleModel, ModelProviderError
from agent.shared import SpecialistResult

ROOT = Path(__file__).resolve().parents[2]


class FinancialModelConfig(BaseModel):
    model_config = ConfigDict(extra='forbid')
    base_url: str = ''
    model: str = ''
    api_key: str = Field(default='', repr=False)
    timeout_seconds: float = Field(default=25, gt=0, le=60)

    @property
    def ready(self):
        parsed = urlparse(self.base_url)
        return bool(self.api_key.strip() and self.model.strip() and parsed.scheme in {'http', 'https'}
                    and parsed.hostname and not parsed.username and not parsed.password
                    and not parsed.query and not parsed.fragment)

    def identity(self):
        # Credential rotation is allowed; silently changing endpoint/model is not.
        return hashlib.sha256(json.dumps({'base_url': self.base_url, 'model': self.model,
            'timeout_seconds': self.timeout_seconds}, sort_keys=True).encode()).hexdigest()

    def provider(self):
        if not self.ready:
            raise ModelProviderError('permission_denied', '请先配置独立的金融 MAS 模型。')
        return OpenAICompatibleModel(self.base_url.rstrip('/'), self.api_key, self.model, self.timeout_seconds)


def model_config():
    path = Path(os.getenv('FINANCIAL_CONFIG_PATH', str(ROOT / 'financial-mas.json')))
    raw = {}
    if path.is_file():
        try:
            raw = json.loads(path.read_text(encoding='utf-8-sig'))
        except (ValueError, OSError) as exc:
            raise ValueError('金融 MAS 配置文件无法读取。') from exc
    for env, field in [('FINANCIAL_AI_BASE_URL', 'base_url'), ('FINANCIAL_AI_MODEL', 'model'),
                       ('FINANCIAL_AI_API_KEY', 'api_key')]:
        if env in os.environ:
            raw[field] = os.environ[env]
    try:
        return FinancialModelConfig.model_validate(raw)
    except ValueError as exc:
        raise ValueError('金融 MAS 配置格式不正确。') from exc


class FinancialRoleModel:
    """Give real providers the exact result schema without modifying legacy prompts."""
    def __init__(self, config, role):
        self.inner = config.provider()
        self.role = role

    async def complete(self, messages, *, request_id=None):
        schema = json.dumps(SpecialistResult.model_json_schema(), ensure_ascii=False)
        instructions = (f'\nReturn one JSON object conforming to this schema: {schema}. '
            f'The role must be {self.role}. Return fields directly, without Markdown. '
            'Use only supplied IDs; use empty arrays/maps when no evidence or proposal is available. '
            'Do not invent prices, classifications or returns. A verifier uses approve or reject.')
        normalized = [dict(m) for m in messages]
        normalized[0]['content'] += instructions
        return await self.inner.complete(normalized, request_id=request_id)
