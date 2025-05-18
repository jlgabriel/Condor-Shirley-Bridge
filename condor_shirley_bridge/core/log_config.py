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
        level: int = logging.DEBUG,  # Usar DEBUG como predeterminado para la consola
        log_to_file: bool = False,
        log_file_path: Optional[str] = None,
        max_log_files: int = 5,
        max_log_size_mb: int = 10
) -> None:
    """
    Configura el sistema de logs para toda la aplicación.

    Args:
        level: Nivel de logging para la consola (por defecto DEBUG)
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
            # Eliminar los demás manejadores
            root_logger.removeHandler(handler)

    # Configurar el nivel del logger raíz para permitir todos los mensajes que necesitemos
    root_logger.setLevel(min(level, logging.INFO))

    # Crear formateador estándar
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Agregar manejador de consola con el nivel solicitado (normalmente DEBUG)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)  # Usar el nivel solicitado para la consola
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
            file_handler.setLevel(level)  # Usar mismo nivel que la consola
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

            logging.info(f"Logging to file: {log_file_path}")
        except Exception as e:
            logging.error(f"Error setting up file logging: {e}")

    # Restaurar los manejadores de texto con nivel INFO fijo
    for handler in text_handlers:
        # Asegurar que el nivel es INFO para la GUI
        handler.setLevel(logging.INFO)
        root_logger.addHandler(handler)

    logging.info(f"Logging system initialized: console={logging.getLevelName(level)}, GUI=INFO")


def add_text_handler(text_widget) -> logging.Handler:
    """
    Agrega un manejador de texto para la GUI que muestra solo INFO, WARNING y ERROR.

    Args:
        text_widget: Widget de texto tkinter donde mostrar los logs

    Returns:
        El manejador creado
    """
    global text_handler

    class TextHandler(logging.Handler):
        def __init__(self, text_widget):
            logging.Handler.__init__(self)
            self.text_widget = text_widget
            self.setLevel(logging.INFO)  # Nivel fijo en INFO
            self.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            self.max_lines = 1000  # Límite para evitar sobrecarga de memoria

        def emit(self, record):
            msg = self.format(record)

            def append():
                if not self.text_widget.winfo_exists():
                    return

                try:
                    self.text_widget.configure(state='normal')

                    # Colorear según el nivel
                    if record.levelno >= logging.ERROR:
                        self.text_widget.insert('end', msg + '\n', 'error')
                    elif record.levelno >= logging.WARNING:
                        self.text_widget.insert('end', msg + '\n', 'warning')
                    else:
                        self.text_widget.insert('end', msg + '\n', 'info')

                    # Limitar el número de líneas
                    line_count = int(self.text_widget.index('end-1c').split('.')[0])
                    if line_count > self.max_lines:
                        to_delete = line_count - self.max_lines
                        self.text_widget.delete('1.0', f'{to_delete + 1}.0')

                    self.text_widget.configure(state='disabled')
                    self.text_widget.see('end')
                except Exception as e:
                    print(f"Error updating log widget: {e}")

            # Agregar en el hilo principal
            if self.text_widget.winfo_exists():
                self.text_widget.after(0, append)

    try:
        # Configurar etiquetas para colorear mensajes
        text_widget.tag_configure('info', foreground='black')
        text_widget.tag_configure('warning', foreground='orange')
        text_widget.tag_configure('error', foreground='red')
    except Exception as e:
        print(f"Error configuring text tags: {e}")

    # Crear y configurar el manejador
    handler = TextHandler(text_widget)

    # Agregar al logger raíz
    root_logger = logging.getLogger()

    # Eliminar manejadores de texto existentes
    for h in list(root_logger.handlers):
        if hasattr(h, 'text_widget'):
            root_logger.removeHandler(h)

    root_logger.addHandler(handler)
    text_handler = handler

    # Mensaje de inicio
    logging.info("Log view initialized with fixed INFO level")

    return handler


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