# Entorno

Única fuente de las variables de entorno; el `README.md` la enlaza. Las lee y
valida `src/ocr_mcp/config.py` al arrancar: un valor faltante o inseguro detiene
el servidor con un mensaje que nunca incluye secretos.

## Perfiles

| Perfil | Para qué | Cómo corre |
| --- | --- | --- |
| Desarrollo | Escribir y probar el código | Entorno virtual de Python, con el core simulado de las pruebas |
| Uso local | Usarlo desde la propia máquina | `ocr-mcp serve` o el contenedor, en `127.0.0.1`, contra un `ocr-core` accesible |
| Red local | Ofrecerlo a las máquinas de una red | `ocr-mcp serve` con TLS directo (`OCR_MCP_TLS_CERT` y `OCR_MCP_TLS_KEY`, decisión 0008) |
| En línea | Ofrecerlo a otros | Contenedor detrás de un proxy inverso con TLS (`OCR_MCP_PUBLIC_URL` con `https`) |

## Requisitos

- Python 3.11 o posterior.
- Node.js, solo para Markdownlint (`docs/procedimientos.md`).
- Para el uso local o en línea: un `ocr-core` 0.7.0 o posterior y un token de
  cliente para él (`README.md`, "Requisitos").

## Servicios

| Servicio | Para qué | Obligatorio |
| --- | --- | --- |
| `ocr-core` | Hace el OCR; el servidor es uno de sus clientes | Sí, salvo en las pruebas |
| Proxy inverso con TLS | Publicar el servidor | Solo en línea |

## Variables de entorno

| Variable | Por defecto | Qué es |
| --- | --- | --- |
| `OCR_CORE_URL` | (obligatoria) | Dirección del core, por ejemplo `http://127.0.0.1:18012` |
| `OCR_CORE_TOKEN` | (obligatoria) | Token de este servidor ante el core. Nunca se registra |
| `OCR_MCP_PUBLIC_URL` | (obligatoria) | URL con la que los clientes llegan al servidor; con ella se construyen los metadatos OAuth y los enlaces |
| `OCR_MCP_HOST` y `OCR_MCP_PORT` | `127.0.0.1` y `18040` | Dirección de escucha |
| `OCR_MCP_DATA_DIR` | (obligatoria) | Carpeta de la base SQLite |
| `OCR_MCP_ADMIN_USER` | (obligatoria) | Usuario del panel `/admin` |
| `OCR_MCP_ADMIN_PASSWORD_HASH` | (obligatoria) | Hash de la contraseña del admin |
| `OCR_MCP_ALLOWED_URL_PREFIXES` | vacío (apagado) | Prefijos de URL que el servidor puede descargar, separados por coma |
| `OCR_MCP_ACCESS_TOKEN_TTL_MIN` | `60` | Vigencia del token de acceso, en minutos |
| `OCR_MCP_REFRESH_TOKEN_TTL_DAYS` | `30` | Vigencia del token de refresco, en días |
| `OCR_MCP_LINK_TTL_MIN` | `30` | Vigencia de los enlaces de subida y descarga, en minutos |
| `OCR_MCP_MAX_UPLOAD_BYTES` | sin valor | Tamaño máximo propio por documento; rige el menor entre este y el del core (decisión 0005) |
| `OCR_MCP_MAX_PAGES` | sin valor | Páginas máximas propias por documento |
| `OCR_MCP_TLS_CERT` y `OCR_MCP_TLS_KEY` | sin valor | Certificado y llave para servir HTTPS sin proxy; van juntas y exigen `OCR_MCP_PUBLIC_URL` con `https` (decisión 0008) |

`OCR_MCP_PUBLIC_URL` solo admite `http` en `127.0.0.1`, `localhost` o `[::1]`;
en cualquier otra dirección exige `https`, como OAuth.

Docker Compose interpreta `$` en los valores del `.env` como el inicio de una
variable. Por eso el hash de la contraseña usa `:` como separador
(`scrypt:16384:8:1:…`). Si un hash del formato anterior (con `$`) llega cortado
al contenedor, el servidor no arranca: basta con cambiar sus `$` por `:`.

Solo para las pruebas:

| Variable | Qué es |
| --- | --- |
| `OCR_MCP_RESTRICTED_TERMS_FILE` | Archivo, fuera del repo, con los términos que ningún archivo versionado puede contener; uno por línea |

## Archivos de configuración

| Archivo | Para qué |
| --- | --- |
| `pyproject.toml` | Dependencias, comando `ocr-mcp`, `pytest` y `ruff` |
| `.env.example` | Plantilla de la configuración; se copia a `.env` |
| `.env` | Configuración local; nunca se versiona (`.gitignore`) |
| `Dockerfile` y `docker-compose.yml` | Imagen y despliegue de ejemplo; el estado va en el volumen `/data` |
| `.markdownlint-cli2.yaml` | Reglas de Markdown |
