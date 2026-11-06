# Entorno

> **Previsto.** El servidor todavía no existe. Los nombres de las variables se
> confirman al implementarlo; esta es la única fuente de las variables y el
> `README.md` la enlaza.

## Perfiles

| Perfil | Para qué | Cómo corre |
| --- | --- | --- |
| Desarrollo | Escribir y probar el código | Entorno virtual de Python, con el core simulado de las pruebas |
| Uso local | Usarlo desde la propia máquina | Servicio en `127.0.0.1`, contra un `ocr-core` accesible |
| En línea | Ofrecerlo a otros | Servicio detrás de un proxy inverso con TLS |

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
| `OCR_MCP_ALLOWED_URL_PREFIXES` | vacío (apagado) | Prefijos de URL que el servidor puede descargar |
| Vigencias | 1 h, 30 días y 30 min | Del token de acceso, del token de refresco y de los enlaces |
| Límites por documento | sin valor | Tamaño y páginas máximas (decisión 0005) |

Solo para las pruebas:

| Variable | Qué es |
| --- | --- |
| `OCR_MCP_RESTRICTED_TERMS_FILE` | Archivo, fuera del repo, con los términos que ningún archivo versionado puede contener; uno por línea |

## Archivos de configuración

| Archivo | Para qué |
| --- | --- |
| `pyproject.toml` | Dependencias, `pytest` y `ruff` |
| `.markdownlint-cli2.yaml` | Reglas de Markdown |
| `.env` | Configuración local; nunca se versiona (`.gitignore`) |
