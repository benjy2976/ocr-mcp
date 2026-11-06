# Contexto: `core`

## Propósito

Habla con `ocr-core` en nombre del servidor. Es el único módulo que conoce su
API HTTP, así que un cambio en el core se resuelve aquí.

## Alcance y límites

- Incluye: `/meta` con caché de 60 s, subida multipart por partes
  (`POST /jobs/upload`), estado (`GET /jobs/{id}`), artefactos
  (`GET /jobs/{id}/artifacts/{nombre}`) y borrado (`DELETE /jobs/{id}`).
- No incluye: quién es el usuario, cuotas ni propiedad de los trabajos (eso es
  de `jobs`).
- Dependencias funcionales: ninguna.

## Actores y permisos

| Actor | Puede | Evidencia |
| --- | --- | --- |
| Este servidor | Usar el core con su token (`OCR_CORE_TOKEN`), como cliente `mcp` | `client.py`, cabecera `Authorization` |

El core solo ve un cliente: el aislamiento entre usuarios lo hace `jobs`.

## Reglas

1. Cada llamada lleva `Authorization: Bearer <OCR_CORE_TOKEN>`; el token nunca
   aparece en un error ni en un log. Prueba: `test_core_errors_are_translated_without_the_token`.
2. El PDF se envía por bloques de 1 MiB con `Content-Length`, sin cargarlo en
   memoria. Prueba: `test_upload_streams_the_pdf_and_reads_artifacts`.
3. Las respuestas del core se traducen a errores propios: `401` →
   `CoreAuthError`, `404` → `CoreNotFound`, `413` y otros `4xx` →
   `CoreRejected`, `5xx` o sin conexión → `CoreUnavailable`. Pruebas en
   `tests/modules/core/test_client.py`.
4. Borrar un trabajo que ya no existe no es un error.
5. `/meta` declara si el core genera Markdown (`artifact_schemas.md =
   ocr.markdown.document.v1`) y su tamaño máximo (`max_upload_bytes`).

## Flujo e integraciones

`jobs` llama a `submit`, `job`, `artifact_text` y `meta`; `files` usa `meta`
para el tamaño máximo y `artifact_stream` para las descargas.

## Errores esperables y recuperación

| Situación | Comportamiento | Recuperación |
| --- | --- | --- |
| Token del servidor rechazado | `CoreAuthError`; el usuario ve "Este servidor no está autorizado ante el core" | Quien opera registra el hash del token en el core |
| Core caído | `CoreUnavailable` | Reintentar más tarde; no se consume cuota |
| Trabajo vencido en el core | `CoreNotFound` | Volver a enviar el documento |

## Pruebas mínimas

`tests/modules/core/test_client.py`, contra el core simulado
(`tests/fakes/core.py`).
