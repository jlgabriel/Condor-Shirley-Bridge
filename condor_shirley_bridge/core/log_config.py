#!/usr/bin/env python3

"""
Configuración centralizada de logs para Condor-Shirley-Bridge.
Proporciona funciones para configurar consistentemente el sistema de logs
en toda la aplicación, incluyendo la visualización en la GUI.

Part of the Condor-Shirley-Bridge project.
"""

import logging
import os
from typing import Optional, Dict, Any, List

# Variable global para rastrear el manejador de texto de la GUI
text_handler = None


def configure_logging(
        level: int = logging.INFO,
        log_to_file: bool = False,
        log_file_path: Optional[str] = None,
        max_log_files: int = 5,
        max_log_size_mb: int = 10
) -> None:
    """
    Configura el sistema de logs para toda la aplicación.

    Args:
        level: Nivel de logging (por defecto INFO)
        log_to_file: Si se debe guardar logs en un archivo
        log_file_path: Ruta al archivo de log (opcional)
        max_log_files: Número máximo de archivos de log para rotar
        max_log_size_mb: Tamaño máximo del archivo de log en MB
    """
    # Obtener el logger raíz
    root_logger = logging.getLogger()

    # Guardar los manejadores de texto existentes para restaurarlos después
    text_handlers = []
    for handler in root_logger.handlers[:]:
        if hasattr(handler, 'text_widget'):
            text_handlers.append(handler)
            root_logger.removeHandler(handler)
        else:
            # Eliminar todos los demás manejadores
            root_logger.removeHandler(handler)

    # Configurar el nivel del logger raíz
    root_logger.setLevel(level)

    # Crear formateador estándar
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Agregar manejador de consola
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Agregar manejador de archivo si está habilitado
    if log_to_file and log_file_path:
        try:
            # Asegurar que el directorio existe
            os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

            # Crear manejador de archivo rotativo
            from logging.handlers import RotatingFileHandler
            file_handler = RotatingFileHandler(
                log_file_path,
                maxBytes=max_log_size_mb * 1024 * 1024,
                backupCount=max_log_files
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

            logging.info(f"Logging to file: {log_file_path}")
        except Exception as e:
            logging.error(f"Error setting up file logging: {e}")

    # Restaurar los manejadores de texto
    for handler in text_handlers:
        handler.setLevel(level)
        root_logger.addHandler(handler)

    logging.info(f"Logging system initialized with level {logging.getLevelName(level)}")


def create_text_handler(text_widget, level: int = logging.INFO) -> logging.Handler:
    """
    Crea un manejador de logs para mostrar en un widget de texto de tkinter.

    Args:
        text_widget: Widget de texto de tkinter
        level: Nivel de logging para este manejador

    Returns:
        El manejador de logs creado
    """
    global text_handler

    # Clase de manejador personalizado
    class TextHandler(logging.Handler):
        def __init__(self, text_widget):
            logging.Handler.__init__(self)
            self.text_widget = text_widget

        def emit(self, record):
            msg = self.format(record)

            def append():
                try:
                    self.text_widget.configure(state='normal')
                    self.text_widget.insert('end', msg + '\n')
                    self.text_widget.configure(state='disabled')
                    self.text_widget.see('end')  # Auto-scroll al final
                except Exception:
                    pass  # Ignorar errores si el widget ya no existe

            # Usar after para ejecutar en el hilo principal
            if self.text_widget.winfo_exists():
                self.text_widget.after(0, append)

    # Crear y configurar el manejador
    handler = TextHandler(text_widget)
    handler.setLevel(level)
    handler.setFormatter(
        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )

    # Guardar referencia global
    text_handler = handler

    return handler


def add_text_handler(text_widget, level: int = logging.INFO) -> logging.Handler:
    """
    Agrega un manejador de texto al sistema de logs.

    Args:
        text_widget: Widget de texto de tkinter
        level: Nivel de logging para este manejador

    Returns:
        El manejador de logs agregado
    """
    # Crear el manejador
    handler = create_text_handler(text_widget, level)

    # Agregar al logger raíz
    root_logger = logging.getLogger()

    # Eliminar cualquier manejador de texto existente para evitar duplicados
    for h in root_logger.handlers[:]:
        if hasattr(h, 'text_widget'):
            root_logger.removeHandler(h)

    # Agregar el nuevo manejador
    root_logger.addHandler(handler)

    # Mensaje de inicio
    logging.info("GUI log handler initialized")

    return handler


def set_text_handler_level(level: int) -> None:
    """
    Cambia el nivel del manejador de texto actual.

    Args:
        level: Nuevo nivel de logging
    """
    global text_handler

    if text_handler:
        text_handler.setLevel(level)
        logging.info(f"GUI log level set to {logging.getLevelName(level)}")
    else:
        # Buscar el manejador en el logger raíz
        for handler in logging.getLogger().handlers:
            if hasattr(handler, 'text_widget'):
                handler.setLevel(level)
                logging.info(f"GUI log level set to {logging.getLevelName(level)}")
                return

        logging.warning("No text handler found to change log level")


def remove_text_handler() -> None:
    """Elimina el manejador de texto del logger raíz."""
    global text_handler

    root_logger = logging.getLogger()

    # Eliminar el manejador si existe
    if text_handler:
        root_logger.removeHandler(text_handler)
        text_handler = None

    # Buscar y eliminar otros manejadores de texto
    for handler in root_logger.handlers[:]:
        if hasattr(handler, 'text_widget'):
            root_logger.removeHandler(handler)