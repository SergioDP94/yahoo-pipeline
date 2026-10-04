import re
import time

from datetime import date, timedelta
from uuid import uuid4

import pandas as pd
import pandas_market_calendars as mcal
import requests

from configuracion import (CARPETA_DATA, 
                           CARPETA_CONTROL, 
                           INTERVALO, CALENDARIO, ZONA_MERCADO, PAUSA_SEGUNDOS, MAX_CONSULTAS)
from extraccion import (BloqueoYahoo, consultar_sesion, pausa_vigente)

from almacenamiento import (leer_dia_validado, guardar_dia, registrar_evento)

from transformacion import transformar_respuesta

def preparar_plan(simbolo, fecha_inicio):
    simbolo = simbolo.strip().upper()
    if not re.fullmatch(r"[A-Z][A-Z0-9.-]{0,19}", simbolo):
        raise ValueError("Utiliza un símbolo bursátil simple, como AAPL o MSFT.")

    inicio = date.fromisoformat(fecha_inicio)
    ahora = pd.Timestamp.now(tz="UTC")
    hoy_mercado = ahora.tz_convert(ZONA_MERCADO).date()
    ayer = hoy_mercado - timedelta(days=1)
    carpeta = CARPETA_DATA / simbolo / INTERVALO
    carpeta.mkdir(parents=True, exist_ok=True)

    columnas = ["fecha", "apertura", "cierre", "ruta", "estado", "detalle", "filas"]
    if inicio > ayer:
        return pd.DataFrame(columns=columnas)

    calendario = mcal.get_calendar(CALENDARIO)
    sesiones = calendario.schedule(start_date=inicio, end_date=ayer)
    limite_historico = ahora - pd.Timedelta(days=30)
    plan = []

    for dia, horario in sesiones.iterrows():
        fecha = dia.date().isoformat()
        apertura, cierre = horario["market_open"], horario["market_close"]
        ruta = carpeta / f"{fecha}.json"
        estado, detalle, filas = "pendiente", "Falta el archivo diario.", 0

        if ruta.exists():
            try:
                df = leer_dia_validado(ruta, simbolo, fecha, apertura, cierre)
                estado, detalle, filas = "existente", "Archivo válido; no consultar.", len(df)
            except (ValueError, KeyError, TypeError, OSError, OverflowError) as error:
                detalle = f"Archivo inválido; requiere recuperación: {error}"

        if estado != "existente" and apertura < limite_historico:
            estado = "sin_historico"
            detalle = "Falta un archivo válido y la sesión está fuera de la ventana de 30 días."

        plan.append({
            "fecha": fecha, "apertura": apertura, "cierre": cierre, "ruta": ruta,
            "estado": estado, "detalle": detalle, "filas": filas,
        })
    return pd.DataFrame(plan, columns=columnas)

def ejecutar_pipeline(simbolo, fecha_inicio):
    simbolo = simbolo.strip().upper()
    plan = preparar_plan(simbolo, fecha_inicio)
    ejecucion = uuid4().hex[:12]
    consultas = 0
    resumen = []

    if plan.empty:
        print("No hay sesiones terminadas dentro del rango solicitado.")
        return pd.DataFrame()

    with requests.Session() as sesion:
        sesion.headers.update({"User-Agent": "Mozilla/5.0", "Accept": "application/json"})

        for _, fila in plan.iterrows():
            fecha = fila["fecha"]

            if fila["estado"] in ("existente", "sin_historico"):
                resumen.append(registrar_evento(
                    ejecucion, simbolo, fecha, fila["estado"], fila["detalle"], fila["filas"]
                ))
                continue

            hasta = pausa_vigente()
            if hasta is not None:
                resumen.append(registrar_evento(
                    ejecucion, simbolo, fecha, "pausa_activa", f"No consultar antes de {hasta}."
                ))
                break

            if consultas >= MAX_CONSULTAS:
                resumen.append(registrar_evento(
                    ejecucion, simbolo, fecha, "limite_consultas", "Quedan fechas pendientes."
                ))
                break

            if consultas:
                time.sleep(PAUSA_SEGUNDOS)
            consultas += 1

            try:
                respuesta_json = consultar_sesion(
                    sesion, simbolo, fila["apertura"], fila["cierre"]
                )
                df, metadatos, descartados = transformar_respuesta(
                    respuesta_json, simbolo, fila["apertura"], fila["cierre"]
                )
                guardar_dia(
                    fila["ruta"], simbolo, fecha, df,
                    fila["apertura"], fila["cierre"], metadatos
                )
            except BloqueoYahoo as error:
                resumen.append(registrar_evento(
                    ejecucion, simbolo, fecha, "bloqueo_http", str(error)
                ))
                break
            except requests.RequestException as error:
                resumen.append(registrar_evento(
                    ejecucion, simbolo, fecha, "error_solicitud", str(error)[:300]
                ))
                break
            except (ValueError, KeyError, TypeError, IndexError, OverflowError) as error:
                resumen.append(registrar_evento(
                    ejecucion, simbolo, fecha, "pendiente_revision", str(error)[:300]
                ))
                continue
            except OSError as error:
                resumen.append(registrar_evento(
                    ejecucion, simbolo, fecha, "error_disco", str(error)[:300]
                ))
                break

            resumen.append(registrar_evento(
                ejecucion, simbolo, fecha, "guardado",
                f"JSON validado. Registros fuera de sesión descartados: {descartados}.", len(df)
            ))

    print(f"Consultas HTTP realizadas en esta ejecución: {consultas}")
    return pd.DataFrame(resumen)

