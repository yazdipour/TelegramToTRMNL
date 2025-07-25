FROM ghcr.io/astral-sh/uv:alpine3.21

WORKDIR /app

# Install poppler-utils for pdf2image
RUN apk add --no-cache poppler-utils

COPY pyproject.toml ./
RUN uv pip install --system --no-cache-dir -r <(uv pip compile pyproject.toml)

COPY . .

ENV TELEGRAM_BOT_TOKEN=""

CMD ["uv", "python", "main.py"]
