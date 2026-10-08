FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/backend:/app:/app/lobster_quant

WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt
COPY lobster_quant/pyproject.toml /tmp/quant-pyproject.toml
RUN python -c "import subprocess, sys, tomllib; dependencies = tomllib.load(open('/tmp/quant-pyproject.toml', 'rb'))['project']['dependencies']; subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--no-cache-dir', *dependencies])"
COPY backend /app/backend
COPY lobster_quant /app/lobster_quant
COPY alembic.ini /app/alembic.ini

RUN useradd --create-home --uid 10001 app \
    && mkdir -p /app/data/documents \
    && chown -R app:app /app
USER app
WORKDIR /app/backend

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
