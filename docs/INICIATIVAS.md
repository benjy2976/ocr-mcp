# Iniciativas

Trabajo pendiente identificado que todavía no tiene plan. Una iniciativa
describe el problema y lo que se sabe; cuando se decide abordarla, se planifica
y, al cerrarla, lo durable pasa a las decisiones y a la documentación vigente.

| Iniciativa | Estado |
| --- | --- |
| [Herramientas adicionales](#herramientas-adicionales) | Solo si el uso lo pide |
| [Tareas largas de MCP](#tareas-largas-de-mcp) | Espera soporte de los clientes |
| [Proveedor de identidad externo](#proveedor-de-identidad-externo) | Sin iniciar |
| [Distribución](#distribución) | Sin decidir |

## Herramientas adicionales

**Problema.** El conjunto mínimo (`ocr_upload_link`, `ocr_submit`,
`ocr_status`, `ocr_read_markdown` y `ocr_artifact_links`) puede quedarse corto
en el uso real.

**Candidatas**, a agregar solo si el uso las pide:

- `ocr_info`: versión del core, artefactos disponibles, límites y la cuota
  restante del usuario;
- `ocr_delete_job`: borrar un trabajo antes de que venza en el core;
- `ocr_pdf_to_markdown`: enviar, esperar hasta unos 50 segundos y leer las
  primeras páginas en una sola llamada; si no termina a tiempo, devuelve el
  `job_id` (decisión 0004);
- el recurso `ocr://jobs/{job_id}/markdown`.

## Tareas largas de MCP

**Problema.** La especificación de MCP incorporó de forma experimental una
primitiva para tareas largas (*tasks*), que reemplazaría el patrón del ticket
(decisión 0004).

**Condición.** Adoptarla solo cuando los clientes que se usen la soporten. El
ticket sigue como alternativa para los demás.

## Proveedor de identidad externo

**Problema.** El servidor de autorización incluido identifica a cada usuario
con una clave que crea el admin (decisión 0006). Una organización con su propio
proveedor de identidad (Keycloak, Google, Microsoft) podría preferir que sus
usuarios entren con su cuenta.

**Lo que haría falta.** Delegar el inicio de sesión en ese proveedor, sin
cambiar el servidor de recursos ni las cuotas, que seguirían por usuario.

## Distribución

**Problema.** Cómo instala y corre el servidor quien clona el repo.

**Opciones:**

- una imagen de contenedor con un `docker-compose.yml` de ejemplo;
- desde Git con `uvx` (`uvx --from git+<url> ocr-mcp`);
- un proxy inverso de ejemplo para publicarlo con TLS.

Se decide con el primer uso real, junto con la licencia (pendiente en el
`AGENTS.md`).
