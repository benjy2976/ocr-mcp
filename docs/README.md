# Documentación de `ocr-mcp`

Índice único de la documentación del repo: qué leer según la tarea, cómo está
organizada y cómo nombrar y ubicar un documento nuevo. El `AGENTS.md` de la
raíz conserva solo las entradas imprescindibles y remite aquí.

## Organización

| Carpeta o archivo | Qué contiene |
|---|---|
| [`decisiones/`](decisiones/README.md) | Registro de decisiones: qué se decidió, por qué y qué se descartó. |
| [`integracion-con-clientes.md`](integracion-con-clientes.md) | Cómo conectar los clientes más habituales al servidor. |
| [`INICIATIVAS.md`](INICIATIVAS.md) | Trabajo pendiente identificado que todavía no tiene plan. |

Fuera de `docs/` están la instalación, la configuración y la regla de uso
([`README.md`](../README.md)) y las reglas para agentes
([`AGENTS.md`](../AGENTS.md)).

## Qué leer según la tarea

| Si vas a... | Leer |
|---|---|
| Saber por qué algo es como es, antes de cambiarlo | [`decisiones/README.md`](decisiones/README.md) |
| Ver el trabajo pendiente que todavía no tiene plan | [`INICIATIVAS.md`](INICIATIVAS.md) |
| Entender qué hace el servidor y qué no (alcance) | Decisión [0001](decisiones/0001-cliente-generico-que-solo-recibe-y-entrega-trabajos.md) |
| Entender cómo corre el servidor y por qué OAuth es obligatorio | Decisión [0002](decisiones/0002-servicio-http-con-oauth-obligatorio.md) |
| Tocar la subida del PDF, las URL permitidas o los enlaces de descarga | Decisión [0003](decisiones/0003-archivos-por-enlace.md) |
| Tocar las claves de acceso, el servidor OAuth, el panel `/admin` o el aislamiento entre usuarios | Decisión [0006](decisiones/0006-claves-de-acceso-oauth-y-panel-de-admin.md) |
| Tocar las cuotas, el modo público o las estadísticas de uso | Decisión [0007](decisiones/0007-cuotas-modo-publico-y-estadisticas.md) |
| Conectar un cliente o cambiar los ejemplos de integración | [`integracion-con-clientes.md`](integracion-con-clientes.md) |
| Tocar el envío, la espera o la idempotencia de los trabajos | Decisión [0004](decisiones/0004-trabajo-asincrono-con-ticket.md) |
| Agregar o cambiar límites de tamaño, páginas o trabajos | Decisión [0005](decisiones/0005-sin-limites-propios-por-defecto.md) |
| Instalar o configurar el servidor | [`README.md`](../README.md) |

## Convención para documentos nuevos

- **Ubicación.** En `docs/`. Cuando un tema reúna más de un documento, va en su
  propia carpeta, que se agrega primero a la tabla "Organización".
- **Nombre.** Español, minúsculas, palabras separadas por guiones y solo ASCII,
  sin tildes ni ñ (`0004-trabajo-asincrono-con-ticket.md`). Las excepciones son `README.md`,
  `AGENTS.md` e `INICIATIVAS.md`, y los identificadores que vienen del código o
  de un contrato.
- **Índice.** Todo documento nuevo tiene una fila en "Qué leer según la tarea".
- **Citas.** Desde fuera de `docs/`, un documento se cita con su ruta desde la
  raíz del repo (`docs/decisiones/README.md`). Entre documentos, con un enlace
  relativo. `tests/test_documentation_links.py` falla si un enlace o una ruta
  citada no existe.
