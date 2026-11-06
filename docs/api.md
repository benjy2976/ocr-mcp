# Contrato HTTP

Fuente normativa del transporte HTTP de `ocr-mcp`: qué rutas existen, quién
puede usarlas, qué devuelven y a qué módulo pertenecen. La composición está en
`src/ocr_mcp/app.py`; las reglas de cada módulo, en su `context.md`.

> El validador de memoria no detecta las rutas de Starlette ni las del SDK de
> MCP: este inventario se revisa a mano contra `app.py` y las funciones
> `routes()` de cada módulo.

## Convenciones transversales

- Hay tres familias de rutas: el protocolo MCP y OAuth, que monta el SDK de MCP
  según sus especificaciones; los enlaces (`/u`, `/d`), cuya credencial es el
  secreto de la URL; y las páginas HTML (inicio de sesión y panel).
- Las páginas usan formularios HTML, que solo envían `GET` y `POST`: en el
  panel, actualizar y borrar son `POST` sobre una ruta con el verbo
  (`/limits`, `/delete`). Es una decisión transversal en
  `docs/convenciones.md`.
- Las respuestas HTML llevan `Cache-Control: no-store`, `X-Frame-Options: DENY`
  y `Referrer-Policy: no-referrer`.
- `<URL>` es `OCR_MCP_PUBLIC_URL`. Con un prefijo de ruta detrás de un proxy,
  todas las rutas cuelgan de él.

## Índice de endpoints

| Método | Ruta | Acceso | Tipo | Recurso o concepto | Módulo | Ruta canónica | Propósito |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `POST`, `GET`, `DELETE` | `/mcp` | Token OAuth | Protocolo MCP | Sesión MCP | SDK + `jobs` | `/mcp` | Herramientas MCP (abajo) |
| `GET` | `/.well-known/oauth-protected-resource/mcp` | Público | Consulta | Metadatos del recurso (RFC 9728) | SDK | — | Dice a los clientes dónde autorizarse |
| `GET` | `/.well-known/oauth-authorization-server` | Público | Consulta | Metadatos del servidor (RFC 8414) | SDK | — | Endpoints y métodos de OAuth |
| `POST` | `/register` | Público | Recurso canónico (crear) | Cliente OAuth (RFC 7591) | SDK + `access` | `/register` | Registro dinámico de clientes |
| `GET` | `/authorize` | Navegador del usuario | Acción OAuth | Pedido de autorización | SDK + `access` | — | Inicia el flujo y redirige a `/login` |
| `POST` | `/token` | Cliente OAuth | Acción OAuth | Tokens | SDK + `access` | — | Canjea el código o el token de refresco |
| `POST` | `/revoke` | Cliente OAuth | Acción OAuth | Tokens | SDK + `access` | — | Revoca un token |
| `GET` | `/login?request=…` | Quien tiene el pedido | Proyección | Pedido pendiente | `access` | — | Página que pide la clave |
| `POST` | `/login` | Quien tiene el pedido | Acción | Pedido pendiente | `access` | — | Aprueba el pedido con una clave y vuelve al cliente |
| `POST` | `/login/public` | Quien tiene el pedido (modo público) | Recurso canónico (crear) | Clave pública | `access` | — | Emite una clave con la cuota pública |
| `PUT` | `/u/{secreto}` | Secreto del enlace | Subrecurso (actualizar) | Contenido de la subida | `files` | `PUT /u/{secreto}` | Sube el PDF, una vez |
| `GET` | `/u/{secreto}` | Secreto del enlace | Proyección | Subida | `files` | — | Formulario para una persona |
| `POST` | `/u/{secreto}` | Secreto del enlace | Ruta contextual | Contenido de la subida | `files` | `PUT /u/{secreto}` | El mismo efecto que `PUT`, desde el formulario |
| `GET` | `/d/{secreto}` | Secreto del enlace | Proyección | Artefacto del core | `files` | — | Descarga reenviada desde el core |
| `GET` | `/health` | Público | Consulta | Salud | `app.py` | — | Sondas |
| `GET` | `/admin` | Sesión del admin | Proyección | Claves y modo público | `admin` | — | Panel, o inicio de sesión sin sesión |
| `POST` | `/admin/login` | Público | Acción | Sesión del admin | `admin` | — | Abre la sesión |
| `POST` | `/admin/logout` | Sesión + CSRF | Acción | Sesión del admin | `admin` | — | Cierra la sesión |
| `POST` | `/admin/keys` | Sesión + CSRF | Recurso canónico (crear) | Clave de acceso | `admin` + `access` | `/admin/keys` | Crea una clave y la muestra una vez |
| `GET` | `/admin/keys/{id}` | Sesión | Recurso canónico (leer) | Clave de acceso | `admin` | `/admin/keys/{id}` | Uso, cuota y borrado |
| `POST` | `/admin/keys/{id}/limits` | Sesión + CSRF | Recurso canónico (actualizar) | Cuota de la clave | `admin` | `/admin/keys/{id}` | Cambia la cuota |
| `POST` | `/admin/keys/{id}/delete` | Sesión + CSRF | Recurso canónico (borrar) | Clave de acceso | `admin` | `/admin/keys/{id}` | Borra la clave y revoca sus tokens |
| `POST` | `/admin/public` | Sesión + CSRF | Recurso singleton (actualizar) | Modo público | `admin` + `quotas` | `/admin/public` | Guarda el modo público |
| `GET` | `/admin/clients` | Sesión | Proyección | Ejemplos de integración | `admin` | — | Cómo conectar los clientes |

## Matriz de aplicabilidad CRUD

| Recurso | List | Create | Get | Update | Delete | Justificación |
| --- | --- | --- | --- | --- | --- | --- |
| Clave de acceso | Panel `/admin` | `/admin/keys`; `/login/public` en modo público | `/admin/keys/{id}` | Solo la cuota (`/limits`); el nombre no se edita: no aplica | `/delete` | Decisiones 0006 y 0007 |
| Subida | No aplica: cada usuario la conoce por su enlace | Herramienta `ocr_upload_link` | `GET /u/{secreto}` | `PUT` una vez | No aplica: vence sola | Decisión 0003 |
| Modo público | No aplica (singleton) | No aplica | Dentro de `/admin` | `/admin/public` | No aplica: se apaga | Decisión 0007 |
| Cliente OAuth | No expuesto | `/register` | No expuesto | No expuesto | No expuesto | RFC 7592 no implementado; no hace falta para los clientes MCP |
| Token OAuth | No expuesto | `/token` | No expuesto | No aplica | `/revoke`; en cascada al borrar la clave | Decisión 0006 |

## Herramientas MCP (sobre `/mcp`)

Exigen un token OAuth con el alcance `ocr`. El usuario es el `subject` del
token. Las reglas están en `src/ocr_mcp/modules/jobs/context.md`; el esquema
exacto lo publica el servidor (`tools/list`).

| Herramienta | Entrada | Resultado |
| --- | --- | --- |
| `ocr_upload_link` | — | `upload_id`, `url`, `method` (`PUT`), `expires_at`, `max_bytes` |
| `ocr_submit` | `upload_id` o `url`; `artifacts` (`md`, `text`, `pdf`; por defecto `md`); `title` opcional | `job_id`, `status`, `pages`, `artifacts`, `already_submitted`, `next` |
| `ocr_status` | `job_id`; `wait_seconds` (0 a 50) | `job_id`, `status`, `pages`, `preflight`, `error`, `artifacts` disponibles |
| `ocr_read_markdown` | `job_id`; `pages` (por ejemplo, `"1-5,8"`) | `page_count`, `pages`, `low_confidence_pages`, `truncated`, `notice`, `markdown` |
| `ocr_artifact_links` | `job_id`; `artifacts` opcional | `links` (`artifact`, `url`, `expires_at`) y `unavailable` (`artifact`, `reason`) |

Los errores se devuelven como error de herramienta, con un mensaje en español.

## Rutas propias

### `POST /login`

Formulario con `request` (el pedido pendiente) y `key`.

| Estado | Cuándo | Recuperación |
| --- | --- | --- |
| `302` | Clave válida: vuelve al `redirect_uri` del cliente con `code` y `state` | — |
| `400` | El pedido no existe o venció | Volver a conectar desde el cliente |
| `401` | "La clave no es válida." (mismo mensaje para cualquier fallo) | Revisar la clave |
| `429` | Más de 10 intentos por dirección en 10 minutos | Esperar |

### `POST /login/public`

| Estado | Cuándo |
| --- | --- |
| `200` | Página con la clave pública nueva, que se muestra una sola vez |
| `404` | El modo público está apagado |
| `429` | La dirección ya obtuvo las claves permitidas hoy |

### `PUT /u/{secreto}` y `POST /u/{secreto}`

El cuerpo del `PUT` es el PDF; el `POST` es `multipart/form-data` con el campo
`file`.

| Estado | Cuándo | Forma |
| --- | --- | --- |
| `200` | PDF válido guardado | `PUT`: JSON con `upload_id`, `pages`, `bytes` y `next`; `POST`: página de confirmación |
| `400` | No es un PDF, está dañado, cifrado o sin páginas | `{"error": …}`; el enlace sigue sirviendo |
| `404` | Enlace inexistente, usado o vencido | `{"error": …}` |
| `413` | Supera el tamaño máximo (core o servidor) | `{"error": …}` |
| `503` | El core no responde (no se conoce su límite) | `{"error": …}` |

### `GET /d/{secreto}`

| Estado | Cuándo |
| --- | --- |
| `200` | Artefacto como adjunto (`ocr-<job>.pdf`, `.jsonl` o `.md`) |
| `404` | Enlace inexistente o vencido |
| `410` | El trabajo ya no está en el core |
| `503` | El core no responde |

### Panel `/admin`

Sin sesión, todo `GET` muestra el inicio de sesión y todo `POST` vuelve a
`/admin` sin cambios. `POST /admin/login` responde `303` con la cookie, `401`
("Usuario o contraseña incorrectos.") o `429` (5 intentos en 10 minutos). Los
demás `POST` responden `303`; un valor inválido vuelve con `?error=…`.

## Pruebas que respaldan el contrato

- OAuth, `/login` y `/mcp`: `tests/modules/access/test_oauth_flow.py`.
- Enlaces: `tests/modules/files/test_links.py`.
- Herramientas: `tests/modules/jobs/test_tools.py`.
- Panel: `tests/modules/admin/test_panel.py`.
