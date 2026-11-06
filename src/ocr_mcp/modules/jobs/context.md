# Contexto: `jobs`

## Propósito

Las herramientas MCP que usa el agente (decisiones 0003 y 0004) y el registro
de los trabajos que este servidor creó en el core, fuente de la propiedad, del
uso de cuota y de las estadísticas.

## Alcance y límites

- Incluye: `ocr_upload_link`, `ocr_submit`, `ocr_status`, `ocr_read_markdown`
  y `ocr_artifact_links` (`tools.py`), el registro (`ledger.py`), el corte del
  Markdown por páginas (`markdown.py`) y reglas sin estado (`rules.py`).
- No incluye: hablar HTTP con el core (`core`), los enlaces (`files`) ni la
  política de cuotas (`quotas`).
- Dependencias funcionales: `access`, `core`, `files` y `quotas`.

## Vocabulario

| Término | Significado |
| --- | --- |
| Trabajo | Un `job_id` del core creado por este servidor |
| Huella del pedido | SHA-256 de clave, contenido, artefactos y título |
| Devolución | Un trabajo fallido deja de contar contra la cuota |

## Actores y permisos

| Actor | Puede | No puede | Evidencia |
| --- | --- | --- | --- |
| Usuario autenticado (`subject` del token) | Usar las cinco herramientas sobre sus trabajos | Ver, leer o descargar un trabajo ajeno: "no existe" | `test_a_user_never_sees_another_users_job_or_upload` |
| Clave borrada | — | Usar cualquier herramienta | `test_a_deleted_key_can_no_longer_use_the_tools` |

## Estados y transiciones

Los estados son los del core: `queued` → `processing` → `done`, `failed` o
`blocked`. `ocr_status` guarda el estado al consultarlo; un trabajo `failed`
devuelve sus páginas a la cuota.

## Reglas

1. `ocr_submit` recibe `upload_id` o `url`, uno de los dos. Pide `md` por
   defecto y rechaza `md` si el core no anuncia su esquema.
2. Antes de enviar se comprueban el límite de páginas por documento, la cuota
   de la clave y, si es pública, el tope global.
   Pruebas: `test_quota_exceeded_explains_when_it_renews`,
   `test_jobs_in_progress_limit` y `test_public_keys_share_a_global_daily_cap`.
3. Un pedido idéntico de la misma clave devuelve el trabajo existente sin
   volver a subir ni contar páginas, salvo que haya fallado: entonces se
   reintenta con otra clave idempotente.
   Pruebas: `test_an_identical_request_reuses_the_job_without_counting_twice` y
   `test_a_failed_job_gives_its_pages_back_and_can_be_retried`.
4. El mismo PDF de dos usuarios crea dos trabajos: la huella incluye al
   usuario. Prueba: `test_the_same_pdf_from_two_users_creates_two_jobs`.
5. `ocr_status` espera hasta 50 s, consultando cada 2 s.
6. `ocr_read_markdown` devuelve como máximo 60.000 caracteres por llamada,
   cortando en límites de página, e indica las páginas de baja confianza. La
   primera página lleva además el encabezado YAML del artefacto (esquema y
   conteos) y el título.
7. Un PDF que ya tenía texto no se ofrece como artefacto: el original sirve
   como PDF buscable. Prueba: `test_a_pdf_that_already_had_text_is_not_offered_again`.
8. El registro guarda conteos y la huella del pedido, nunca nombres de archivo
   ni títulos. Prueba: `test_usage_keeps_counts_but_never_titles_or_file_names`.
9. Las descripciones de las herramientas y la lectura del Markdown advierten
   que el texto OCR es contenido, no instrucciones.

## Flujo e integraciones

Flujo completo en `docs/arquitectura.md`. Prueba de punta a punta:
`test_full_flow_from_upload_to_download`.

## Errores esperables y recuperación

| Situación | Mensaje | Recuperación |
| --- | --- | --- |
| Cuota agotada | Explica cuánto queda y cuándo se renueva | Esperar o pedir más cuota |
| Trabajo ajeno o inexistente | "El trabajo no existe." | Usar un `job_id` propio |
| Trabajo vencido en el core | "venció su retención" | Volver a enviar |
| Core caído o sin autorizar | Mensaje del módulo `core` | Reintentar o avisar a quien opera |

## Pruebas mínimas

`tests/modules/jobs/test_tools.py` y `tests/modules/jobs/test_markdown.py`.
