#!/usr/bin/env python3

"""
Main entry point for Condor-Shirley-Bridge
Parses command line arguments and starts the application
in either GUI or CLI mode.

Part of the Condor-Shirley-Bridge project.
"""

import os
import sys
import argparse
import logging
import asyncio
import signal
import tkinter as tk
from typing import Optional, Dict, Any

# Add parent directory to path so we can import our modules
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Importar configuración centralizada de logs
from condor_shirley_bridge.core.log_config import configure_logging

# Configurar logs con nivel DEBUG para consola (y archivo si está habilitado)
# Esto automáticamente usará INFO para la GUI cuando se inicie
configure_logging(level=logging.DEBUG)

# Crear logger para este módulo
logger = logging.getLogger('main')

# Import from our project structure
from condor_shirley_bridge.core.bridge import Bridge
from condor_shirley_bridge.core.settings import Settings
from condor_shirley_bridge.gui.main_window import MainWindow

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('main')


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Condor-Shirley-Bridge - Connects Condor Soaring Simulator to FlyShirley"
    )
    
    # Mode selection
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Run in command-line mode (no GUI)"
    )
    
    # Settings file
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        help="Path to configuration file"
    )
    
    # Auto-start
    parser.add_argument(
        "--start",
        action="store_true",
        help="Automatically start the bridge on launch"
    )
    
    # Auto-minimized
    parser.add_argument(
        "--minimized",
        action="store_true",
        help="Start minimized (GUI mode only)"
    )
    
    # Logging
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=None,
        help="Set logging level"
    )
    
    parser.add_argument(
        "--log-file",
        type=str,
        help="Log to specified file"
    )
    
    return parser.parse_args()


async def run_cli(bridge: Bridge):
    """
    Run the bridge in command-line mode.
    
    Args:
        bridge: Bridge instance
    """
    logger.info("Starting Condor-Shirley-Bridge in CLI mode")
    
    # Set up signal handlers for graceful shutdown
    loop = asyncio.get_running_loop()
    
    def signal_handler():
        logger.info("Shutdown signal received")
        loop.create_task(bridge.stop())
        loop.stop()
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)
    
    # Start bridge
    await bridge.start()
    
    try:
        logger.info("Bridge running, press Ctrl+C to stop")
        
        # Keep running until stopped
        while bridge.running:
            await asyncio.sleep(1)
            
            # Log status periodically
            if int(asyncio.get_event_loop().time()) % 30 == 0:  # Every 30 seconds
                status = bridge.get_status()
                
                logger.info(f"Bridge Status:")
                logger.info(f"- Running for {status['uptime']:.1f} seconds")
                logger.info(f"- Serial: {status['serial']['connected'] if status['serial'] else 'Disabled'}")
                logger.info(f"- UDP: {status['udp']['bound'] if status['udp'] else 'Disabled'}")
                logger.info(f"- WebSocket: {status['websocket']['connections'] if status['websocket'] else 'Disabled'} clients")
                logger.info(f"- Data active: {status['data_active']}")
    
    except asyncio.CancelledError:
        # Handle cancellation
        pass
    
    finally:
        # Ensure bridge is stopped
        if bridge.running:
            await bridge.stop()
        
        logger.info("Bridge stopped, exiting")


def run_gui(args):
    """
    Run the bridge in GUI mode.
    
    Args:
        args: Command line arguments
    """
    logger.info("Starting Condor-Shirley-Bridge in GUI mode")
    
    # Create root window
    root = tk.Tk()
    
    # Create main window
    app = MainWindow(root)
    
    # Apply command-line overrides
    if args.start:
        # Schedule auto-start after a short delay (to let the UI initialize)
        root.after(1000, app._start_bridge)
    
    if args.minimized:
        # Start minimized
        root.iconify()
    
    # Run the application
    root.mainloop()


def main():
    """Main entry point."""
    # Parse command line arguments
    args = parse_arguments()
    
    # Load settings
    settings = Settings(args.config)
    
    # Apply logging settings from command line
    if args.log_level:
        settings.set('logging', 'level', args.log_level)
    
    if args.log_file:
        settings.set('logging', 'log_to_file', True)
        settings.set('logging', 'log_file_path', args.log_file)
    
    settings.apply_logging_settings()
    
    # Run in appropriate mode
    if args.cli:
        # CLI mode
        bridge = Bridge(args.config)
        asyncio.run(run_cli(bridge))
    else:
        # GUI mode
        run_gui(args)


if __name__ == "__main__":
    main()
