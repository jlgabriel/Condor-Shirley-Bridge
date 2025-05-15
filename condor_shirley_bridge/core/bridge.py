#!/usr/bin/env python3

"""
Bridge for Condor-Shirley-Bridge
Main orchestrator that coordinates data flow between components.

Part of the Condor-Shirley-Bridge project.
"""

import asyncio
import logging
import time
import signal
import sys
from typing import Dict, Any, Optional, List, Tuple

# Import from our project structure
from condor_shirley_bridge.parsers.nmea_parser import NMEAParser
from condor_shirley_bridge.parsers.condor_parser import CondorUDPParser
from condor_shirley_bridge.io.serial_reader import SerialReader
from condor_shirley_bridge.io.udp_receiver import UDPReceiver
from condor_shirley_bridge.io.websocket_server import WebSocketServer
from condor_shirley_bridge.core.sim_data import SimData
from condor_shirley_bridge.core.settings import Settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('bridge')


class Bridge:
    """
    Main orchestrator for Condor-Shirley-Bridge.
    
    Coordinates the flow of data between different components:
    - SerialReader: Reads NMEA data from serial port
    - UDPReceiver: Receives UDP data from Condor
    - NMEAParser: Parses NMEA data
    - CondorUDPParser: Parses Condor UDP data
    - SimData: Combines and processes data from different sources
    - WebSocketServer: Broadcasts processed data to clients
    """
    def __init__(self, settings_file: Optional[str] = None):
        """
        Initialize the bridge.
        
        Args:
            settings_file: Path to settings file (optional)
        """
        # Load settings
        self.settings = Settings(settings_file)
        
        # Apply logging settings
        self.settings.apply_logging_settings()
        
        # Initialize parsers
        self.nmea_parser = NMEAParser()
        self.condor_parser = CondorUDPParser()
        
        # Initialize central data model
        self.sim_data = SimData()
        
        # Initialize IO components (but don't start them yet)
        self._init_io_components()
        
        # Flags and state
        self.running = False
        self.startup_time = 0
        self.error_count = 0
        self.main_task = None
    
    def _init_io_components(self) -> None:
        """Initialize IO components based on settings."""
        # Serial Reader
        serial_settings = self.settings.get('serial')
        self.serial_reader = SerialReader(
            port=serial_settings.port,
            baudrate=serial_settings.baudrate,
            timeout=serial_settings.timeout,
            data_callback=self._handle_serial_data
        )
        
        # UDP Receiver
        udp_settings = self.settings.get('udp')
        self.udp_receiver = UDPReceiver(
            host=udp_settings.host,
            port=udp_settings.port,
            buffer_size=udp_settings.buffer_size,
            data_callback=self._handle_udp_data
        )

        # WebSocket Server
        ws_settings = self.settings.get('websocket')
        self.websocket_server = WebSocketServer(
            host=ws_settings.host,
            port=ws_settings.port,
            path=ws_settings.path,
            data_provider=self._get_data_for_websocket,
            compatibility_mode=ws_settings.compatibility_mode  # Nuevo parámetro añadido aquí
        )
        self.websocket_server.set_broadcast_interval(ws_settings.broadcast_interval)
    
    def _handle_serial_data(self, data: str) -> None:
        """
        Process serial data.
        
        Args:
            data: Line of NMEA data
        """
        try:
            # Parse NMEA sentence
            self.nmea_parser.parse_sentence(data)
            
            # Get combined data from parser
            nmea_data = self.nmea_parser.get_combined_data()
            
            # Update simulation data model
            self.sim_data.update_from_nmea(nmea_data)
            
        except Exception as e:
            logger.error(f"Error processing serial data: {e}")
            self.error_count += 1
    
    def _handle_udp_data(self, data: str) -> None:
        """
        Process UDP data.
        
        Args:
            data: UDP message from Condor
        """
        try:
            # Parse UDP message
            self.condor_parser.parse_message(data)
            
            # Get combined data from parser
            udp_data = self.condor_parser.get_combined_data()
            
            # Update simulation data model
            self.sim_data.update_from_condor_udp(udp_data)
            
        except Exception as e:
            logger.error(f"Error processing UDP data: {e}")
            self.error_count += 1

    def _get_data_for_websocket(self) -> Dict[str, Any]:
        """
        Provide data for the WebSocket server.

        Returns:
            dict: Processed data for WebSocket clients
        """
        data = self.sim_data.get_data()
        logger.debug(f"Data for WebSocket: {data}")
        return data
    
    async def start(self) -> None:
        """Start the bridge and all components."""
        if self.running:
            logger.warning("Bridge is already running")
            return
        
        logger.info("Starting Condor-Shirley-Bridge...")
        self.startup_time = time.time()
        self.running = True
        self.error_count = 0
        
        # Start serial reader if enabled
        if self.settings.get('serial', 'enabled'):
            if not self.serial_reader.start_reading():
                logger.error("Failed to start serial reader")
                self.error_count += 1
            else:
                logger.info(f"Serial reader started on port {self.serial_reader.port}")
        else:
            logger.info("Serial reader disabled in settings")
        
        # Start UDP receiver if enabled
        if self.settings.get('udp', 'enabled'):
            if not self.udp_receiver.start_receiving():
                logger.error("Failed to start UDP receiver")
                self.error_count += 1
            else:
                logger.info(f"UDP receiver started on port {self.udp_receiver.port}")
        else:
            logger.info("UDP receiver disabled in settings")
        
        # Start WebSocket server if enabled
        if self.settings.get('websocket', 'enabled'):
            try:
                # Start in a background task
                logger.info("Starting WebSocket server...")
                
                # Create task for WebSocket server
                websocket_task = asyncio.create_task(self.websocket_server.start())
                
                # Wait a moment to let it initialize
                await asyncio.sleep(0.5)
                
                logger.info(f"WebSocket server started on port {self.websocket_server.port}")
                
            except Exception as e:
                logger.error(f"Failed to start WebSocket server: {e}")
                self.error_count += 1
        else:
            logger.info("WebSocket server disabled in settings")
        
        # Start main monitoring loop
        self.main_task = asyncio.create_task(self._main_loop())
        
        logger.info("Bridge started successfully")
    
    async def stop(self) -> None:
        """Stop the bridge and all components."""
        if not self.running:
            logger.warning("Bridge is not running")
            return
        
        logger.info("Stopping Condor-Shirley-Bridge...")
        self.running = False
        
        # Cancel main task
        if self.main_task:
            self.main_task.cancel()
            try:
                await self.main_task
            except asyncio.CancelledError:
                pass
        
        # Stop WebSocket server
        if self.settings.get('websocket', 'enabled'):
            try:
                await self.websocket_server.stop()
                logger.info("WebSocket server stopped")
            except Exception as e:
                logger.error(f"Error stopping WebSocket server: {e}")
        
        # Stop UDP receiver
        if self.settings.get('udp', 'enabled'):
            self.udp_receiver.close()
            logger.info("UDP receiver stopped")
        
        # Stop serial reader
        if self.settings.get('serial', 'enabled'):
            self.serial_reader.close()
            logger.info("Serial reader stopped")
        
        # Reset sim data
        self.sim_data.reset()
        
        logger.info("Bridge stopped successfully")
    
    async def _main_loop(self) -> None:
        """Main monitoring loop that checks component status."""
        try:
            while self.running:
                await self._check_components()
                await asyncio.sleep(1.0)  # Check every second
                
        except asyncio.CancelledError:
            logger.info("Main loop cancelled")
            raise
            
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            self.error_count += 1
    
    async def _check_components(self) -> None:
        """Check the status of all components and handle issues."""
        # Check serial reader
        if self.settings.get('serial', 'enabled'):
            serial_status = self.serial_reader.get_status()
            if not serial_status["connected"]:
                logger.warning("Serial reader disconnected")
                # Could attempt reconnection here
        
        # Check UDP receiver
        if self.settings.get('udp', 'enabled'):
            udp_status = self.udp_receiver.get_status()
            if not udp_status["bound"]:
                logger.warning("UDP receiver not bound")
                # Could attempt rebinding here
        
        # Check if we're receiving data from any source
        if not self.sim_data.is_active():
            data_age = time.time() - self.sim_data.get_last_update_time()
            if data_age > 10.0 and self.sim_data.get_last_update_time() > 0:
                logger.warning(f"No data received for {data_age:.1f} seconds")
        
        # Log component status at lower frequency (every 10 seconds)
        if int(time.time()) % 10 == 0:
            self._log_status()
    
    def _log_status(self) -> None:
        """Log the status of all components."""
        # Get status from components
        serial_status = self.serial_reader.get_status() if self.settings.get('serial', 'enabled') else None
        udp_status = self.udp_receiver.get_status() if self.settings.get('udp', 'enabled') else None
        ws_status = self.websocket_server.get_status() if self.settings.get('websocket', 'enabled') else None
        sim_status = self.sim_data.get_source_status()
        
        # Log status
        logger.debug("Bridge Status:")
        logger.debug(f"  Running: {self.running}")
        logger.debug(f"  Uptime: {time.time() - self.startup_time:.1f} seconds")
        logger.debug(f"  Errors: {self.error_count}")
        
        if serial_status:
            logger.debug("Serial Reader:")
            logger.debug(f"  Connected: {serial_status['connected']}")
            logger.debug(f"  Data: {serial_status['lines_received']} lines, {serial_status['bytes_received']} bytes")
        
        if udp_status:
            logger.debug("UDP Receiver:")
            logger.debug(f"  Bound: {udp_status['bound']}")
            logger.debug(f"  Data: {udp_status['messages_received']} messages, {udp_status['bytes_received']} bytes")
        
        if ws_status:
            logger.debug("WebSocket Server:")
            logger.debug(f"  Running: {ws_status['running']}")
            logger.debug(f"  Clients: {ws_status['connections']}")
            logger.debug(f"  Broadcasts: {ws_status['total_broadcasts']}")
        
        logger.debug("Simulation Data:")
        for source, status in sim_status.items():
            logger.debug(f"  {source}: {'Fresh' if status['fresh'] else 'Stale'}")

    def get_status(self) -> Dict[str, Any]:
        """
        Get the status of the bridge and all components.

        Returns:
            dict: Status information
        """
        # Get component status
        serial_status = self.serial_reader.get_status() if self.settings.get('serial', 'enabled') else None
        udp_status = self.udp_receiver.get_status() if self.settings.get('udp', 'enabled') else None
        ws_status = self.websocket_server.get_status() if self.settings.get('websocket', 'enabled') else None
        sim_status = self.sim_data.get_source_status()

        # Get actual flight data
        flight_data = self.sim_data.get_data()

        # Build status dictionary
        result = {
            "running": self.running,
            "uptime": time.time() - self.startup_time if self.startup_time > 0 else 0,
            "error_count": self.error_count,
            "data_active": self.sim_data.is_active(),
            "data_last_update_ago": time.time() - self.sim_data.get_last_update_time() if self.sim_data.get_last_update_time() > 0 else None,
            "serial": serial_status,
            "udp": udp_status,
            "websocket": ws_status,
            "sim_data": sim_status,
            "data": flight_data  # Add flight data to the response
        }

        return result
    
    def update_settings(self, new_settings: Optional[str] = None) -> bool:
        """
        Update settings and reconfigure components.
        
        Args:
            new_settings: Path to new settings file (optional)
            
        Returns:
            bool: True if settings were updated and applied successfully
        """
        # Already running? Stop first
        was_running = self.running
        if was_running:
            # Create a new event loop for synchronous calls
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Stop the bridge
            loop.run_until_complete(self.stop())
            
            loop.close()
        
        # Load new settings
        if new_settings:
            success = self.settings.load(new_settings)
        else:
            success = self.settings.load()
        
        if not success:
            logger.error("Failed to load new settings")
            return False
        
        # Apply logging settings
        self.settings.apply_logging_settings()
        
        # Reinitialize IO components
        self._init_io_components()
        
        # Restart if was running
        if was_running:
            # Create a new event loop for synchronous calls
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Start the bridge
            loop.run_until_complete(self.start())
            
            loop.close()
        
        logger.info("Settings updated successfully")
        return True


# Example usage:
if __name__ == "__main__":
    # Create bridge
    bridge = Bridge()
    
    # Set up signal handlers for graceful shutdown
    loop = asyncio.get_event_loop()
    
    def signal_handler():
        logger.info("Shutdown signal received")
        loop.create_task(bridge.stop())
        loop.stop()
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)
    
    # Start bridge
    loop.run_until_complete(bridge.start())
    
    try:
        logger.info("Bridge running, press Ctrl+C to stop")
        loop.run_forever()
    finally:
        # Clean up
        loop.close()
        logger.info("Bridge stopped, exiting")
        sys.exit(0)
