import json
import pandas as pd
from email.utils import parsedate_to_datetime
from configuracion import (CARPETA_CONTROL, INTERVALO, PAUSA_BLOQUEO_SEGUNDOS)
from almacenamiento import escribir_json_atomico

class BloqueoYahoo(RuntimeError):
    pass

def registrar_pausa(respuesta):
    ahora = pd.Timestamp.now(tz="UTC")
    espera = PAUSA_BLOQUEO_SEGUNDOS
    cabecera = respuesta.headers.get("Retry-After")

    if cabecera:
        try:
            if cabecera.strip().isdigit():
                indicada = int(cabecera.strip())
            else:
                fecha_http = pd.Timestamp(parsedate_to_datetime(cabecera))
                if fecha_http.tzinfo is None:
                    fecha_http = fecha_http.tz_localize("UTC")
                indicada = (fecha_http - ahora).total_seconds()
            espera = max(espera, indicada)
        except (TypeError, ValueError, OverflowError):
            pass  # Se mantiene la pausa de respaldo.

    hasta = ahora + pd.Timedelta(seconds=espera)
    escribir_json_atomico(CARPETA_CONTROL / "pausa_yahoo.json", {
        "hasta_utc": hasta.isoformat(),
        "codigo_http": respuesta.status_code,
        "retry_after": cabecera,
    })
    return hasta


def pausa_vigente():
    ruta = CARPETA_CONTROL / "pausa_yahoo.json"
    if not ruta.exists():
        return None
    documento = json.loads(ruta.read_text(encoding="utf-8"))
    hasta = pd.Timestamp(documento["hasta_utc"])
    if hasta.tzinfo is None:
        raise ValueError("El archivo de pausa debe contener una fecha con zona horaria.")
    return hasta if hasta > pd.Timestamp.now(tz="UTC") else None

def consultar_sesion(sesion, simbolo, apertura, cierre):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{simbolo}"
    parametros = {
        "interval": INTERVALO,
        "period1": int(apertura.timestamp()),
        "period2": int(cierre.timestamp()),
        "includePrePost": "false",
    }
    respuesta = sesion.get(url, params=parametros, timeout=(10, 30))

    if respuesta.status_code in (401, 403, 429):
        hasta = registrar_pausa(respuesta)
        raise BloqueoYahoo(
            f"HTTP {respuesta.status_code}. Consultas pausadas al menos hasta {hasta}."
        )

    respuesta.raise_for_status()
    return respuesta.json()