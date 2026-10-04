from configuracion import CARPETA_DATA, CARPETA_LOGS, CARPETA_CONTROL, FECHA_INICIO, SIMBOLO, INTERVALO, CALENDARIO, ZONA_MERCADO, PAUSA_SEGUNDOS, MAX_CONSULTAS
from pipeline import ejecutar_pipeline


def crear_carpetas():
    """
    Crea las carpetas necesarias para el proyecto si no existen.
    """
    for carpeta in [CARPETA_DATA, CARPETA_LOGS, CARPETA_CONTROL]:
        carpeta.mkdir(parents=True, exist_ok=True)

def main():
    """
    Función principal para ejecutar la creación de carpetas.
    """
    crear_carpetas()
    print("Carpetas creadas o ya existentes:")
    print(f"- Datos: {CARPETA_DATA}")
    print(f"- Logs: {CARPETA_LOGS}")
    print(f"- Control: {CARPETA_CONTROL}")

    print("Iniciando proceso")
    print("Simbolo:", SIMBOLO)
    print("Fecha inicial:", FECHA_INICIO)

    resumen = ejecutar_pipeline(SIMBOLO, FECHA_INICIO)

    if resumen.empty:
        print("No hay sesiones para procesar.")
        return
    print("Resumen de la ejecución:")
    columnas = ["fecha","estado", "filas", "detalle"]

    print(resumen[columnas].to_string(index=False))

    estados_con_problemas = ['sin_historico', 'error', 'archivo_invalido','pausa_activa','limite_consultas','error_solicitud','error_disco']

    hubo_problemas = resumen['estado'].isin(estados_con_problemas).any()
    if hubo_problemas:
        print("Se encontraron problemas durante la ejecución. Revisar los logs para más detalles.")
        print("Estados con problemas:")
        print(hubo_problemas)


if __name__ == "__main__":
    main()