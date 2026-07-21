"""Prueba de conexión estándar del conector azure_monitor.

Firma estándar Ruvic: def test_connection() -> tuple[bool, str]
- Lee la configuración EXCLUSIVAMENTE de las env vars RUVIC_AZURE_MONITOR_*.
- Nunca lanza excepciones; retorna (ok, mensaje).

Ejecutable también como script para pruebas locales:
    python test_connection.py
"""

from __future__ import annotations


def test_connection() -> tuple[bool, str]:
    """Verifica que el Service Principal pueda autenticarse, usando las
    env vars RUVIC_AZURE_MONITOR_*."""
    try:
        from ruvic_azure_monitor_connector import (
            AzureMonitorAuthError,
            AzureMonitorClient,
            AzureMonitorDataError,
            AzureMonitorNetworkError,
        )
    except ImportError:
        return (
            False,
            "La librería ruvic-azure-monitor-connector no está instalada. "
            "Instala con: pip install git+https://github.com/Dgirto/"
            "Azure-Monitor.git#subdirectory=lib",
        )

    try:
        client = AzureMonitorClient()  # valida que existan las env vars
    except ValueError as exc:
        return False, str(exc)

    try:
        client.ping()
    except AzureMonitorAuthError as exc:
        return False, f"Autenticación fallida: {exc}"
    except AzureMonitorNetworkError as exc:
        return False, f"Error de red: {exc}"
    except AzureMonitorDataError as exc:
        return False, f"Error de datos: {exc}"
    except Exception as exc:  # red de seguridad: jamás propagar
        return False, f"Error inesperado: {exc}"

    return (
        True,
        f"Conexión exitosa a Azure Monitor (suscripción {client.config.subscription_id})",
    )


if __name__ == "__main__":
    ok, message = test_connection()
    print(f"{'OK' if ok else 'FALLO'}: {message}")
    raise SystemExit(0 if ok else 1)
