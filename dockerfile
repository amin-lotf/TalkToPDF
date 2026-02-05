FROM python:3.11-slim-bookworm

WORKDIR /app




RUN apt-get update -o Acquire::Retries=5 \
 && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/*

RUN pip install -U uv



ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"



COPY pyproject.toml  uv.lock .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-dev

COPY . /app

RUN uv sync --no-editable --locked --no-dev



CMD ["talk"]

