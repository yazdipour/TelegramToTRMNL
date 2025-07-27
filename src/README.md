# Dev Doc

## How to TRMNL

Create your Plugin at [TRMNL](https://usetrmnl.com/integrations/private-plugin) and get your Plugin ID.

## How to setup the bot

### Create your Telegram Bot

Follow instructions at [Telegram Bot API](https://core.telegram.org/bots#6-botfather) to create your bot and get the token.

### Prepare your .env file

Create a `.env` file in the root directory of the project with the following content:

```
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TRMNL_PLUGIN_UUID=your_trmnl_plugin_uuid
TRMNL_API_BASE=https://usetrmnl.com/api
```

### Using Docker Compose (recommended)

```
docker compose build            # Build once
docker compose up -d            # Starts with .env
docker compose logs -f trmnl-teb      # to check the logs
```

### Build Docker

`docker build -t trmnl-teb .`

### Run Docker Image

`docker run --rm --env-file .env trmnl-teb`
