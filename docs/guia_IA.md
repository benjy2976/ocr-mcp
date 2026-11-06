# Guía para agentes de IA

## Propósito y cuándo aplica

Este documento orienta a agentes y personas hacia la fuente correcta y registra
qué versión del estándar de memoria viva adoptó el repo. Es un mapa; el
protocolo operativo vive en `AGENTS.md` y no se duplica aquí.

## Adopción del estándar de memoria viva

- Skill: `gestionar-memoria-viva-proyecto`.
- Versión adoptada: `1.7.0`.
- Fecha de revisión: `2026-11-06`.
- Versión anterior: no aplica; es la primera adopción.
- Adaptaciones y mejoras locales, que se conservan en este repo:
  - registro de decisiones (`docs/decisiones/`) e iniciativas
    (`docs/INICIATIVAS.md`);
  - política de planes y bitácoras (sección propia de `AGENTS.md`);
  - pruebas de independencia y de enlaces de la documentación, y la prueba de
    términos prohibidos (`docs/procedimientos.md`);
  - guía de integración con clientes (`docs/integracion-con-clientes.md`).

El registro es informativo: no conecta el repo con la skill ni sustituye la
validación local (`scripts/validate-project-memory`).

### Límites del validador en este repo

El validador detecta el CLI, pero no las rutas de Starlette ni del SDK de MCP
(informa `api: N/A`) ni las migraciones SQL (informa `model: N/A`). Las dos
capacidades existen: `docs/api.md` y `docs/modelo-datos.md` se revisan a mano
contra `src/ocr_mcp/app.py`, las funciones `routes()` de cada módulo y
`src/ocr_mcp/migrations/`. Los contextos de `src/ocr_mcp/modules/` tampoco se
detectan solos: el índice de abajo es la referencia.

## Estado del proyecto

El servidor está implementado: OAuth 2.1 con claves por usuario, las cinco
herramientas, enlaces de subida y descarga, cuotas, modo público, estadísticas
y panel `/admin`. Las pruebas automáticas usan un core simulado; además se
probó de punta a punta contra un `ocr-core` 0.7.0 real con el cliente MCP
oficial (OAuth, las cinco herramientas, descargas y aislamiento entre
usuarios), el 2026-11-06. Falta verificarlo con cada cliente de uso diario
(ver "Pendientes conocidos").

Al leer cualquier documento, distinguir lo implementado (con evidencia
ejecutable), lo aprobado sin implementar y lo pendiente.

## Mapa de fuentes normativas

| Pregunta | Fuente |
| --- | --- |
| ¿Cómo trabajar y cerrar una tarea? | `AGENTS.md` |
| ¿Qué es y cómo se usa el servidor? | `README.md` |
| ¿Por qué algo es como es? | `docs/decisiones/README.md` |
| ¿Cómo se organiza el sistema? | `docs/arquitectura.md` |
| ¿Cómo se escribe el código y la documentación? | `docs/convenciones.md` |
| ¿Qué requiere el entorno? | `docs/entorno.md` |
| ¿Cómo se instala, prueba, valida y despliega? | `docs/procedimientos.md` |
| ¿Qué rutas HTTP y herramientas MCP existen? | `docs/api.md` |
| ¿Cómo se persisten los datos? | `docs/modelo-datos.md` |
| ¿Qué hace el comando `ocr-mcp`? | `docs/cli.md` |
| ¿Cómo se conecta un cliente MCP? | `docs/integracion-con-clientes.md` |
| ¿Qué trabajo pendiente no tiene plan? | `docs/INICIATIVAS.md` |
| ¿Cómo se gobiernan comandos y recursos? | `docs/memoria-viva/resource-efficiency.md` |
| ¿Dónde están las referencias del estándar? | `docs/memoria-viva/README.md` |
| ¿Cómo se estructura un contexto de módulo? | `docs/context-template.md` |

`docs/frontend.md` no aplica: el panel y la página de inicio de sesión son
plantillas del servidor dentro de sus módulos, no una raíz frontend.

## Flujos críticos

| Flujo | Invariante | Fuente | Prueba |
| --- | --- | --- | --- |
| Autorización | Toda petición MCP exige un token OAuth para `<URL>/mcp`; borrar la clave lo revoca | Decisiones 0002 y 0006, `src/ocr_mcp/modules/access/context.md` | `tests/modules/access/test_oauth_flow.py` |
| Aislamiento | Cada usuario ve solo sus trabajos y subidas | `src/ocr_mcp/modules/jobs/context.md` | `test_a_user_never_sees_another_users_job_or_upload` |
| Archivos | Entran y salen por enlace; nunca en base64 ni por rutas del servidor | Decisión 0003, `src/ocr_mcp/modules/files/context.md` | `tests/modules/files/test_links.py` |
| Cuotas | Se comprueban antes de enviar; un fallo devuelve las páginas | Decisión 0007, `src/ocr_mcp/modules/quotas/context.md` | `tests/modules/quotas/test_policy.py` |
| Privacidad | Secretos solo como hash; estadísticas solo con conteos | Decisiones 0006 y 0007, `docs/modelo-datos.md` | `test_usage_keeps_counts_but_never_titles_or_file_names` |

## Contextos de módulos

- `core`: `src/ocr_mcp/modules/core/context.md` — cliente HTTP de `ocr-core`.
- `quotas`: `src/ocr_mcp/modules/quotas/context.md` — política de cuotas y modo público.
- `access`: `src/ocr_mcp/modules/access/context.md` — claves de acceso, OAuth e inicio de sesión.
- `files`: `src/ocr_mcp/modules/files/context.md` — enlaces de subida y descarga, y URL permitidas.
- `jobs`: `src/ocr_mcp/modules/jobs/context.md` — herramientas MCP y registro de trabajos.
- `admin`: `src/ocr_mcp/modules/admin/context.md` — panel `/admin`.

## Instrucciones por capa

- Python: `.github/instructions/python.instructions.md` — todo el servicio, en
  `src/ocr_mcp/`.

## Pendientes conocidos

| Pendiente | Responsable | Antes de |
| --- | --- | --- |
| Elegir la licencia libre del repo | Autor | Publicar el repo |
| Dirección pública de `ocr-core`; hoy se genera desde el repositorio `ocr-lab` | Autor | Publicar el repo |
| Conectar Claude Code y usarlo con documentos propios | Autor | Marcar el servidor como listo para uso |
| Verificar con cada cliente los ejemplos de `docs/integracion-con-clientes.md` | Agente y autor | Marcar la guía como vigente |

## Errores comunes al usar la memoria

- leer solo esta guía y omitir `AGENTS.md` o el contexto afectado;
- confiar en un `N/A` del validador para `api` o `model`: aquí son límites de
  detección, no ausencia de la capacidad;
- duplicar una regla para hacerla más visible en vez de enlazar su fuente;
- cambiar una ruta, una tabla o el comando sin actualizar `docs/api.md`,
  `docs/modelo-datos.md` o `docs/cli.md`.
