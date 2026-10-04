import math
import pandas as pd

from configuracion import (COLUMNAS_VELAS,CAMPOS_VALOR,CAMPOS_PRECIO, ZONA_MERCADO, INTERVALO)

def validar_velas(df, apertura, cierre):
    if df.empty or not set(COLUMNAS_VELAS).issubset(df.columns):
        raise ValueError("No hay velas o faltan columnas obligatorias.")

    df = df[COLUMNAS_VELAS].copy()
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
    df = df.sort_values("timestamp_utc").reset_index(drop=True)

    if df["timestamp_utc"].isna().any():
        raise ValueError("Hay marcas de tiempo nulas.")
    if df["timestamp_utc"].duplicated().any():
        raise ValueError("Hay minutos duplicados.")

    for columna in CAMPOS_VALOR:
        df[columna] = pd.to_numeric(df[columna], errors="coerce")
        if not all(math.isfinite(valor) for valor in df[columna]):
            raise ValueError(f"Valores nulos o no finitos en {columna}.")

    if (df[CAMPOS_PRECIO] <= 0).any().any():
        raise ValueError("Se encontraron precios no positivos.")
    if (df["volume"] < 0).any() or (df["volume"] % 1 != 0).any():
        raise ValueError("El volumen debe ser entero y no negativo.")

    techo = df[["open", "close", "low"]].max(axis=1)
    piso = df[["open", "close", "high"]].min(axis=1)
    if (df["high"] < techo).any() or (df["low"] > piso).any():
        raise ValueError("Hay inconsistencias entre apertura, máximo, mínimo y cierre.")

    esperados = pd.date_range(apertura, cierre, freq="1min", inclusive="left")
    recibidos = pd.DatetimeIndex(df["timestamp_utc"])
    faltantes = esperados.difference(recibidos)
    adicionales = recibidos.difference(esperados)

    if len(faltantes) or len(adicionales):
        raise ValueError(
            f"Cobertura no válida: {len(faltantes)} minutos faltantes "
            f"y {len(adicionales)} fuera de la grilla."
        )

    df["volume"] = df["volume"].astype("int64")
    return df

def transformar_respuesta(respuesta_json, simbolo, apertura, cierre):
    chart = respuesta_json["chart"]
    if not isinstance(chart, dict):
        raise ValueError("La respuesta no tiene la estructura chart esperada.")
    if chart.get("error"):
        raise ValueError(f"Yahoo devolvió un error: {chart['error']}")
    if not chart.get("result"):
        raise ValueError("Yahoo no devolvió resultados para la sesión.")

    resultado = chart["result"][0]
    metadatos = resultado["meta"]
    if metadatos.get("symbol", "").upper() != simbolo:
        raise ValueError("El símbolo de la respuesta no coincide con el solicitado.")
    if metadatos.get("instrumentType") != "EQUITY":
        raise ValueError("El instrumento no es una acción.")
    if metadatos.get("exchangeName") not in ("NMS", "NGM", "NCM"):
        raise ValueError("Este caso utiliza acciones de Nasdaq.")
    if metadatos.get("exchangeTimezoneName") != ZONA_MERCADO:
        raise ValueError("La zona del instrumento no corresponde al alcance del ejercicio.")
    if metadatos.get("dataGranularity") != INTERVALO:
        raise ValueError("La respuesta no contiene el intervalo solicitado.")

    marcas = resultado.get("timestamp", [])
    precios = resultado["indicators"]["quote"][0]
    df = pd.DataFrame({columna: precios[columna] for columna in CAMPOS_VALOR})
    df["timestamp_utc"] = pd.to_datetime(marcas, unit="s", utc=True)

    dentro = (df["timestamp_utc"] >= apertura) & (df["timestamp_utc"] < cierre)
    descartados = int((~dentro).sum())
    df = validar_velas(df.loc[dentro], apertura, cierre)
    return df, metadatos, descartados