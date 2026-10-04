# Yahoo Pipeline

## Caso: de Jupyter a un pipeline automatizado de datos bursátiles

Proyecto educativo de ingeniería de datos que transforma un notebook de Jupyter en un conjunto de scripts Python organizados por responsabilidad.

El proceso consulta Yahoo Finance, valida los datos y guarda un archivo JSON por sesión bursátil. En cada ejecución revisa el histórico local e identifica fechas pendientes, sin volver a descargar archivos que ya son válidos.

> Se descargan velas de un minuto: apertura, máximo, mínimo, cierre y volumen (OHLCV). No son operaciones individuales. La frecuencia de los datos es de un minuto; la ejecución del programa puede ser diaria.

## Objetivos de aprendizaje

- Separar un programa en módulos e importar funciones entre archivos.
- Consultar un servicio HTTP con `requests`.
- Transformar y validar datos con `pandas`.
- Implementar una carga incremental que detecte huecos en el histórico.
- Guardar datos y registrar los resultados de cada ejecución.
- Preparar un script para ejecutarlo con el Programador de tareas de Windows.

## Archivos del proyecto

| Archivo | Responsabilidad |
|---|---|
| `main.py` | Crea las carpetas, inicia el proceso y muestra el resumen. |
| `configuracion.py` | Define símbolo, fecha inicial, rutas y límites de consultas. |
| `extraccion.py` | Consulta Yahoo Finance y gestiona las pausas por restricciones HTTP. |
| `transformacion.py` | Interpreta la respuesta y valida las velas. |
| `almacenamiento.py` | Lee y escribe JSON y registra eventos en CSV. |
| `pipeline.py` | Identifica fechas pendientes y coordina las etapas. |
| `requirements.txt` | Declara las dependencias del proyecto. |

Durante la ejecución se crean estas carpetas:

| Carpeta | Contenido |
|---|---|
| `data/AAPL/1m/` | Un JSON por fecha de negociación, por ejemplo `2026-09-21.json`. |
| `logs/` | Archivo `ejecuciones.csv` con los resultados del proceso. |
| `control/` | Archivo `pausa_yahoo.json` cuando se registra una restricción de acceso. |

## Requisitos

- Python 3.10 o superior.
- Conexión a internet para descargar datos.
- Acceso de escritura a la carpeta del proyecto.

Las instrucciones siguientes utilizan Windows y una terminal CMD. En VS Code, selecciona **Command Prompt / Símbolo del sistema** como terminal.

## Instalación y primera ejecución

Descarga o clona el repositorio y abre una terminal dentro de su carpeta. Ejecuta:

```bat
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe main.py
```

Estos comandos crean el entorno virtual, instalan las dependencias y ejecutan el proceso. No es necesario activar el entorno porque se utiliza directamente su ejecutable de Python.

Para las siguientes ejecuciones basta con:

```bat
.venv\Scripts\python.exe main.py
```

## Configuración

Edita `configuracion.py` para cambiar los parámetros del caso:

```python
SIMBOLO = "AAPL"
FECHA_INICIO = "2026-09-21"

PAUSA_SEGUNDOS = 5
MAX_CONSULTAS = 8
PAUSA_BLOQUEO_SEGUNDOS = 15 * 60
```

- `SIMBOLO`: acción que se desea consultar. Este caso valida instrumentos de Nasdaq, como AAPL o MSFT.
- `FECHA_INICIO`: inicio fijo del histórico. No debe cambiarse cada día.
- `PAUSA_SEGUNDOS`: espera entre consultas de una misma ejecución.
- `MAX_CONSULTAS`: máximo de solicitudes por ejecución; las fechas restantes quedan pendientes.
- `PAUSA_BLOQUEO_SEGUNDOS`: espera mínima de respaldo ante restricciones HTTP. El proceso respeta una espera mayor si viene indicada en `Retry-After`.

El intervalo de un minuto, el calendario Nasdaq y la zona `America/New_York` forman parte del diseño de este caso. Cambiarlos requiere revisar también las validaciones.

## Funcionamiento

1. Crea las carpetas necesarias.
2. Obtiene las sesiones bursátiles desde la fecha inicial hasta ayer, según Nueva York.
3. Revisa los archivos existentes y valida su contenido.
4. Identifica sesiones pendientes y fechas fuera de la ventana de recuperación configurada.
5. Consulta las fechas elegibles respetando pausas y límites.
6. Comprueba las columnas, los valores OHLCV, los duplicados y la cobertura de minutos.
7. Guarda cada sesión válida en JSON y registra su resultado.

La fecha del archivo corresponde a la sesión de Nueva York; las marcas de tiempo de las velas se guardan en UTC.

El día actual siempre se excluye, incluso si el mercado ya cerró. Los fines de semana y feriados no generan archivos, aunque una ejecución en esos días puede recuperar sesiones anteriores pendientes.

## Resultados y seguimiento

Consulta la salida de la terminal y `logs/ejecuciones.csv`:

| Estado | Significado |
|---|---|
| `guardado` | Se descargó, validó y guardó la sesión. |
| `existente` | El archivo local es válido y no se volvió a consultar. |
| `sin_historico` | Falta un archivo válido y la fecha supera la ventana de recuperación del caso. |
| `pendiente_revision` | La respuesta o los datos no cumplen las validaciones. |
| `pausa_activa` | Existe una pausa vigente y no se realizan nuevas consultas. |
| `limite_consultas` | Se alcanzó el máximo de solicitudes de la ejecución. |
| `bloqueo_http` | Yahoo respondió con HTTP 401, 403 o 429; se registró una pausa. |
| `error_solicitud` | Ocurrió un error de conexión o HTTP. |
| `error_disco` | Ocurrió un error al guardar los datos. |

`main.py` devuelve código de salida `1` cuando el resumen contiene problemas o pendientes. Esto no elimina los archivos guardados correctamente. Los errores inesperados pueden detener el programa y mostrar su detalle en la terminal sin quedar registrados en el CSV.

Repetir el proceso conserva los JSON válidos, pero agrega nuevos eventos al registro de ejecuciones.

## Ejecución diaria en Windows

Después de comprobar que la ejecución manual funciona, crea una tarea en el **Programador de tareas de Windows**. Configura un desencadenador diario, por ejemplo a las 07:00 si el equipo utiliza la hora de Perú.

En la acción **Iniciar un programa**, utiliza estas rutas de ejemplo:

| Campo | Valor |
|---|---|
| Programa o script | `C:\proyectos\yahoo-pipeline\.venv\Scripts\python.exe` |
| Agregar argumentos | `"C:\proyectos\yahoo-pipeline\main.py"` |
| Iniciar en | `C:\proyectos\yahoo-pipeline` |

Sustituye las rutas por la ubicación real del proyecto. Configura la tarea para que no inicie una nueva instancia si ya hay una en ejecución.

El equipo debe estar disponible y tener conexión a internet. No es necesario mantener VS Code abierto, activar el entorno ni reinstalar los paquetes diariamente.
