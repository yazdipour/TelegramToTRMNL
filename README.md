# TEBTRMNL — Telegram eBook Bot for TRMNL

A Telegram bot for reading and navigating PDF documents, with integration to the TRMNL platform for custom plugin workflows.

![photo](photo.jpeg)

## Features

- Send a PDF to the bot and navigate pages interactively
- Each page is converted to an image and can be sent to TRMNL via webhook
- User authorization via Telegram user IDs
- Dockerized deployment with `uv` for fast Python dependency management

## Project Structure

- `src/main.py` — Bot entrypoint
- `src/pdf_utils.py` — PDF page/image utilities
- `src/trmnl_utils.py` — TRMNL webhook integration
- `src/markup/` — Liquid templates
- `src/docker-compose.yml` / `Dockerfile` — Containerization

## Quick Start

### 1. Create Your TRMNL Plugin

- Go to [TRMNL Private Plugin](https://usetrmnl.com/integrations/private-plugin) and create your plugin.
- Copy your Plugin UUID.

### 2. Create Your Telegram Bot

- Use [BotFather](https://core.telegram.org/bots#6-botfather) to create a bot and get your token.

### 3. Prepare Your `.env` File

Create a `.env` file in the project root:
```
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TRMNL_PLUGIN_UUID=your_trmnl_plugin_uuid
TRMNL_API_BASE=https://usetrmnl.com/api
FILTER_USER_IDS=123456,789012   # (optional) comma-separated Telegram user IDs
```

### 4. Build & Run with Docker Compose (Recommended)

```fish
docker compose build
docker compose up -d
docker compose logs -f tebt
```

### 5. Manual Docker Build/Run

```fish
docker build -t trmnl-tebt .
docker run --rm --env-file .env trmnl-tebt
```

## Development

### Install Dependencies (with uv)

```fish
uv pip install --system --no-cache-dir -r <(uv pip compile pyproject.toml)
```

### Run Locally

```fish
uv run src/main.py
```

## License

MIT
