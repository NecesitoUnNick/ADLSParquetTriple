"""
Módulo de logging asíncrono para la aplicación.

Este módulo implementa un sistema de logging basado en una cola para escribir registros
de solicitudes en Azure Data Lake Storage sin bloquear la respuesta de la API. Una tarea
trabajadora en segundo plano procesa la cola, asegurando que los registros se escriban
de forma secuencial.
"""

import asyncio
import datetime
import json
import logging
from typing import Any, Dict, Optional

from app.core.config import settings
from app.services.azure_client import write_log_async

# Una cola para mantener los mensajes de log antes de que se escriban en Azure.
# Esto desacopla el procesamiento de la solicitud de la E/S de escritura de logs
# y asegura que los registros se escriban secuencialmente en un único archivo.
log_queue: asyncio.Queue = asyncio.Queue()

# Un manejador para la tarea trabajadora en segundo plano.
_log_worker_task: Optional[asyncio.Task] = None

# Logger estándar para la salida por consola, ej., para errores en el propio proceso de logging.
console_logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


async def log_worker():
    """
    Un trabajador en segundo plano que extrae mensajes de log de una cola y los escribe en Azure.

    Esta corrutina se ejecuta en un bucle infinito, esperando a que aparezcan mensajes en
    `log_queue`. Los formatea y los envía a Azure Data Lake.
    """
    while True:
        log_message = None
        try:
            log_message = await log_queue.get()

            # Construye la ruta del archivo a partir de la plantilla, ej., "fast-parquet-api/2025/09/19/log.jsonl"
            now = datetime.datetime.now(datetime.UTC)
            file_path = settings.LOG_FILE_PATH_TEMPLATE.format(
                year=now.strftime("%Y"),
                month=now.strftime("%m"),
                day=now.strftime("%d"),
            )

            # Convierte el diccionario a una línea JSON y lo codifica a bytes
            log_line = (json.dumps(log_message) + "\n").encode("utf-8")

            await write_log_async(file_path=file_path, log_data=log_line)

        except asyncio.CancelledError:
            # La tarea fue cancelada, que es la señal para apagarse.
            console_logger.info("El trabajador de logs se está apagando.")
            break
        except Exception as e:
            # Si falla la escritura en Azure, registra el error en la consola.
            console_logger.error(f"Fallo al escribir el log en Azure: {e}", exc_info=True)
        finally:
            # Señala que el elemento de la cola ha sido procesado, solo si se obtuvo uno.
            # Esto evita el error 'task_done() called too many times' si la tarea es cancelada
            # mientras espera en `log_queue.get()`.
            if log_message is not None:
                log_queue.task_done()


async def queue_log_message(
    client_ip: str,
    request_path: str,
    request_params: Dict[str, Any],
    response_summary: Dict[str, Any],
    processing_time_ms: float,
):
    """
    Construye un mensaje de log y lo pone en la cola asíncrona.

    Args:
        client_ip: La dirección IP del cliente que realiza la solicitud.
        request_path: La ruta de la solicitud.
        request_params: Los parámetros de la consulta de la solicitud.
        response_summary: Un resumen de la carga útil de la respuesta (ej., recuento de registros).
        processing_time_ms: El tiempo total que tardó en procesarse la solicitud en ms.
    """
    log_message = {
        "timestamp_utc": datetime.datetime.now(datetime.UTC).isoformat(),
        "client_ip": client_ip,
        "request_path": request_path,
        "request_params": request_params,
        "response_payload_summary": response_summary,
        "processing_time_ms": round(processing_time_ms, 2),
    }
    await log_queue.put(log_message)


def start_log_worker():
    """
    Inicia la tarea trabajadora de logs en segundo plano.
    Debe llamarse durante el inicio de la aplicación.
    """
    global _log_worker_task
    if _log_worker_task is None or _log_worker_task.done():
        _log_worker_task = asyncio.create_task(log_worker())
        console_logger.info("Trabajador de logs asíncrono iniciado.")


async def stop_log_worker():
    """
    Detiene la tarea trabajadora de logs en segundo plano de forma segura.
    Debe llamarse durante el apagado de la aplicación.
    """
    global _log_worker_task
    if _log_worker_task and not _log_worker_task.done():
        console_logger.info("Deteniendo el trabajador de logs...")
        # Espera a que la cola esté vacía antes de cancelar.
        await log_queue.join()
        # Cancela la tarea trabajadora.
        _log_worker_task.cancel()
        # Espera a que la tarea confirme la cancelación.
        try:
            await _log_worker_task
        except asyncio.CancelledError:
            pass  # Este es el resultado esperado.
        _log_worker_task = None
        console_logger.info("Trabajador de logs detenido de forma segura.")
