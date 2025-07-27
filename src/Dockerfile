FROM ghcr.io/astral-sh/uv:python3.12-alpine

WORKDIR /app

# Install system dependencies for PDF processing and EPUB conversion
RUN apk add --no-cache \
    poppler-utils \
    pandoc \
    py3-weasyprint \
    fontconfig \
    ttf-liberation \
    ttf-dejavu \
    && rm -rf /var/cache/apk/*

# Update font cache
RUN fc-cache -fv

COPY pyproject.toml ./
RUN uv pip install --system --no-cache-dir -r <(uv pip compile pyproject.toml)

COPY . .

CMD ["uv", "run", "main.py"]
