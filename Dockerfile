FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    RUNNER_BACKEND=docker \
    RUNNER_IMAGE=agent-eval-runner:local \
    DATABASE_PATH=/app/data/evaluations.db

RUN apt-get update \
    && apt-get install -y --no-install-recommends docker-cli \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

EXPOSE 8000
HEALTHCHECK --interval=20s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"

CMD ["uvicorn", "agent_eval.main:app", "--host", "0.0.0.0", "--port", "8000"]
