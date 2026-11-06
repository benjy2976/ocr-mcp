# Plantilla de contexto de módulo

Se copia como `context.md` en la raíz de un módulo de `src/ocr_mcp/modules/`
cuando el módulo nace con comportamiento real, y se indexa en
`docs/guia_IA.md`. No se crea para carpetas técnicas como `shared/`.

El `context.md` es la fuente del negocio propio del módulo: vocabulario,
actores, permisos, estados, reglas y escenarios verificables. Los campos
persistidos viven en `docs/modelo-datos.md`, el transporte en `docs/api.md` y
la composición global en `docs/arquitectura.md`: se enlazan, no se copian.

Al copiarla, cada sección se completa con evidencia del código y las pruebas.
Una sección que no aplica se elimina; una duda real se convierte en un
pendiente concreto.

## Propósito

Quién obtiene valor del módulo y qué resultado observable produce, en una o
dos oraciones.

## Alcance y límites

Qué incluye, qué queda fuera y de qué otros módulos depende (solo por su
interfaz pública).

## Vocabulario

Términos cuyo significado local no sea obvio, con su nombre en el código.

## Actores y permisos

Quién puede hacer qué y qué código lo comprueba. Distinguir autenticación,
autorización y propiedad del recurso.

## Estados y transiciones

Estados válidos, eventos, condiciones y efectos. Con tres estados o más, un
diagrama `stateDiagram-v2` ayuda a leerlos.

## Reglas

Reglas numeradas, cada una con condición, comportamiento y excepción, y con la
prueba que la demuestra.

## Flujo e integraciones

Entrada, secuencia principal y salida. Si participan tres componentes o más,
un `sequenceDiagram` y el enlace al contrato correspondiente.

## Errores esperables y recuperación

Qué falla, qué ve el usuario y si reintentar es seguro.

## Pruebas mínimas

El camino principal, una regla de permisos y la transición o excepción
crítica, con el enlace a cada prueba.

## Decisiones recientes

Solo decisiones no obvias que todavía condicionan el trabajo. Las que cruzan
módulos van en `docs/decisiones/`.
