# bybit_tri_arb

Console-based triangular arbitrage monitoring platform for Bybit Spot (monitoring only, no trading).

## Requirements

- Python 3.11
- Poetry
- Docker & docker-compose (for containerized run)
- Redis
- Configuration via `.env` (copy from `.env.example`)

## Layout

```
bybit_tri_arb/
├── pyproject.toml, poetry.lock, .env.example
├── Dockerfile, docker-compose.yml
├── core/           # config, redis_store, models
├── services/
│   ├── dashboard/  # WS client, triangles, calc, printer, main
│   └── bot/        # placeholder for future trading
└── scripts/
    └── run_dashboard.py   # entry: poetry run dashboard
```

## Setup

```bash
cp .env.example .env
# Edit .env if needed (REDIS_URL, SYMBOLS, etc.)
poetry install
```

## Run with Docker

```bash
cp .env.example .env
docker compose up --build
```

Runs Redis and the dashboard; dashboard connects to Bybit WebSocket, computes triangular arbitrage, writes snapshots to Redis, and prints a table to the console every `PRINT_EVERY_SEC` seconds.

## Run with tmux (local)

1. Start Redis (e.g. `docker compose up -d redis` or local Redis).
2. Set `REDIS_URL=redis://localhost:6379/0` in `.env` if Redis is local.
3. In tmux, run the dashboard in one pane:

```bash
tmux new -s bybit_arb
poetry run dashboard
```

Or split panes: one for Redis (e.g. `docker compose up redis`), one for `poetry run dashboard`.

## Console output

The dashboard prints a table (cleared each refresh) with columns: **triangle**, **edge_bps**, **leg1**, **leg2**, **leg3**, **end_amount**, **timestamp**, sorted by **edge_bps** descending, top **TOP_N** rows.
