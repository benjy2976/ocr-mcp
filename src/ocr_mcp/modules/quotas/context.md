# Contexto: `quotas`

## Propósito

Decide si un usuario puede enviar más páginas (decisión 0007) y guarda la
configuración del modo público. Es lógica pura: no lee trabajos ni claves.

## Alcance y límites

- Incluye: `Limits`, `Usage`, `check`, `check_global`, los cortes de periodo y
  el modo público (`public.load` y `public.save`, en la tabla `settings`).
- No incluye: contar el uso (lo hace `jobs`) ni asignar límites a una clave
  (lo hace `access`).
- Dependencias funcionales: ninguna.

## Vocabulario

| Término | Significado |
| --- | --- |
| Cuota | Límite de páginas por día o por mes, y de trabajos en curso, de una clave |
| Clave pública | Clave obtenida por cualquiera en el modo público |
| Tope global | Suma diaria de páginas de todas las claves públicas |

## Actores y permisos

| Actor | Puede | Evidencia |
| --- | --- | --- |
| Admin | Fijar cuotas por clave y configurar el modo público en el panel | `admin` |
| Usuario | Consumir páginas hasta su cuota | `jobs.tools._check_limits` |

## Reglas

1. Sin límite, una clave solo está sujeta al límite del core (decisión 0005).
2. Los periodos son días y meses UTC; el error indica cuándo se renueva.
   Prueba: `test_daily_monthly_and_active_limits`.
3. Un trabajo en curso cuenta contra `max_active_jobs` hasta terminar.
4. Las claves públicas comparten un tope diario global.
   Prueba: `test_the_global_public_cap`.
5. El modo público está apagado por defecto y su cuota necesita al menos un
   límite de páginas. Prueba: `test_public_mode_is_off_by_default_and_needs_a_page_limit`.

## Flujo e integraciones

`jobs` calcula el uso con su registro de trabajos y llama a `check` (y a
`check_global` si la clave es pública) antes de enviar un PDF al core.

## Errores esperables y recuperación

| Situación | Comportamiento | Recuperación |
| --- | --- | --- |
| Cuota agotada | `QuotaExceeded` con la fecha de renovación | Esperar o pedir más cuota al admin |
| Tope global alcanzado | `QuotaExceeded` hasta el día siguiente | Esperar |

## Pruebas mínimas

`tests/modules/quotas/test_policy.py` y las pruebas de cuotas de
`tests/modules/jobs/test_tools.py`.
