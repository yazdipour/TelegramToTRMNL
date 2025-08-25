# Telegram to TRMNL Bot

A versatile Telegram bot that displays various content types on your TRMNL device. Send images, PDFs, or EPUB files and instantly view them on your TRMNL display.

![photo](photo.jpeg)

> [!WARNING]  
> This project was originally created for the [TRMNL Book Reader Hackathon](https://usetrmnl.com/blog/hackathon-book-readers-winners) but has evolved into a general-purpose content display bot. It is not intended for production use and may contain bugs or incomplete features. Use at your own risk.

## Features

- **📷 Image Support**: Send any image (JPG, PNG, GIF, etc.) and instantly display it on TRMNL
- **📄 PDF Navigation**: Send PDFs and navigate pages interactively with navigation buttons
- **📚 EPUB Support**: EPUB files are automatically converted to PDF with optimized dimensions for TRMNL display
- **🔒 User Authorization**: Control access via Telegram user IDs
- **🐳 Dockerized Deployment**: Easy deployment with `uv` for fast Python dependency management
- **⚙️ Configurable Display**: Set custom dimensions via environment variables
- **🎮 Interactive Controls**: Navigation buttons for PDF page control

![navigation](nav.jpg)

## Project Structure

- `src/main.py` — Bot entrypoint and message handlers
- `src/pdf_utils.py` — PDF page/image conversion utilities
- `src/epub_utils.py` — EPUB to PDF conversion utilities
- `src/trmnl_utils.py` — TRMNL webhook integration
- `src/bot_utils.py` — Bot utility classes and helpers
- `src/markup/` — Liquid templates
- `src/docker-compose.yml` / `Dockerfile` — Containerization

## Supported Content Types

### Images 📷
- **Formats**: JPG, PNG, GIF, WebP, and other common image formats
- **Usage**: Simply send any image to the bot
- **Result**: Image is instantly displayed on your TRMNL device

### PDF Documents 📄
- **Usage**: Send a PDF file to start reading
- **Features**: Interactive page navigation with previous/next buttons
- **Processing**: Each page is converted to an optimized image for TRMNL display

### EPUB eBooks 📚
- **Usage**: Send an EPUB file 
- **Processing**: Automatically converted to PDF format, then handled like PDFs
- **Features**: Same navigation controls as PDFs

## Quick Start to Host Your Bot

### 1. Create Your TRMNL Plugin

- Go to [TRMNL Private Plugin](https://usetrmnl.com/integrations/private-plugin) and create your plugin.
- Copy your Plugin UUID.

### 2. Create Your Telegram Bot

- Use [BotFather](https://core.telegram.org/bots#6-botfather) to create a bot and get your token
- Choose a descriptive name like "MyTRMNLBot" or "TelegramToTRMNL"

### 3. Prepare Your `.env` File

Create a `.env` file in the project root:
```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TRMNL_PLUGIN_UUID=your_trmnl_plugin_uuid
TRMNL_API_BASE=https://usetrmnl.com/api
TRMNL_WIDTH=480                 # (optional) display width in pixels, default: 480
TRMNL_HEIGHT=800                # (optional) display height in pixels, default: 800
FILTER_USER_IDS=123456,789012   # (optional) comma-separated Telegram user IDs for access control
```

### 4. Build & Run with Docker Compose (Recommended)

```fish
docker compose up -d
```

### 5. Manual Docker Build/Run

```fish
docker build -t telegram-to-trmnl .
docker run --rm --env-file .env telegram-to-trmnl
```

## Usage

1. **Start the bot**: Send `/start` to get a welcome message
2. **Get help**: Send `/help` for detailed usage instructions
3. **Send content**:
   - 📷 **Images**: Just send any image - it will appear on your TRMNL instantly
   - 📄 **PDFs**: Send a PDF file and use navigation buttons to browse pages
   - 📚 **EPUBs**: Send an EPUB file - it will be converted and displayed like a PDF
4. **Navigate PDFs**: Use the Previous/Next buttons to move between pages

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
