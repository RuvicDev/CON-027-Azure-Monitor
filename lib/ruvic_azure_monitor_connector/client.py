"""Cliente de solo lectura para Azure Monitor.

Capacidades:
- get_metric_data():     consultar los datapoints de una métrica de un recurso.
- list_active_alerts():  listar las alertas actualmente activas (disparadas).

Las credenciales SIEMPRE provienen de variables de entorno
RUVIC_AZURE_MONITOR_* (ver config.AzureMonitorConfig.from_env).
Prohibido hardcodearlas. Se autentica vía Service Principal (Azure AD
App Registration).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from azure.core.exceptions import (
    ClientAuthenticationError,
    HttpResponseError,
    ResourceNotFoundError,
    ServiceRequestError,
)
from azure.identity import ClientSecretCredential
from azure.mgmt.alertsmanagement import AlertsManagementClient
from azure.mgmt.monitor import MonitorManagementClient

from .config import AzureMonitorConfig
from .exceptions import (
    AzureMonitorAuthError,
    AzureMonitorConnectorError,
    AzureMonitorDataError,
    AzureMonitorNetworkError,
)
from .logging_utils import get_logger

_MAX_ALERT_LIMIT = 200


def _wrap_error(exc: Exception, not_found_message: str) -> AzureMonitorConnectorError:
    """Traduce un error del SDK de Azure a una excepción propia, sin dejar
    escapar nunca el tipo crudo del SDK."""
    if isinstance(exc, ClientAuthenticationError):
        return AzureMonitorAuthError(
            "Credenciales inválidas o el Service Principal no tiene permiso "
            "suficiente. Revisa el rol RBAC asignado (ej. Monitoring Reader)."
        )
    if isinstance(exc, ResourceNotFoundError):
        return AzureMonitorDataError(not_found_message)
    if isinstance(exc, HttpResponseError):
        return AzureMonitorDataError(f"Error de datos (HTTP {exc.status_code}): {exc.message}")
    return AzureMonitorDataError(f"Error de datos: {exc}")


class AzureMonitorClient:
    """Cliente de solo lectura para métricas y alertas de Azure Monitor.

    Args:
        config: configuración de conexión. Si se omite, se lee de las
            variables de entorno RUVIC_AZURE_MONITOR_* (comportamiento
            estándar en el runtime de la plataforma).

    Ejemplo:
        >>> client = AzureMonitorClient()   # lee RUVIC_AZURE_MONITOR_* del entorno
        >>> client.list_active_alerts()
        [{'name': 'cpu-alta-produccion', 'severity': 'Sev2', ...}]
    """

    def __init__(self, config: AzureMonitorConfig | None = None) -> None:
        self.config = config or AzureMonitorConfig.from_env()
        self._logger = get_logger()
        self._credential: ClientSecretCredential | None = None
        self._monitor_client: MonitorManagementClient | None = None
        self._alerts_client: AlertsManagementClient | None = None

    # ------------------------------------------------------------------ #
    # Conexión
    # ------------------------------------------------------------------ #

    def _get_credential(self) -> ClientSecretCredential:
        if self._credential is None:
            self._credential = ClientSecretCredential(
                tenant_id=self.config.tenant_id,
                client_id=self.config.client_id,
                client_secret=self.config.client_secret,
            )
        return self._credential

    def _get_monitor_client(self) -> MonitorManagementClient:
        if self._monitor_client is None:
            self._monitor_client = MonitorManagementClient(
                credential=self._get_credential(),
                subscription_id=self.config.subscription_id,
            )
        return self._monitor_client

    def _get_alerts_client(self) -> AlertsManagementClient:
        if self._alerts_client is None:
            self._alerts_client = AlertsManagementClient(
                credential=self._get_credential(),
                subscription_id=self.config.subscription_id,
            )
        return self._alerts_client

    def ping(self) -> bool:
        """Verifica la conexión obteniendo un token de acceso del Service
        Principal (valida credenciales y red; no valida permisos RBAC
        sobre un recurso específico).

        Returns:
            True si la conexión funciona.

        Raises:
            AzureMonitorAuthError / AzureMonitorNetworkError según el fallo.
        """
        try:
            self._get_credential().get_token("https://management.azure.com/.default")
        except ClientAuthenticationError as exc:
            raise _wrap_error(exc, "") from exc
        except ServiceRequestError as exc:
            raise AzureMonitorNetworkError(
                f"No se pudo conectar a Azure AD (timeout {self.config.connect_timeout}s). "
                "Verifica el tenant_id y el acceso de red."
            ) from exc
        self._logger.info("Ping exitoso (token de Service Principal obtenido)")
        return True

    # ------------------------------------------------------------------ #
    # Capacidad 1: consultar métricas
    # ------------------------------------------------------------------ #

    def get_metric_data(
        self,
        resource_id: str,
        metric_name: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        interval: str = "PT5M",
        aggregation: str = "Average",
    ) -> list[dict[str, Any]]:
        """Consulta los datapoints de una métrica de un recurso de Azure.

        Args:
            resource_id: ID completo del recurso (ARM resource ID, ej.
                "/subscriptions/.../resourceGroups/.../providers/Microsoft.Compute/virtualMachines/mi-vm").
            metric_name: nombre de la métrica (ej. "Percentage CPU").
            start_time: inicio del rango (UTC). Default: hace 1 hora.
            end_time: fin del rango (UTC). Default: ahora.
            interval: granularidad ISO 8601 (default "PT5M" = 5 minutos).
            aggregation: "Average", "Total", "Minimum", "Maximum" o "Count"
                (default "Average").

        Returns:
            Lista de dicts: {"timestamp", "value", "unit"}, ordenados
            cronológicamente.

        Ejemplo:
            >>> client.get_metric_data(
            ...     "/subscriptions/.../virtualMachines/mi-vm", "Percentage CPU")
            [{'timestamp': '2026-07-17T10:00:00Z', 'value': 23.5, 'unit': 'Percent'}]
        """
        resource_id = (resource_id or "").strip()
        if not resource_id:
            raise AzureMonitorDataError("resource_id no puede estar vacío.")
        now = datetime.now(timezone.utc)
        end_time = end_time or now
        start_time = start_time or (end_time - timedelta(hours=1))
        timespan = f"{start_time.isoformat()}/{end_time.isoformat()}"

        client = self._get_monitor_client()
        try:
            response = client.metrics.list(
                resource_uri=resource_id,
                metricnames=metric_name,
                timespan=timespan,
                interval=interval,
                aggregation=aggregation,
            )
        except ClientAuthenticationError as exc:
            raise _wrap_error(exc, "") from exc
        except ResourceNotFoundError as exc:
            raise AzureMonitorDataError(
                f"No se encontró el recurso o la métrica {metric_name!r}."
            ) from exc
        except (ServiceRequestError, HttpResponseError) as exc:
            raise _wrap_error(exc, "") from exc

        agg_attr = aggregation.lower()
        result: list[dict[str, Any]] = []
        for metric in response.value:
            unit = str(metric.unit) if metric.unit else None
            for series in metric.timeseries:
                for point in series.data:
                    value = getattr(point, agg_attr, None)
                    if value is None:
                        continue
                    result.append(
                        {"timestamp": point.time_stamp.isoformat(), "value": value, "unit": unit}
                    )
        result.sort(key=lambda d: d["timestamp"])
        self._logger.info(
            "Se obtuvieron %d datapoints de %s en %s", len(result), metric_name, resource_id
        )
        return result

    # ------------------------------------------------------------------ #
    # Capacidad 2: listar alertas activas
    # ------------------------------------------------------------------ #

    def list_active_alerts(self, limit: int = 100) -> list[dict[str, Any]]:
        """Lista las alertas que están actualmente activas (disparadas y
        no cerradas) en la suscripción configurada.

        Args:
            limit: máximo de alertas a retornar (default 100, máximo 200).

        Returns:
            Lista de dicts: {"name", "severity", "state", "monitor_condition",
            "resource_id", "start_time"}.

        Ejemplo:
            >>> client.list_active_alerts()
            [{'name': 'cpu-alta-produccion', 'severity': 'Sev2', 'state': 'New', ...}]
        """
        limit = max(1, min(int(limit), _MAX_ALERT_LIMIT))
        client = self._get_alerts_client()
        try:
            alerts = client.alerts.get_all(monitor_condition="Fired", alert_state="New")
        except ClientAuthenticationError as exc:
            raise _wrap_error(exc, "") from exc
        except (ServiceRequestError, HttpResponseError) as exc:
            raise _wrap_error(exc, "") from exc

        result = []
        for alert in alerts:
            props = alert.properties.essentials if alert.properties else None
            result.append(
                {
                    "name": props.alert_rule if props else alert.name,
                    "severity": str(props.severity) if props and props.severity else None,
                    "state": str(props.alert_state) if props and props.alert_state else None,
                    "monitor_condition": str(props.monitor_condition)
                    if props and props.monitor_condition
                    else None,
                    "resource_id": props.target_resource if props else None,
                    "start_time": props.start_date_time.isoformat()
                    if props and props.start_date_time
                    else None,
                }
            )
            if len(result) >= limit:
                break
        self._logger.info("Se listaron %d alertas activas", len(result))
        return result
