# Imagen del servidor ocr-mcp. La configuración llega por variables de entorno
# (docs/entorno.md); el estado vive en el volumen /data.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OCR_MCP_DATA_DIR=/data \
    OCR_MCP_HOST=0.0.0.0 \
    OCR_MCP_PORT=18040

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir . \
    && useradd --system --uid 10001 --home-dir /data ocrmcp \
    && mkdir -p /data && chown ocrmcp /data

USER ocrmcp
VOLUME ["/data"]
EXPOSE 18040
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request,os; urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"OCR_MCP_PORT\"]}/health', timeout=2)"
CMD ["ocr-mcp", "serve"]
