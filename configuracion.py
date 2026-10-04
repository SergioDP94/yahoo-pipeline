from pathlib import Path
# Configuración del proyecto
# empresa y fecha de inicio de la descarga de datos
SIMBOLO = "AAPL"
FECHA_INICIO = "2026-09-21"
# características de la descarga de datos
INTERVALO = "1m"
CALENDARIO = "NASDAQ"
ZONA_MERCADO = "America/New_York"

# Configuración de carpetas y parámetros de descarga
BASE = Path.cwd() / "pipeline_yahoo"
CARPETA_DATA = BASE / "data"
CARPETA_LOGS = BASE / "logs"
CARPETA_CONTROL = BASE / "control"
# limites de consultas y pausas para evitar bloqueos
PAUSA_SEGUNDOS = 5
MAX_CONSULTAS = 8
PAUSA_BLOQUEO_SEGUNDOS = 15 * 60
# campos de datos descargados
CAMPOS_PRECIO = ["open", "high", "low", "close"]
CAMPOS_VALOR = CAMPOS_PRECIO + ["volume"]
COLUMNAS_VELAS = ["timestamp_utc"] + CAMPOS_VALOR

#for carpeta in [CARPETA_DATA, CARPETA_LOGS, CARPETA_CONTROL]:
#    carpeta.mkdir(parents=True, exist_ok=True)

#print("Proyecto:", BASE.name)
#print("Símbolo:", SIMBOLO)
#print("Fecha inicial:", FECHA_INICIO)