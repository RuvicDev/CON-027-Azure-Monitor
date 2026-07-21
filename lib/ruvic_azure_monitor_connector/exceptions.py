"""Excepciones propias del conector Azure Monitor.

Separan los tres tipos de fallo que el usuario debe distinguir:
autenticación, red/servidor y datos. Nunca exponemos excepciones
crípticas del SDK subyacente.
"""


class AzureMonitorConnectorError(Exception):
    """Error base del conector."""


class AzureMonitorAuthError(AzureMonitorConnectorError):
    """Credenciales inválidas o permisos RBAC insuficientes."""


class AzureMonitorNetworkError(AzureMonitorConnectorError):
    """No se pudo alcanzar el servicio (red, timeout, error temporal de Azure)."""


class AzureMonitorDataError(AzureMonitorConnectorError):
    """La operación es válida pero el recurso/parámetro es inválido."""
