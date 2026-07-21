"""Validación local del conector azure_monitor: ejercita las 2 capacidades.

Uso:
    python validate_local.py --resource-id "/subscriptions/.../resourceGroups/.../providers/..." --metric "Percentage CPU"

Requiere las variables RUVIC_AZURE_MONITOR_* exportadas en el entorno, y
un recurso real de Azure (VM, Storage Account, etc.) que ya genere esa
métrica.
"""

import argparse

from ruvic_azure_monitor_connector import AzureMonitorClient, setup_logging

parser = argparse.ArgumentParser()
parser.add_argument("--resource-id", required=True, help="ARM resource ID a consultar")
parser.add_argument("--metric", required=True, help="Nombre de la métrica (ej. 'Percentage CPU')")
args = parser.parse_args()

setup_logging("INFO")
client = AzureMonitorClient()

print(f"== 1. Consultar métrica '{args.metric}' (última hora) ==")
datapoints = client.get_metric_data(args.resource_id, args.metric)
print(f"  {len(datapoints)} datapoints")
for dp in datapoints[-5:]:
    print(f"  {dp['timestamp']}: {dp['value']} {dp['unit']}")

print("== 2. Listar alertas activas ==")
alerts = client.list_active_alerts()
print(f"  {len(alerts)} alerta(s) activa(s)")
for alert in alerts:
    print(f"  {alert['name']} ({alert['severity']}): {alert['resource_id']}")

print("\nTodo OK: get_metric_data y list_active_alerts funcionan.")
