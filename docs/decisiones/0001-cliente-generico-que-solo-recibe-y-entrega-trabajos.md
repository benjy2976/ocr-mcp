# 0001. Un cliente genérico de `ocr-core` que solo recibe y entrega trabajos

- **Estado:** aceptada, sin implementar
- **Fecha:** 2026-11-05
- **Decidió:** Walther Aguirre

> **Hoy:** el repo todavía no tiene código. Esta decisión fija el alcance de lo
> que se va a implementar.

## Contexto

`ocr-core` es un servicio HTTP genérico de OCR. Desde 0.6.0 recibe el PDF por
subida (`POST /jobs/upload`), entrega los artefactos por descarga
(`GET /jobs/{id}/artifacts/{pdf|text|md}`) y no accede al almacenamiento de
quien lo usa. Desde 0.7.0 cada cliente se autentica con su propio token, y cada
trabajo pertenece al cliente que lo creó. `/meta` anuncia su versión, sus
capacidades y el tamaño máximo que acepta.

Ese OCR sirve también a agentes de IA, que usan herramientas externas mediante
MCP. El servidor lo usará su autor, y también cualquiera que clone el repo y
tenga acceso a un core.

## Decisión

`ocr-mcp` es **un cliente más del core**, con su propio token, que solo recibe
y entrega trabajos:

1. Traduce las peticiones del agente a la API HTTP del core: enviar un PDF,
   consultar y esperar el estado, leer el Markdown, entregar los artefactos y
   borrar el trabajo.
2. **No contiene lógica OCR.** Toda mejora del OCR llega por el core.
3. **No conoce el almacenamiento de ningún otro sistema.** Los archivos le
   llegan por un enlace de subida y los devuelve por enlaces de descarga
   (decisión 0003).
4. **Es genérico.** Ningún archivo versionado nombra una institución, otro
   cliente del core ni rutas de un equipo concreto. Se configura por variables
   de entorno: `OCR_CORE_URL` (dirección del core) y `OCR_CORE_TOKEN` (token de
   este cliente, cuyo hash registra quien opera el core).
5. Declara su compatibilidad contra lo que anuncia `/meta`: autenticación
   (`capabilities.auth`), esquema del Markdown (`capabilities.artifact_schemas.md`)
   y tamaño máximo (`max_upload_bytes`). Al arrancar verifica el token con
   `/meta`.
6. Quién lo usa y cuánto se controla en el propio servidor: OAuth con una clave
   por usuario (decisiones 0002 y 0006) y cuotas por clave (decisión 0007).

## Alternativas descartadas

- **Integrar el MCP dentro del core.** Mezclaría responsabilidades: el core
  tendría que conocer a los agentes y su protocolo, y cada cambio del MCP
  exigiría un release del core.
- **Leer o escribir el almacenamiento de otro sistema.** El core abandonó el
  almacenamiento compartido precisamente para no depender de él. El MCP no
  necesita más que los archivos del usuario y la API del core.
- **Ejecutar el OCR dentro del MCP** (Tesseract u otro motor local). Duplicaría
  el motor, sin la normalización previa ni los modelos del core, y daría
  resultados distintos.

## Consecuencias

- Requiere un `ocr-core` 0.7.0 o posterior accesible por HTTP y un token cuyo
  hash esté registrado en ese core. Sin token válido, el servidor lo informa y
  no ofrece resultados.
- El MCP solo ve los trabajos que él mismo creó: el core responde `404` a los
  de otros clientes.
- Una capacidad nueva del core (otro artefacto, otro esquema) se aprovecha
  cuando `/meta` la anuncia y el MCP la incorpora; no hay que tocar el motor.

## Evidencia

Commit inicial del repo.
