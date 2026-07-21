---
name: azure-monitor
description: >
  Usa la librería ruvic_azure_monitor_connector para consultar métricas y
  alertas de Azure en modo solo lectura - consultar los datapoints de una
  métrica de un recurso (get_metric_data) y listar las alertas
  actualmente activas de la suscripción (list_active_alerts). Úsala
  cuando el usuario pida revisar métricas o el estado de alertas de sus
  recursos en Azure.
triggers:
- azure monitor
- métricas de azure
- alertas de azure
---

# Conector Azure Monitor (ruvic_azure_monitor_connector)

Librería Python de solo lectura para métricas y alertas de Azure Monitor. Está **preinstalada en el runtime** cuando el conector está configurado (si no, instálala con `pip install git+https://github.com/Dgirto/Azure-Monitor.git#subdirectory=lib`).

## Regla crítica de credenciales

El código generado **NUNCA hardcodea credenciales**. Siempre se leen de variables de entorno, disponibles cuando el conector `azure_monitor` está configurado:

| Variable | Contenido |
|----------|-----------|
| `RUVIC_AZURE_MONITOR_TENANT_ID` | Tenant ID de Azure AD |
| `RUVIC_AZURE_MONITOR_CLIENT_ID` | Client ID (Application ID) del Service Principal |
| `RUVIC_AZURE_MONITOR_CLIENT_SECRET` | Client Secret del Service Principal |
| `RUVIC_AZURE_MONITOR_SUBSCRIPTION_ID` | ID de la suscripción de Azure |
| `RUVIC_AZURE_MONITOR_CONNECT_TIMEOUT` | (opcional) timeout en segundos |

Si estas variables NO existen, el conector no está configurado: no generes código que lo use; indica al usuario que lo configure en **Settings → Conectores**.

## Conexión (siempre igual)

```python
from ruvic_azure_monitor_connector import AzureMonitorClient

client = AzureMonitorClient()  # lee RUVIC_AZURE_MONITOR_* del entorno automáticamente
```

## Capacidad 1 — Consultar métricas

```python
from datetime import datetime, timedelta, timezone

resource_id = "/subscriptions/.../resourceGroups/mi-grupo/providers/Microsoft.Compute/virtualMachines/mi-vm"
datapoints = client.get_metric_data(
    resource_id, "Percentage CPU",
    start_time=datetime.now(timezone.utc) - timedelta(hours=6),
)
for dp in datapoints:
    print(dp["timestamp"], dp["value"], dp["unit"])
```

`resource_id` es el ARM resource ID completo del recurso (lo encuentras en el Azure Portal → recurso → "Propiedades" → "Resource ID", o con `az resource list`). `metric_name` depende del tipo de recurso (ej. "Percentage CPU" para VMs, "Transactions" para Storage Accounts). Sin `start_time`/`end_time`, trae la última hora.

## Capacidad 2 — Listar alertas activas

```python
alerts = client.list_active_alerts()
for alert in alerts:
    print(f"{alert['name']} ({alert['severity']}): {alert['resource_id']}")
```

Solo retorna alertas con `monitor_condition="Fired"` y `alert_state="New"` (activas, no reconocidas ni cerradas) de toda la suscripción configurada.

## Manejo de errores

```python
from ruvic_azure_monitor_connector import (
    AzureMonitorAuthError, AzureMonitorDataError, AzureMonitorNetworkError,
)

try:
    alerts = client.list_active_alerts()
except AzureMonitorAuthError:
    print("Credenciales inválidas o sin permiso RBAC (Monitoring Reader)")
except AzureMonitorNetworkError:
    print("No se pudo alcanzar Azure — revisa el tenant y el acceso de red")
except AzureMonitorDataError as e:
    print(f"Error de datos: {e}")  # ej. el recurso no existe
```

## Buenas prácticas al generar código

1. Lee credenciales SOLO de las variables `RUVIC_AZURE_MONITOR_*` (el constructor de `AzureMonitorClient` ya lo hace).
2. Nunca imprimas `RUVIC_AZURE_MONITOR_CLIENT_SECRET` en logs ni en la salida.
3. La librería es de SOLO LECTURA: no intentes crear ni modificar reglas de alerta ni métricas personalizadas con ella.
4. Si no conoces el `resource_id` exacto, pide al usuario que lo copie desde el Azure Portal (Propiedades del recurso) en vez de intentar adivinarlo.
5. `list_active_alerts` opera a nivel de toda la suscripción; el usuario puede filtrar el resultado por `resource_id` si necesita solo las alertas de un recurso específico.
