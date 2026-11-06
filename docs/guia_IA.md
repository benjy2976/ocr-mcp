# Guía para agentes de IA

## Propósito y cuándo aplica

Este documento orienta a agentes y personas hacia la fuente correcta y registra
qué versión del estándar de memoria viva adoptó el repo. Es un mapa; el
protocolo operativo vive en `AGENTS.md` y no se duplica aquí.

## Adopción del estándar de memoria viva

- Skill: `gestionar-memoria-viva-proyecto`.
- Versión adoptada: `1.7.0`.
- Fecha de revisión: `2026-11-05`.
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

## Estado del proyecto

El repo tiene su diseño y su memoria, pero **todavía no tiene código**. Las
decisiones 0001 a 0007 están aceptadas y sin implementar. Al leer cualquier
documento, distinguir:

- **implementado:** existe evidencia ejecutable actual. Hoy, solo las pruebas
  de la documentación;
- **aprobado, no implementado:** orienta el diseño, pero no es una capacidad;
- **pendiente:** pregunta abierta con responsable (ver abajo).

## Mapa de fuentes normativas

| Pregunta | Fuente |
| --- | --- |
| ¿Cómo trabajar y cerrar una tarea? | `AGENTS.md` |
| ¿Qué es y cómo se usa el servidor? | `README.md` |
| ¿Por qué algo es como es? | `docs/decisiones/README.md` |
| ¿Cómo se organiza el sistema? | `docs/arquitectura.md` |
| ¿Cómo se escribe el código y la documentación? | `docs/convenciones.md` |
| ¿Qué requiere el entorno? | `docs/entorno.md` |
| ¿Cómo se instala, prueba y valida? | `docs/procedimientos.md` |
| ¿Cómo se conecta un cliente MCP? | `docs/integracion-con-clientes.md` |
| ¿Qué trabajo pendiente no tiene plan? | `docs/INICIATIVAS.md` |
| ¿Cómo se gobiernan comandos y recursos? | `docs/memoria-viva/resource-efficiency.md` |
| ¿Dónde están las referencias del estándar? | `docs/memoria-viva/README.md` |
| ¿Cómo se estructura un contexto de módulo? | `docs/context-template.md` |

### Fuentes condicionales todavía inexistentes

| Fuente | Nace cuando | Qué contendrá |
| --- | --- | --- |
| `docs/api.md` | Exista el primer endpoint HTTP (`/mcp`, OAuth, enlaces o `/admin`) | Operaciones, acceso, entradas, salidas y errores |
| `docs/modelo-datos.md` | Exista la primera migración de SQLite | Entidades, relaciones y restricciones |
| `docs/cli.md` | Exista un comando propio (por ejemplo, generar el hash del admin) | Argumentos, salidas y códigos |
| `.github/instructions/python.instructions.md` | Exista el primer código Python del servidor | Reglas propias de la capa |

`docs/frontend.md` no aplica: el panel `/admin` y la página de inicio de sesión
son plantillas del servidor dentro de sus módulos, no una raíz frontend.

## Invariantes aprobados

Todavía no hay flujos implementados. Estos invariantes gobiernan el diseño y
pasan a ser flujos críticos, con su prueba, cuando exista el código:

| Invariante | Fuente |
| --- | --- |
| Toda petición MCP exige un token OAuth válido, también en uso local | Decisión 0002 |
| Los archivos viajan por enlace; nunca en base64 ni por rutas del servidor | Decisión 0003 |
| Cada usuario ve solo sus trabajos; la `idempotency_key` incluye al usuario | Decisión 0006 |
| Claves y tokens solo como hash; nunca en logs, errores ni respuestas | Decisión 0006 |
| Las estadísticas guardan solo conteos, nunca nombres ni contenido | Decisión 0007 |

## Contextos de módulos

Ninguno todavía. Cada módulo de `src/ocr_mcp/modules/` crea su `context.md`
desde `docs/context-template.md` al nacer, y se indexa aquí en una línea. Los
módulos previstos están en `docs/arquitectura.md`.

## Instrucciones por capa

Ninguna todavía. La capa Python nace con el primer código del servidor.

## Pendientes conocidos

| Pendiente | Responsable | Antes de |
| --- | --- | --- |
| Elegir la licencia libre del repo | Autor | Publicar el repo |
| Dirección pública de `ocr-core`; hoy se genera desde el repositorio `ocr-lab` | Autor | Publicar el repo |
| Verificar con cada cliente los ejemplos de `docs/integracion-con-clientes.md` | Agente y autor | Marcar la guía como vigente |

## Errores comunes al usar la memoria

- leer solo esta guía y omitir `AGENTS.md` o el contexto afectado;
- presentar una decisión aceptada como si ya estuviera implementada;
- duplicar una regla para hacerla más visible en vez de enlazar su fuente;
- crear un documento condicional antes de que exista su capacidad;
- asumir que `N/A` o una ejecución sin errores significa que todo fue evaluado.
