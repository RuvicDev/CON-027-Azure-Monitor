# Conector Azure Monitor (CON-027)

Conector Ruvic de solo lectura para métricas y alertas de Azure Monitor.
Permite consultar los datapoints de una métrica de un recurso y listar
las alertas actualmente activas de la suscripción.

## Instalación

```bash
pip install git+https://github.com/Dgirto/Azure-Monitor.git#subdirectory=lib
```

Python 3.10+. Dependencias: `azure-identity`, `azure-mgmt-monitor`,
`azure-mgmt-alertsmanagement`.

## Permisos requeridos en Azure

Crea un **Service Principal** dedicado (App Registration en Azure AD) con
el rol RBAC `Monitoring Reader`:

```bash
az ad sp create-for-rbac --name "ruvic-monitor-reader" \
  --role "Monitoring Reader" \
  --scopes "/subscriptions/TU_SUBSCRIPTION_ID"
```

Este comando imprime `appId` (Client ID), `password` (Client Secret) y
`tenant` (Tenant ID) — los tres van al formulario del conector.

- `Monitoring Reader`: necesario para `monitor.get_metrics` y
  `monitor.list_active_alerts`. Es un rol 100% de solo lectura.
- No se otorga el rol `Monitoring Contributor` ni ningún permiso de
  escritura sobre recursos, reglas de alerta o métricas personalizadas.
- Para limitar el alcance a solo ciertos recursos, cambia el `--scopes`
  a un grupo de recursos específico en vez de toda la suscripción:
  `--scopes "/subscriptions/TU_SUB/resourceGroups/TU_GRUPO"`.

## Variables de entorno (`RUVIC_AZURE_MONITOR_*`)

| Variable | Obligatoria | Descripción |
|----------|-------------|-------------|
| `RUVIC_AZURE_MONITOR_TENANT_ID` | Sí | Tenant ID de Azure AD |
| `RUVIC_AZURE_MONITOR_CLIENT_ID` | Sí | Client ID (Application ID) del Service Principal |
| `RUVIC_AZURE_MONITOR_CLIENT_SECRET` | Sí | Client Secret del Service Principal |
| `RUVIC_AZURE_MONITOR_SUBSCRIPTION_ID` | Sí | ID de la suscripción de Azure |
| `RUVIC_AZURE_MONITOR_CONNECT_TIMEOUT` | No (default `10`) | Timeout de conexión en segundos |

## Pruebas locales

Con una suscripción de Azure real y al menos un recurso que ya genere
métricas (una VM, un Storage Account, etc.):

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ./lib

export RUVIC_AZURE_MONITOR_TENANT_ID=tu-tenant-id
export RUVIC_AZURE_MONITOR_CLIENT_ID=tu-client-id
export RUVIC_AZURE_MONITOR_CLIENT_SECRET=tu-client-secret
export RUVIC_AZURE_MONITOR_SUBSCRIPTION_ID=tu-subscription-id

python test_connection.py
python validate_local.py --resource-id "/subscriptions/.../virtualMachines/mi-vm" --metric "Percentage CPU"
```

Prueba también los casos de error (credenciales incorrectas, recurso
inexistente, métrica sin datos) y verifica que los mensajes sean claros.

## Notas de integración

- El conector es de solo lectura: nunca crea, modifica ni elimina
  reglas de alerta, métricas personalizadas ni recursos.
- `get_metric_data` requiere el ARM resource ID completo del recurso
  (no solo su nombre) — el usuario debe copiarlo del Azure Portal o
  usar `az resource show` para obtenerlo.
- `list_active_alerts` solo retorna alertas con `monitor_condition="Fired"`
  y `alert_state="New"` (activas y no reconocidas), a nivel de toda la
  suscripción configurada.
- `ping()` solo valida que el Service Principal pueda obtener un token de
  Azure AD; no valida permisos RBAC sobre un recurso específico hasta que
  se invoca una operación real.
