#!/usr/bin/env python3

"""
UDP Receiver for Condor-Shirley-Bridge
Receives Condor Soaring Simulator data via UDP and
forwards it to a parser for processing.

Part of the Condor-Shirley-Bridge project.
"""

import socket
import threading
import time
import asyncio
from typing import Optional, Callable, Any, Dict, Union
import queue
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('udp_receiver')


class UDPReceiver:
    """
    Receives UDP messages from Condor Soaring Simulator and 
    passes them to a callback function for processing.
    """
    def __init__(self,
                 host: str = '0.0.0.0',
                 port: int = 55278,
                 buffer_size: int = 65535,
                 data_callback: Optional[Callable[[str], Any]] = None,
                 max_retries: int = 5,
                 retry_delay: float = 2.0):
        """
        Initialize the UDP receiver.

        Args:
            host: Host to bind to ('0.0.0.0' for all interfaces)
            port: UDP port to listen on
            buffer_size: Size of the receive buffer
            data_callback: Callback function to process received data
            max_retries: Maximum number of reconnection attempts (default: 5)
            retry_delay: Initial delay between reconnection attempts in seconds (default: 2.0)
        """
        self.host = host
        self.port = port
        self.buffer_size = buffer_size
        self.data_callback = data_callback
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # UDP socket
        self.socket: Optional[socket.socket] = None

        # Thread for receiving UDP messages
        self.receive_thread: Optional[threading.Thread] = None
        self.running = False

        # Queue for storing UDP messages (for async interface)
        self.data_queue = queue.Queue(maxsize=100)

        # Statistics
        self.bytes_received = 0
        self.messages_received = 0
        self.start_time = 0
        self.error_count = 0
        self.last_received_time = 0
        self.reconnect_attempts = 0
    
    def open(self) -> bool:
        """
        Open the UDP socket and bind to the specified host and port.
        
        Returns:
            bool: True if socket opened and bound successfully, False otherwise
        """
        try:
            # Create UDP socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            # Enable address reuse (helpful for quick restarts)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Set socket timeout (to allow clean shutdown)
            self.socket.settimeout(0.5)
            
            # Bind to specified host and port
            self.socket.bind((self.host, self.port))
            
            logger.info(f"UDP socket bound to {self.host}:{self.port}")
            self.start_time = time.time()
            self.last_received_time = 0
            return True
                
        except OSError as e:
            logger.error(f"Error opening UDP socket: {e}")
            self.error_count += 1
            return False

    async def auto_reconnect(self) -> bool:
        """
        Attempt to reconnect automatically with exponential backoff.

        Returns:
            bool: True if reconnection was successful, False otherwise
        """
        self.reconnect_attempts = 0

        while self.reconnect_attempts < self.max_retries and self.running:
            # Calculate delay with exponential backoff
            delay = self.retry_delay * (2 ** self.reconnect_attempts)
            logger.info(f"Reconnection attempt {self.reconnect_attempts + 1}/{self.max_retries} "
                       f"for UDP socket {self.host}:{self.port} in {delay:.1f}s")

            await asyncio.sleep(delay)

            # Attempt to reconnect
            if self.open():
                logger.info(f"UDP socket {self.host}:{self.port} reconnected successfully")
                self.reconnect_attempts = 0
                return True

            self.reconnect_attempts += 1

        if self.reconnect_attempts >= self.max_retries:
            logger.error(f"Failed to reconnect UDP socket {self.host}:{self.port} after {self.max_retries} attempts")

        return False

    def close(self) -> None:
        """Close the UDP socket and stop the receive thread."""
        self.running = False
        
        # Wait for receive thread to finish
        if self.receive_thread and self.receive_thread.is_alive():
            self.receive_thread.join(timeout=2.0)
        
        # Close UDP socket
        if self.socket:
            try:
                self.socket.close()
                logger.info(f"UDP socket closed")
            except OSError as e:
                logger.error(f"Error closing UDP socket: {e}")
    
    def start_receiving(self) -> bool:
        """
        Start receiving UDP messages in a separate thread.
        
        Returns:
            bool: True if receiving started successfully, False otherwise
        """
        if not self.socket:
            if not self.open():
                return False
        
        self.running = True
        self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self.receive_thread.start()
        logger.info(f"Started receiving UDP messages on {self.host}:{self.port}")
        return True
    
    def _receive_loop(self) -> None:
        """
        Main loop for receiving UDP messages.
        Runs in a separate thread.
        """
        if not self.socket:
            logger.error("UDP socket not initialized")
            return
        
        while self.running:
            try:
                # Receive message from UDP socket
                data, addr = self.socket.recvfrom(self.buffer_size)
                
                if data:
                    # Decode bytes to string
                    decoded_message = data.decode('utf-8', errors='ignore')
                    
                    # Update statistics
                    self.bytes_received += len(data)
                    self.messages_received += 1
                    self.last_received_time = time.time()
                    
                    # Put the message in the queue for async interface
                    self.data_queue.put(decoded_message)
                    
                    # Call the callback function if provided
                    if self.data_callback:
                        try:
                            self.data_callback(decoded_message)
                        except Exception as e:
                            logger.error(f"Error in callback: {e}")
                            self.error_count += 1
                
            except socket.timeout:
                # Socket timeout is expected (for clean shutdown)
                continue
                
            except OSError as e:
                # Only log if we're still supposed to be running
                if self.running:
                    logger.error(f"UDP receive error: {e}")
                    self.error_count += 1
                # Break out of the loop on socket error
                break
                
            except Exception as e:
                logger.error(f"Unexpected error in receive loop: {e}")
                self.error_count += 1
                # Continue receiving despite other errors
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the UDP receiver.
        
        Returns:
            dict: Status information
        """
        now = time.time()
        uptime = now - self.start_time if self.start_time > 0 else 0
        
        return {
            "host": self.host,
            "port": self.port,
            "bound": bool(self.socket),
            "running": self.running and bool(self.receive_thread and self.receive_thread.is_alive()),
            "bytes_received": self.bytes_received,
            "messages_received": self.messages_received,
            "error_count": self.error_count,
            "uptime_seconds": uptime,
            "data_rate_bps": self.bytes_received / uptime if uptime > 0 else 0,
            "data_rate_mps": self.messages_received / uptime if uptime > 0 else 0,
            "last_received_ago": now - self.last_received_time if self.last_received_time > 0 else None
        }
    
    def is_receiving_data(self) -> bool:
        """
        Check if we're actively receiving data (in the last 5 seconds).
        
        Returns:
            bool: True if receiving data, False otherwise
        """
        if not self.last_received_time:
            return False
        
        return (time.time() - self.last_received_time) < 5.0
    
    def set_port(self, port: int) -> bool:
        """
        Change the UDP port. Will reopen the socket if already open.
        
        Args:
            port: New UDP port to use
            
        Returns:
            bool: True if successful, False otherwise
        """
        was_running = self.running
        
        # Stop current receiving if running
        if was_running:
            self.close()
        
        # Set new port
        self.port = port
        
        # Restart if it was running
        if was_running:
            return self.start_receiving()
        
        return True
    
    def set_callback(self, callback: Callable[[str], Any]) -> None:
        """
        Set or change the data callback function.
        
        Args:
            callback: New callback function
        """
        self.data_callback = callback
    
    async def receive_async(self) -> Optional[str]:
        """
        Asynchronously receive a UDP message (via queue).
        For use with asyncio-based applications.
        
        Returns:
            str or None: A UDP message if available, None if no data or error
        """
        try:
            # Use asyncio to run queue.get in a thread pool
            message = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.data_queue.get(block=True, timeout=0.1)
            )
            return message
        except queue.Empty:
            return None
        except Exception as e:
            logger.error(f"Error in async receive: {e}")
            return None


# Example usage:
if __name__ == "__main__":
    # Define a simple callback function
    def print_message(message):
        # Print just the first 100 characters to avoid flooding the console
        print(f"UDP Received ({len(message)} bytes): {message[:100]}...")
    
    # Create a UDP receiver
    receiver = UDPReceiver(port=55278, data_callback=print_message)
    
    try:
        # Start receiving
        if receiver.start_receiving():
            print(f"Started listening for UDP messages on port {receiver.port}")
            
            # Run for 30 seconds
            for _ in range(30):
                time.sleep(1)
                status = receiver.get_status()
                
                if receiver.is_receiving_data():
                    print(f"Received {status['messages_received']} messages, {status['bytes_received']} bytes")
                else:
                    print("No data received recently")
        
    except KeyboardInterrupt:
        print("\nReceiving stopped by user")
    
    finally:
        # Always close the connection
        receiver.close()
