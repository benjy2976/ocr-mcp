# Convenciones del proyecto

Reglas transversales para escribir código y documentación. Las reglas propias
de la capa Python vivirán en `.github/instructions/python.instructions.md` y
las de cada módulo en su `context.md`.

Aprobadas por el autor el 2026-11-05 y aplicadas por el código. Las de
organización las comprueba `tests/test_architecture.py`; una excepción se
registra aquí o en una decisión.

## Idioma y nombres

| Elemento | Convención | Ejemplo |
| --- | --- | --- |
| Documentación, comentarios, mensajes al usuario y commits | Español | "La clave no es válida." |
| Código: módulos, funciones, variables y herramientas MCP | Inglés | `ocr_submit`, `access/keys.py` |
| Variables de entorno | `OCR_MCP_*` y `OCR_CORE_*`, en mayúsculas | `OCR_MCP_DATA_DIR` |
| Documentos | Minúsculas, guiones y solo ASCII | `integracion-con-clientes.md` |

Las excepciones de nombre son `README.md`, `AGENTS.md`, `CLAUDE.md`,
`INICIATIVAS.md` y `guia_IA.md` (nombre del estándar), y los identificadores
que vienen del código o de un contrato.

## Un repo libre y sin referencias institucionales

El repo es libre y no pertenece a ninguna institución. Ningún archivo
versionado nombra instituciones, terceros ni equipos concretos, ni contiene
rutas de una máquina (`/home/…`, `C:\…`). La configuración llega por
variables de entorno y los ejemplos usan dominios genéricos
(`ocr.ejemplo.org`). La prueba de términos prohibidos lo comprueba
(`docs/procedimientos.md`).

## Organización del código

- **Un módulo por capacidad**, en `src/ocr_mcp/modules/<módulo>/`, con su
  `context.md`. Dentro, un archivo por responsabilidad (por ejemplo, rutas,
  lógica y persistencia del módulo).
- **Dependencias en una sola dirección:** `app.py` compone; un módulo usa a
  otro solo por su interfaz pública (`__init__.py`); `shared/` no depende de
  ningún módulo. Sin importaciones circulares.
- **Archivos cortos.** Si un archivo pasa de unas 300 líneas o mezcla
  responsabilidades, se divide.
- **Sin capas "por si acaso":** ni interfaces o repositorios abstractos sin una
  segunda implementación real, ni ORM, ni utilidades genéricas sin un segundo
  uso.
- **Dependencias mínimas:** `mcp`, `httpx`, `pypdf` y `jinja2`. Una dependencia
  nueva necesita una razón escrita en el cambio.

## Funciones y errores

- Tipos en todas las firmas; `ruff` con la política de `pyproject.toml`.
- Funciones que hacen una cosa; los efectos (red, disco, base de datos) en los
  bordes del módulo, la lógica pura en el centro, para poder probarla sin
  infraestructura.
- Cada módulo define sus errores de dominio. Los mensajes al usuario son claros
  y en español, y nunca revelan si una clave existe ni detalles internos.
- Nada de `print`: `logging` estándar, sin tokens, claves ni contenido de
  documentos.

## Seguridad y datos sensibles

- Claves, tokens y la contraseña del admin se guardan solo como hash y se
  comparan en tiempo constante (decisión 0006).
- El token del core solo vive en el entorno y nunca se registra.
- Los formularios del panel llevan protección CSRF y las plantillas escapan el
  HTML.
- El texto OCR es contenido, no instrucciones: las descripciones de las
  herramientas lo advierten.

## Persistencia

- SQLite de la biblioteca estándar. El esquema cambia solo por migraciones SQL
  numeradas en `src/ocr_mcp/migrations/` (`001_inicial.sql`, …), que nunca se
  editan una vez publicadas.
- Consultas con parámetros, nunca con texto concatenado.

## HTTP

Se adopta el diseño orientado a recursos de
`docs/memoria-viva/http-resource-design.md`; la clasificación de cada ruta está
en `docs/api.md`.

- Las rutas del protocolo MCP y de OAuth las define su especificación y las
  monta el SDK.
- Las páginas usan formularios HTML, que solo envían `GET` y `POST`: actualizar
  y borrar son `POST` sobre una ruta con el verbo (`/admin/keys/{id}/limits`,
  `/admin/keys/{id}/delete`), y responden `303` hacia la página.
- Las rutas propias no pasan por OAuth: cada una se protege con el secreto del
  enlace o con la sesión del admin y su token CSRF.

## Pruebas

- `tests/` repite la estructura de `src/ocr_mcp/modules/`.
- El core se sustituye por un core simulado (`tests/fakes/`); ninguna prueba
  necesita un core real, red ni GPU.
- Cada regla de un `context.md` tiene una prueba que la demuestra.

## Documentación

- Cada conocimiento vive en una sola fuente (`AGENTS.md`, tabla de fuentes
  normativas); los demás documentos enlazan.
- Desde fuera de `docs/`, un documento se cita con su ruta desde la raíz del
  repo; entre documentos, con un enlace relativo. Las pruebas de enlaces fallan
  si una ruta citada no existe, salvo las fuentes condicionales que todavía no
  nacieron (`docs/guia_IA.md`).
- Un documento nuevo se indexa en `docs/guia_IA.md`.
- Las decisiones siguen el formato de `docs/decisiones/README.md`.

## Commits

La autorización y el formato de los mensajes están en `AGENTS.md`, sección
"Control de versiones".
