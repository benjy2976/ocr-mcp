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
# La sonda habla con el propio contenedor: con TLS (decisión 0008) usa https sin
# verificar el certificado, que puede no incluir 127.0.0.1.
HEALTHCHECK --interval=30s --timeout=3s CMD ["python", "-c", "import os, ssl, urllib.request; tls = bool(os.environ.get('OCR_MCP_TLS_CERT')); scheme = 'https' if tls else 'http'; context = ssl._create_unverified_context() if tls else None; urllib.request.urlopen(f\"{scheme}://127.0.0.1:{os.environ['OCR_MCP_PORT']}/health\", timeout=2, context=context)"]
CMD ["ocr-mcp", "serve"]
