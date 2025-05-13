#!/usr/bin/env python3

"""
WebSocket Server for Condor-Shirley-Bridge
Broadcasts simulator data to connected clients via WebSocket,
following the FlyShirley API format.

Part of the Condor-Shirley-Bridge project.
"""

import asyncio
import json
import logging
import time
from typing import Dict, Set, Any, Optional, Callable

import websockets
from websockets.server import WebSocketServerProtocol, serve

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('websocket_server')


class WebSocketServer:
    """
    WebSocket server that broadcasts simulator data to connected clients.

    Compatible with FlyShirley's WebSocket API expectations.
    """

    def __init__(self,
                 host: str = '0.0.0.0',
                 port: int = 2992,
                 path: str = '/api/v1',
                 data_provider: Optional[Callable[[], Dict[str, Any]]] = None):
        """
        Initialize the WebSocket server.

        Args:
            host: Host to bind to ('0.0.0.0' for all interfaces)
            port: WebSocket port to listen on
            path: API endpoint path
            data_provider: Callback function that returns data to broadcast
        """
        self.host = host
        self.port = port
        self.path = path
        self.data_provider = data_provider

        # Set of connected clients
        self.connections: Set[WebSocketServerProtocol] = set()

        # WebSocket server instance
        self.server = None

        # Broadcast control
        self.running = False
        self.broadcast_task = None
        self.broadcast_interval = 0.25  # 4 Hz by default

        # Statistics
        self.total_connections = 0
        self.total_broadcasts = 0
        self.total_bytes_sent = 0
        self.errors = 0
        self.start_time = 0
        self.last_broadcast_time = 0

    async def handler(self, websocket: WebSocketServerProtocol, path: str) -> None:
        """
        Handle a new WebSocket connection.

        Args:
            websocket: The WebSocket connection
            path: The request path
        """
        # Check if path matches our API path
        if not path.endswith(self.path):
            logger.warning(f"Client attempted to connect with incorrect path: {path}")
            await websocket.close(1008, f"Invalid path. Expected {self.path}")
            return

        # Get client info for logging
        client_info = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"

        # Add to connections set
        self.connections.add(websocket)
        self.total_connections += 1
        logger.info(f"Client connected: {client_info}")

        try:
            # Keep the connection alive and listen for client messages
            async for message in websocket:
                # Shirley might send commands or settings changes
                # For now, we just log them
                logger.info(f"Received message from {client_info}: {message[:100]}")

                # In the future, we could add command handling here
                # e.g., process JSON commands that might control the simulator

        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Connection closed normally: {client_info}")

        except Exception as e:
            logger.error(f"Error handling client {client_info}: {e}")
            self.errors += 1

        finally:
            # Always remove the connection from the set
            if websocket in self.connections:
                self.connections.remove(websocket)
            logger.info(f"Client disconnected: {client_info}")

    async def start(self) -> None:
        """Start the WebSocket server."""
        # Create and start the WebSocket server
        self.server = await serve(
            self.handler,
            self.host,
            self.port
        )

        # Start broadcast task
        self.running = True
        self.broadcast_task = asyncio.create_task(self._broadcast_loop())

        self.start_time = time.time()
        logger.info(f"WebSocket server started at ws://{self.host}:{self.port}{self.path}")

        # Keep the server running
        await self.server.wait_closed()

    async def stop(self) -> None:
        """Stop the WebSocket server gracefully."""
        logger.info("Stopping WebSocket server...")

        # Stop broadcast loop
        self.running = False
        if self.broadcast_task:
            try:
                self.broadcast_task.cancel()
                await asyncio.gather(self.broadcast_task, return_exceptions=True)
            except asyncio.CancelledError:
                pass

        # Close all client connections
        close_tasks = []
        for ws in self.connections:
            close_tasks.append(ws.close(1001, "Server shutting down"))

        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)
            self.connections.clear()

        # Close the server
        if self.server:
            self.server.close()
            await self.server.wait_closed()

        logger.info("WebSocket server stopped")

    async def _broadcast_loop(self) -> None:
        """
        Continuously broadcast simulator data to all connected clients.
        """
        try:
            while self.running:
                await self._broadcast_data()
                await asyncio.sleep(self.broadcast_interval)

        except asyncio.CancelledError:
            logger.info("Broadcast loop cancelled")
            raise

        except Exception as e:
            logger.error(f"Error in broadcast loop: {e}")
            self.errors += 1
            raise

    async def _broadcast_data(self) -> None:
        """
        Broadcast data to all connected clients once.
        """
        # Skip if no connections
        if not self.connections:
            return

        # Skip if no data provider
        if not self.data_provider:
            return

        try:
            # Get data from provider
            sim_data = self.data_provider()

            # Skip if no data available
            if not sim_data:
                return

            # Convert to FlyShirley expected format
            formatted_data = self._format_for_shirley(sim_data)

            # JSON encode
            message = json.dumps(formatted_data)
            message_bytes = len(message.encode('utf-8'))

            # Send to all clients
            stale_connections = []
            for ws in self.connections:
                try:
                    await ws.send(message)
                except websockets.exceptions.ConnectionClosed:
                    stale_connections.append(ws)
                except Exception as e:
                    logger.error(f"Error sending to {ws.remote_address}: {e}")
                    stale_connections.append(ws)
                    self.errors += 1

            # Remove stale connections
            for ws in stale_connections:
                if ws in self.connections:
                    self.connections.remove(ws)

            # Update statistics
            self.total_broadcasts += 1
            self.total_bytes_sent += message_bytes * (len(self.connections) + len(stale_connections))
            self.last_broadcast_time = time.time()

        except Exception as e:
            logger.error(f"Error broadcasting data: {e}")
            self.errors += 1

    def _format_for_shirley(self, sim_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format simulator data according to FlyShirley API expectations.

        Args:
            sim_data: Raw simulator data

        Returns:
            dict: Formatted data for FlyShirley
        """
        # Prepare position data
        position = {
            "latitudeDeg": sim_data.get("latitude", 0.0),
            "longitudeDeg": sim_data.get("longitude", 0.0),
            "mslAltitudeFt": sim_data.get("altitude_msl", 0.0) * 3.28084,  # m to ft
            "gpsGroundSpeedKts": sim_data.get("ground_speed", 0.0),
            "trueTrackDeg": sim_data.get("track_true", 0.0),
        }

        # Add optional AGL height if available
        if "height_agl" in sim_data:
            position["aglAltitudeFt"] = sim_data["height_agl"] * 3.28084  # m to ft

        # Prepare attitude data
        attitude = {
            "rollAngleDegRight": sim_data.get("bank_deg", 0.0),
            "pitchAngleDegUp": sim_data.get("pitch_deg", 0.0),
            "trueHeadingDeg": sim_data.get("heading", sim_data.get("yaw_deg", 0.0)),
        }

        # Add optional yaw string if available
        if "yawstring_angle_deg" in sim_data:
            attitude["yawStringDeg"] = sim_data["yawstring_angle_deg"]

        # Prepare soaring-specific data
        soaring = {
            "indicatedAirspeedKts": sim_data.get("ias_kts", sim_data.get("ias", 0.0)),
            "totalEnergyVarioFpm": sim_data.get("vario_mps", 0.0) * 196.85,  # m/s to fpm
        }

        # Add optional netto vario if available
        if "netto_vario_mps" in sim_data:
            soaring["nettoVarioFpm"] = sim_data["netto_vario_mps"] * 196.85  # m/s to fpm

        # Add optional average vario if available
        if "avg_vario" in sim_data:
            soaring["averageVarioFpm"] = sim_data["avg_vario"] * 196.85  # m/s to fpm

        # Add optional turn rate if available
        if "turn_rate" in sim_data:
            attitude["turnRateDegPerSec"] = sim_data["turn_rate"]

        # Add optional G-force if available
        if "g_force" in sim_data:
            attitude["gForce"] = sim_data["g_force"]

        # Add environment data if available
        environment = {}
        if "turbulence" in sim_data:
            environment["turbulenceIntensity"] = sim_data["turbulence"]

        # Assemble final data structure
        result = {
            "position": position,
            "attitude": attitude,
            "soaring": soaring
        }

        # Add environment if we have any data
        if environment:
            result["environment"] = environment

        return result

    def set_broadcast_interval(self, interval: float) -> None:
        """
        Set the broadcast interval in seconds.

        Args:
            interval: Interval in seconds (e.g., 0.25 for 4 Hz)
        """
        if interval <= 0:
            raise ValueError("Broadcast interval must be positive")

        self.broadcast_interval = interval
        logger.info(f"Broadcast interval set to {interval} seconds ({1 / interval:.1f} Hz)")

    def set_data_provider(self, provider: Callable[[], Dict[str, Any]]) -> None:
        """
        Set the data provider function.

        Args:
            provider: Function that returns data to broadcast
        """
        self.data_provider = provider

    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the WebSocket server.

        Returns:
            dict: Status information
        """
        now = time.time()
        uptime = now - self.start_time if self.start_time > 0 else 0

        return {
            "host": self.host,
            "port": self.port,
            "path": self.path,
            "running": self.running and self.server is not None,
            "connections": len(self.connections),
            "total_connections": self.total_connections,
            "total_broadcasts": self.total_broadcasts,
            "total_bytes_sent": self.total_bytes_sent,
            "errors": self.errors,
            "uptime_seconds": uptime,
            "broadcast_interval": self.broadcast_interval,
            "broadcast_frequency": 1.0 / self.broadcast_interval if self.broadcast_interval > 0 else 0,
            "last_broadcast_ago": now - self.last_broadcast_time if self.last_broadcast_time > 0 else None,
            "data_provider_set": self.data_provider is not None
        }


# Example usage:
if __name__ == "__main__":
    import random
    import math  # Importación añadida para la función sin()


    # Simple example data provider that generates random flight data
    def random_data_provider():
        return {
            "latitude": 47.0 + random.uniform(-0.1, 0.1),
            "longitude": -122.0 + random.uniform(-0.1, 0.1),
            "altitude_msl": 1000.0 + random.uniform(-10, 10),
            "ground_speed": 50.0 + random.uniform(-5, 5),
            "track_true": (time.time() * 10) % 360,
            "bank_deg": 10.0 * math.sin(time.time()),
            "pitch_deg": 5.0 * math.sin(time.time() * 0.5),
            "heading": (time.time() * 5) % 360,
            "ias": 60.0 + random.uniform(-3, 3),
            "vario_mps": random.uniform(-2, 2),
            "g_force": 1.0 + 0.2 * math.sin(time.time()),
            "turn_rate": 3.0 * math.sin(time.time() * 0.7)
        }


    async def main():
        import math  # Para la función sin() en random_data_provider

        # Create server
        server = WebSocketServer(port=2992, data_provider=random_data_provider)

        # Run in background task so we can still interact
        server_task = asyncio.create_task(server.start())

        try:
            print("Server running at ws://localhost:2992/api/v1")
            print("Press Ctrl+C to stop")

            # Wait for Ctrl+C
            while True:
                await asyncio.sleep(1)
                status = server.get_status()
                print(f"Connections: {status['connections']}, "
                      f"Broadcasts: {status['total_broadcasts']}, "
                      f"Data sent: {status['total_bytes_sent'] / 1024:.1f} KB")

        except KeyboardInterrupt:
            print("\nStopping server...")

        finally:
            # Stop the server
            await server.stop()

            # Cancel the server task
            if not server_task.done():
                server_task.cancel()
                try:
                    await server_task
                except asyncio.CancelledError:
                    pass


    # Run the example
    asyncio.run(main())