# 0007. Cuotas por clave, modo público opcional y estadísticas de uso

- **Estado:** vigente
- **Fecha:** 2026-11-05
- **Decidió:** Walther Aguirre

## Contexto

El servidor da acceso al OCR de un core con GPU. Quien lo opera puede querer
limitar cuánto procesa cada usuario, abrirlo al público con un tope y saber
quién lo usa y cuánto. El costo del OCR crece con las páginas, no con los
documentos.

## Decisión

1. **Cuotas por clave**, que el admin fija en el panel al crear la clave o
   después:
   - **páginas por periodo**, por día y por mes;
   - **trabajos en curso** a la vez.

   Sin cuota, la clave no tiene límite propio: solo rige el del core
   (decisión 0005). Las páginas se cuentan al enviar el PDF. Si el core lo
   rechaza o falla por una causa ajena al documento, se devuelven a la cuota.
   Al agotarse la cuota, `ocr_submit` responde con un error claro que indica
   cuándo se renueva.
2. **Modo público, opcional y apagado por defecto.** El admin lo habilita en el
   panel:
   - la página de inicio de sesión ofrece, además, obtener una clave propia, que
     nace con la **cuota pública** configurada;
   - un **tope global** de páginas por día limita la suma de todas las claves
     públicas;
   - la emisión de claves públicas tiene un límite por dirección;
   - las claves públicas se distinguen en el panel; el admin puede borrarlas o
     apagar el modo público en cualquier momento, y las que siguen activas
     conservan su cuota;
   - el texto de la página pública advierte la regla de uso sobre datos
     personales (`README.md`).
3. **Estadísticas de uso por clave**, en el panel:
   - documentos, páginas y bytes enviados;
   - trabajos terminados y fallidos;
   - última vez que se usó;
   - una serie diaria de los últimos 30 días;
   - el consumo de la cuota del periodo.

   Solo se guardan conteos. Nunca nombres de archivo, títulos ni contenido de
   los documentos.

## Alternativas descartadas

- **Cuotas por documentos o por bytes.** No reflejan el costo: un documento de
  una página y uno de 500 cuestan muy distinto.
- **Modo público sin clave** (anónimo). No permitiría cuotas por usuario ni
  cortar el acceso a quien abuse, y la decisión 0002 exige OAuth.
- **Estadísticas con nombres de archivo.** Los nombres pueden contener datos
  personales, y para medir el uso bastan los conteos.

## Consecuencias

- El panel deja de ser solo de claves: también fija cuotas y muestra uso.
  Sigue sin roles ni más funciones.
- Encender el modo público expone la GPU del core a cualquiera con una clave
  pública, dentro del tope global. Es una decisión de quien opera el servidor.
- Las pruebas cubren el agotamiento y la renovación de cuotas, la devolución
  cuando el trabajo falla, el tope global y que las estadísticas no guarden
  nombres.

## Evidencia

Commit inicial del repo (diseño). Implementación: `src/ocr_mcp/modules/quotas/`
y `src/ocr_mcp/modules/jobs/ledger.py`; pruebas en
`tests/modules/quotas/test_policy.py` y en las de cuotas de
`tests/modules/jobs/test_tools.py`.
