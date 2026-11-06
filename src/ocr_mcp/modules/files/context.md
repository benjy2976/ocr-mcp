# Contexto: `files`

## Propósito

Hace viajar los archivos por enlace (decisión 0003): el PDF entra por un enlace
de subida y los artefactos salen por enlaces de descarga. Nunca por rutas del
disco del servidor ni en base64 dentro de la conversación.

## Alcance y límites

- Incluye: enlaces de subida (`uploads.py`), de descarga (`downloads.py`), la
  descarga por URL de prefijos permitidos (`fetch.py`) y sus rutas
  (`routes.py`).
- No incluye: crear trabajos ni decidir quién los ve (eso es de `jobs`).
- Dependencias funcionales: `core` (tamaño máximo y artefactos).

## Vocabulario

| Término | Significado |
| --- | --- |
| Enlace de subida | `/u/{secreto}`: acepta un PDF una sola vez, vence a los `link_ttl` segundos |
| Subida | Registro del PDF recibido: `waiting` → `ready` → `used` |
| Enlace de descarga | `/d/{secreto}`: reenvía un artefacto desde el core hasta que vence |

## Actores y permisos

| Actor | Puede | No puede | Evidencia |
| --- | --- | --- | --- |
| Quien tiene el enlace de subida | Subir un PDF, una vez | Subirlo de nuevo o después de vencer | `test_put_stores_a_valid_pdf_once` |
| Dueño de la subida | Enviarla al core con `ocr_submit` | — | `test_only_the_owner_can_take_an_upload` |
| Otro usuario | — | Usar una subida ajena: no existe para él | `test_a_user_never_sees_another_users_job_or_upload` |

El secreto del enlace es la credencial: las rutas `/u` y `/d` no usan OAuth.

## Estados y transiciones

| Origen | Evento | Condición | Destino |
| --- | --- | --- | --- |
| — | `ocr_upload_link` | — | `waiting` |
| `waiting` | `PUT` o formulario | PDF válido, dentro del tamaño | `ready` |
| `waiting` | Archivo inválido | — | `waiting` (el enlace sigue sirviendo) |
| `ready` | `ocr_submit` | Mismo dueño, sin vencer | `used`, el archivo se borra |

## Reglas

1. Un PDF válido tiene la cabecera `%PDF-` en su primer KiB, se puede leer, no
   está cifrado y tiene al menos una página.
2. El tamaño máximo es el menor entre `max_upload_bytes` del core y
   `OCR_MCP_MAX_UPLOAD_BYTES`. Se rechaza antes de leer el cuerpo si su
   `Content-Length` ya lo supera (`413`).
   Prueba: `test_a_pdf_over_the_core_limit_is_rejected_before_storing`.
3. Una URL solo se descarga si empieza por un prefijo configurado, por segmento
   de ruta, sin credenciales en la URL y sin seguir redirecciones; la lista está
   vacía por defecto. Prueba: `test_url_prefixes_are_matched_by_path_segment`.
4. Un enlace vencido o usado responde `404`.
5. Los archivos solo viven mientras la subida está `ready`; la limpieza borra
   los vencidos y los que no tienen registro.

## Flujo e integraciones

Un agente con terminal sube con `curl -T documento.pdf <enlace>`; una persona
abre el enlace y elige el archivo. La descarga reenvía el artefacto del core
por partes, con `Content-Disposition` de adjunto. Contrato HTTP: `docs/api.md`.

## Errores esperables y recuperación

| Situación | Respuesta | Recuperación |
| --- | --- | --- |
| No es un PDF, está dañado o cifrado | `400` | Subir otro archivo al mismo enlace |
| Supera el tamaño | `413` | Reducir el PDF |
| Enlace vencido o usado | `404` | Pedir otro con `ocr_upload_link` |
| Trabajo vencido en el core | `410` en la descarga | Volver a enviar |

## Pruebas mínimas

`tests/modules/files/test_links.py` y el flujo de `tests/modules/jobs/test_tools.py`.
