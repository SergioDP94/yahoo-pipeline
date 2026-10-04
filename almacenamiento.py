import json
import csv
import pandas as pd

from configuracion import (INTERVALO,CALENDARIO,ZONA_MERCADO,CARPETA_LOGS)
from transformacion import validar_velas

def leer_dia_validado(ruta, simbolo, fecha, apertura, cierre):
    documento = json.loads(ruta.read_text(encoding="utf-8"))
    if not isinstance(documento, dict) or not isinstance(documento.get("datos"), list):
        raise ValueError("El archivo no tiene la estructura de un JSON diario.")

    esperado = {
        "version_esquema": 1,
        "simbolo": simbolo,
        "fecha": fecha,
        "intervalo": INTERVALO,
        "calendario": CALENDARIO,
        "sesion": "regular",
        "zona_sesion": ZONA_MERCADO,
        "zona_timestamps": "UTC",
    }
    for clave, valor in esperado.items():
        if documento.get(clave) != valor:
            raise ValueError(f"Metadato incorrecto: {clave}.")

    df = validar_velas(pd.DataFrame(documento["datos"]), apertura, cierre)
    if documento.get("registros") != len(df):
        raise ValueError("El conteo de registros no coincide con el contenido.")
    return df

def escribir_json_atomico(ruta, documento):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_suffix(".tmp")
    with temporal.open("w", encoding="utf-8") as archivo:
        json.dump(documento, archivo, ensure_ascii=False, indent=2, allow_nan=False)
    temporal.replace(ruta)

def guardar_dia(ruta, simbolo, fecha, df, apertura, cierre, metadatos):
    salida = df.copy()
    salida["timestamp_utc"] = salida["timestamp_utc"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    documento = {
        "version_esquema": 1,
        "simbolo": simbolo,
        "fecha": fecha,
        "intervalo": INTERVALO,
        "calendario": CALENDARIO,
        "sesion": "regular",
        "zona_sesion": ZONA_MERCADO,
        "zona_timestamps": "UTC",
        "fuente": "Yahoo Finance",
        "moneda": metadatos.get("currency"),
        "extraido_en_utc": pd.Timestamp.now(tz="UTC").isoformat(),
        "apertura_utc": apertura.isoformat(),
        "cierre_utc": cierre.isoformat(),
        "registros": len(salida),
        "criterio_calidad": "grilla de minutos de la sesión completa y OHLCV válidos",
        "consulta": {
            "period1": int(apertura.timestamp()),
            "period2": int(cierre.timestamp()),
            "includePrePost": False,
        },
        "datos": salida.to_dict(orient="records"),
    }
    escribir_json_atomico(ruta, documento)

def registrar_evento(ejecucion, simbolo, fecha, estado, detalle="", filas=0):
    evento = {
        "ejecucion": ejecucion,
        "momento_utc": pd.Timestamp.now(tz="UTC").isoformat(),
        "simbolo": simbolo,
        "fecha": fecha,
        "estado": estado,
        "filas": filas,
        "detalle": detalle,
    }
    ruta = CARPETA_LOGS / "ejecuciones.csv"
    escribir_cabecera = not ruta.exists() or ruta.stat().st_size == 0
    with ruta.open("a", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=list(evento))
        if escribir_cabecera:
            escritor.writeheader()
        escritor.writerow(evento)
    print(f"{fecha} | {estado} | {detalle}")
    return evento