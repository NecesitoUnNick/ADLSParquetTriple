"""
Asynchronous logging module for the application.

This module implements a queue-based logging system to write request logs
to Azure Data Lake Storage without blocking the API response. A background
worker task processes the queue, ensuring that logs are written sequentially.
"""

import asyncio
import datetime
import json
import logging
from typing import Any, Dict, Optional

from app.core.config import settings
from app.services.azure_client import write_log_async

# A queue to hold log messages before they are written to Azure.
# This decouples the request processing from the log writing I/O
# and ensures logs are written sequentially to a single file.
log_queue: asyncio.Queue = asyncio.Queue()

# A handle for the background worker task.
_log_worker_task: Optional[asyncio.Task] = None

# Standard logger for console output, e.g., for errors in the logging process itself.
console_logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


async def log_worker():
    """
    A background worker that pulls log messages from a queue and writes them to Azure.

    This coroutine runs in an infinite loop, waiting for messages to appear on the
    `log_queue`. It formats them and sends them to Azure Data Lake.
    """
    while True:
        try:
            log_message = await log_queue.get()

            # Construct file path from template, e.g., "fast-parquet-api/2025/09/19/log.jsonl"
            now = datetime.datetime.now(datetime.UTC)
            file_path = settings.LOG_FILE_PATH_TEMPLATE.format(
                year=now.strftime("%Y"),
                month=now.strftime("%m"),
                day=now.strftime("%d"),
            )

            # Convert dict to a JSON line and encode to bytes
            log_line = (json.dumps(log_message) + "\n").encode("utf-8")

            await write_log_async(file_path=file_path, log_data=log_line)

        except asyncio.CancelledError:
            # The task was cancelled, which is the signal to shut down.
            console_logger.info("Log worker is shutting down.")
            break
        except Exception as e:
            # If writing to Azure fails, log the error to the console.
            console_logger.error(f"Failed to write log to Azure: {e}", exc_info=True)
        finally:
            # Signal that the queue item has been processed.
            log_queue.task_done()


async def queue_log_message(
    client_ip: str,
    request_path: str,
    request_params: Dict[str, Any],
    response_summary: Dict[str, Any],
    processing_time_ms: float,
):
    """
    Constructs a log message and puts it onto the asynchronous queue.

    Args:
        client_ip: The IP address of the client making the request.
        request_path: The path of the request.
        request_params: The query parameters of the request.
        response_summary: A summary of the response payload (e.g., record count).
        processing_time_ms: The total time taken to process the request in ms.
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
    Starts the background log worker task.
    This should be called during application startup.
    """
    global _log_worker_task
    if _log_worker_task is None or _log_worker_task.done():
        _log_worker_task = asyncio.create_task(log_worker())
        console_logger.info("Asynchronous log worker started.")


async def stop_log_worker():
    """
    Stops the background log worker task gracefully.
    This should be called during application shutdown.
    """
    global _log_worker_task
    if _log_worker_task and not _log_worker_task.done():
        console_logger.info("Stopping log worker...")
        # Wait for the queue to be empty before cancelling.
        await log_queue.join()
        # Cancel the worker task.
        _log_worker_task.cancel()
        # Wait for the task to acknowledge cancellation.
        try:
            await _log_worker_task
        except asyncio.CancelledError:
            pass  # This is the expected outcome.
        _log_worker_task = None
        console_logger.info("Log worker stopped gracefully.")
