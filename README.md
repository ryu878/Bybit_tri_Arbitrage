# Bybit Triangular Arbitrage

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

## Telegram (optional)

When an arbitrage opportunity appears (net edge above threshold), the dashboard can send one message per opportunity to a Telegram chat. When the opportunity disappears, that triangle is cleared; if it appears again later, a new message is sent.

1. Create a bot with [@BotFather](https://t.me/BotFather) and get `TELEGRAM_BOT_TOKEN`.
2. Get your chat ID (e.g. send a message to the bot and open `https://api.telegram.org/bot<TOKEN>/getUpdates`).
3. In `.env` set:
   - `TELEGRAM_BOT_TOKEN=...`
   - `TELEGRAM_CHAT_ID=...`

Leave either variable empty to disable Telegram.

## Console output

The dashboard prints a table (cleared each refresh) with columns: **triangle**, **raw_edge**, **net_edge** (in bps), sorted by net edge descending, top **TOP_N** rows.
