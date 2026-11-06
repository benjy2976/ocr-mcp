# Procedimientos

Comandos reproducibles para preparar, probar y validar el repo. Todos se
ejecutan desde la raíz del repo. Antes de ejecutar comandos, el protocolo de
`AGENTS.md` pide declarar su propósito y alcance
(`docs/memoria-viva/resource-efficiency.md`).

> El servidor todavía no existe. Hoy solo hay pruebas de la documentación; los
> procedimientos de arranque, Docker y prueba de humo nacen con el código.

## Preparar el entorno

Precondición: Python 3.11 o posterior (`docs/entorno.md`).

```bash
python -m venv .venv
.venv/bin/pip install -e '.[dev]'
```

Éxito: `.venv/bin/pytest --version` responde sin error.

## Pruebas y lint

```bash
.venv/bin/pytest
.venv/bin/ruff check .
```

Las pruebas no necesitan un core real, red ni GPU (`docs/convenciones.md`).

## Términos prohibidos

El repo no puede contener nombres de instituciones, terceros, equipos ni rutas
de máquinas (`docs/convenciones.md`). La lista de términos vive **fuera del
repo**, un término por línea, para que el repo no los nombre ni siquiera en la
prueba:

```bash
OCR_MCP_RESTRICTED_TERMS_FILE=/ruta/fuera/del/repo/terminos.txt .venv/bin/pytest tests/test_restricted_terms.py
```

Sin la variable, la prueba se omite y lo informa. Antes de cada commit, quien
tenga la lista la corre.

## Validar la memoria

```bash
scripts/validate-project-memory
npx --no-install markdownlint-cli2 "**/*.md" "#.venv" "#planes"
```

- El validador se ejecuta directo, sin anteponer `python3`: el lanzador ya
  aísla el intérprete. Para un cambio pequeño, `--changed` o `--module`
  limitan el alcance; el modo completo y Markdownlint global se reservan para
  un hito candidato a commit (`AGENTS.md`, "Cierre obligatorio").
- Leer cobertura, confianza y evidencia de cada hallazgo, no solo el código de
  salida. `NOT_EVALUATED` no significa conformidad.
- `--no-install` usa la copia de `markdownlint-cli2` en la caché de `npx`. Sin
  ella, declarar la comprobación como no ejecutada.

## Obtener `ocr-core`

`ocr-core` se genera desde el repositorio `ocr-lab`, que contiene su fuente y
su empaquetado; su documentación explica cómo generar un release desde un tag.
Para conectarlo, el servidor necesita un token de cliente cuyo hash registre
quien opera el core (`README.md`, "Requisitos").

## Mantenimiento de memoria

Antes del cambio:

1. Leer `AGENTS.md`, el `context.md` de los módulos afectados y la fuente
   normativa de lo que se va a tocar.
2. Anotar las capacidades actuales que el cambio puede alterar.

Después del cambio:

1. Revisar el diff completo.
2. Evaluar la matriz de umbrales de `AGENTS.md` y crear o actualizar la fuente
   que corresponda.
3. Correr las pruebas del módulo y el validador con alcance.
4. En un hito candidato a commit, además: suite completa, validador sin
   alcance, Markdownlint global y la prueba de términos prohibidos.

## Actualizar el estándar de memoria

Se sigue el modo "Actualizar estándar" de `docs/memoria-viva/workflow.md`:
comparar la versión adoptada (`docs/guia_IA.md`) con la nueva, migrar por
artefacto sin perder las mejoras locales y registrar la nueva versión solo al
terminar y validar.
