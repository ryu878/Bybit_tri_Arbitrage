FROM python:3.11-slim

WORKDIR /app

ENV POETRY_VERSION=1.7.1
ENV POETRY_VIRTUALENVS_CREATE=false

RUN pip install --no-cache-dir "poetry==${POETRY_VERSION}"

COPY pyproject.toml poetry.lock* ./

RUN poetry install --no-interaction --no-ansi

COPY . .

CMD ["poetry", "run", "dashboard"]
