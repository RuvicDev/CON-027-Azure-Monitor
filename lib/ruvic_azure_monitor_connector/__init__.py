"""Conector Ruvic de solo lectura para Azure Monitor."""

from .client import AzureMonitorClient
from .config import ENV_PREFIX, AzureMonitorConfig
from .exceptions import (
    AzureMonitorAuthError,
    AzureMonitorConnectorError,
    AzureMonitorDataError,
    AzureMonitorNetworkError,
)
from .logging_utils import setup_logging

__all__ = [
    "ENV_PREFIX",
    "AzureMonitorAuthError",
    "AzureMonitorClient",
    "AzureMonitorConfig",
    "AzureMonitorConnectorError",
    "AzureMonitorDataError",
    "AzureMonitorNetworkError",
    "setup_logging",
]

__version__ = "1.0.0"
