# 0005. Sin límites propios por defecto; manda el límite del core

- **Estado:** vigente
- **Fecha:** 2026-11-05
- **Decidió:** Walther Aguirre

## Contexto

El core define el tamaño máximo que acepta y lo publica en `/meta` como
`max_upload_bytes`; una fuente más grande recibe `413`. Quien opere un servidor
MCP compartido podría querer límites más estrictos, pero un valor por defecto
inventado en el MCP divergiría del core.

## Decisión

- Por defecto, el MCP **no impone límites propios** de tamaño, páginas ni
  trabajos en curso. Manda el límite del core: antes de subir, compara el
  tamaño del PDF con `max_upload_bytes` y, si lo supera, lo rechaza sin
  subirlo y con un mensaje claro.
- Se pueden configurar límites propios **por documento** (tamaño y páginas
  máximas) por variables de entorno, **sin valor por defecto**. Sus nombres se
  fijan al implementarlos y se documentan en el `README.md`.
- Los límites **por usuario** (páginas por periodo y trabajos en curso) son las
  cuotas por clave que fija el admin en el panel (decisión 0007), también sin
  valor por defecto, salvo la cuota pública cuando el modo público está
  encendido.
- Antes de subir, el servidor valida que el archivo sea un PDF y cuenta sus
  páginas.

## Alternativas descartadas

- **Límites fijos por defecto.** Serían valores arbitrarios, distintos de los
  del core, y rechazarían documentos que el core sí acepta.
- **Ninguna forma de limitar.** Quien comparta un core con otros clientes, o
  abra el servidor al público, necesita contener el uso desde el MCP.

## Consecuencias

- Un PDF que el core no aceptaría se rechaza antes de subirlo.
- Si el core sube su límite, el MCP lo sigue sin cambios.

## Evidencia

Commit inicial del repo (diseño). Implementación: `JobsDeps.upload_limit` en
`src/ocr_mcp/modules/jobs/tools.py` y `OCR_MCP_MAX_UPLOAD_BYTES` y
`OCR_MCP_MAX_PAGES` (`docs/entorno.md`); prueba
`test_a_pdf_over_the_core_limit_is_rejected_before_storing`.
