FROM ghcr.io/astral-sh/uv:python3.12-alpine

WORKDIR /app

# Install poppler-utils for pdf2image
RUN apk add --no-cache poppler-utils

COPY pyproject.toml ./
RUN uv pip install --system --no-cache-dir -r <(uv pip compile pyproject.toml)

COPY . .

CMD ["uv", "run", "main.py"]
