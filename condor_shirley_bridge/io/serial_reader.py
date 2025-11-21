#!/usr/bin/env python3

"""
Serial Reader for Condor-Shirley-Bridge
Reads NMEA data from a serial port (virtual COM port) and
forwards it to a parser for processing.

Part of the Condor-Shirley-Bridge project.
"""

import serial
import time
import threading
import asyncio
from typing import Optional, Callable, Any, Dict
import queue
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('serial_reader')


class SerialReader:
    """
    Reads NMEA data from a serial port and passes it to a callback
    function for processing.
    """
    def __init__(self,
                 port: str = 'COM4',
                 baudrate: int = 4800,
                 timeout: float = 1.0,
                 data_callback: Optional[Callable[[str], Any]] = None,
                 max_retries: int = 5,
                 retry_delay: float = 2.0):
        """
        Initialize the serial reader.

        Args:
            port: The serial port to connect to (e.g., 'COM4', '/dev/ttyS0')
            baudrate: The baudrate to use
            timeout: Read timeout in seconds
            data_callback: Callback function to process received data
            max_retries: Maximum number of reconnection attempts (default: 5)
            retry_delay: Initial delay between reconnection attempts in seconds (default: 2.0)
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.data_callback = data_callback
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Serial connection
        self.serial_conn: Optional[serial.Serial] = None

        # Thread for reading from serial port
        self.read_thread: Optional[threading.Thread] = None
        self.running = False

        # Queue for storing serial data (for async interface)
        self.data_queue = queue.Queue(maxsize=100)

        # Statistics
        self.bytes_received = 0
        self.lines_received = 0
        self.start_time = 0
        self.error_count = 0
        self.last_received_time = 0
        self.reconnect_attempts = 0
    
    def open(self) -> bool:
        """
        Open the serial connection.
        
        Returns:
            bool: True if connection opened successfully, False otherwise
        """
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout
            )
            
            if self.serial_conn.is_open:
                logger.info(f"Serial port {self.port} opened successfully")
                self.start_time = time.time()
                self.last_received_time = 0
                return True
            else:
                logger.error(f"Failed to open serial port {self.port}")
                return False
                
        except serial.SerialException as e:
            logger.error(f"Error opening serial port {self.port}: {e}")
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
                       f"for serial port {self.port} in {delay:.1f}s")

            await asyncio.sleep(delay)

            # Attempt to reconnect
            if self.open():
                logger.info(f"Serial port {self.port} reconnected successfully")
                self.reconnect_attempts = 0
                return True

            self.reconnect_attempts += 1

        if self.reconnect_attempts >= self.max_retries:
            logger.error(f"Failed to reconnect serial port {self.port} after {self.max_retries} attempts")

        return False

    def close(self) -> None:
        """Close the serial connection and stop the read thread."""
        self.running = False
        
        # Wait for read thread to finish
        if self.read_thread and self.read_thread.is_alive():
            self.read_thread.join(timeout=2.0)
        
        # Close serial connection
        if self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.close()
                logger.info(f"Serial port {self.port} closed")
            except serial.SerialException as e:
                logger.error(f"Error closing serial port {self.port}: {e}")
    
    def start_reading(self) -> bool:
        """
        Start reading from the serial port in a separate thread.
        
        Returns:
            bool: True if reading started successfully, False otherwise
        """
        if not self.serial_conn or not self.serial_conn.is_open:
            if not self.open():
                return False
        
        self.running = True
        self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
        self.read_thread.start()
        logger.info(f"Started reading from serial port {self.port}")
        return True
    
    def _read_loop(self) -> None:
        """
        Main loop for reading from the serial port.
        Runs in a separate thread.
        """
        if not self.serial_conn:
            logger.error("Serial connection not initialized")
            return
        
        while self.running and self.serial_conn.is_open:
            try:
                # Read a line from the serial port
                line = self.serial_conn.readline()
                
                if line:
                    # Decode bytes to string and strip whitespace
                    decoded_line = line.decode('ascii', errors='ignore').strip()
                    
                    # Update statistics
                    self.bytes_received += len(line)
                    self.lines_received += 1
                    self.last_received_time = time.time()
                    
                    # Put the line in the queue for async interface
                    self.data_queue.put(decoded_line)
                    
                    # Call the callback function if provided
                    if self.data_callback:
                        try:
                            self.data_callback(decoded_line)
                        except Exception as e:
                            logger.error(f"Error in callback: {e}")
                            self.error_count += 1
                
            except serial.SerialException as e:
                logger.error(f"Serial read error: {e}")
                self.error_count += 1
                # Break out of the loop on serial error
                break
                
            except Exception as e:
                logger.error(f"Unexpected error in read loop: {e}")
                self.error_count += 1
                # Continue reading despite other errors
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the serial reader.
        
        Returns:
            dict: Status information
        """
        now = time.time()
        uptime = now - self.start_time if self.start_time > 0 else 0
        
        return {
            "port": self.port,
            "baudrate": self.baudrate,
            "connected": bool(self.serial_conn and self.serial_conn.is_open),
            "running": self.running and bool(self.read_thread and self.read_thread.is_alive()),
            "bytes_received": self.bytes_received,
            "lines_received": self.lines_received,
            "error_count": self.error_count,
            "uptime_seconds": uptime,
            "data_rate_bps": self.bytes_received / uptime if uptime > 0 else 0,
            "data_rate_lps": self.lines_received / uptime if uptime > 0 else 0,
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
    
    def set_port(self, port: str) -> bool:
        """
        Change the serial port. Will reopen the connection if already open.
        
        Args:
            port: New serial port to use
            
        Returns:
            bool: True if successful, False otherwise
        """
        was_running = self.running
        
        # Stop current reading if running
        if was_running:
            self.close()
        
        # Set new port
        self.port = port
        
        # Restart if it was running
        if was_running:
            return self.start_reading()
        
        return True
    
    def set_baudrate(self, baudrate: int) -> bool:
        """
        Change the baudrate. Will reopen the connection if already open.
        
        Args:
            baudrate: New baudrate to use
            
        Returns:
            bool: True if successful, False otherwise
        """
        was_running = self.running
        
        # Stop current reading if running
        if was_running:
            self.close()
        
        # Set new baudrate
        self.baudrate = baudrate
        
        # Restart if it was running
        if was_running:
            return self.start_reading()
        
        return True
    
    def set_callback(self, callback: Callable[[str], Any]) -> None:
        """
        Set or change the data callback function.
        
        Args:
            callback: New callback function
        """
        self.data_callback = callback
    
    async def read_async(self) -> Optional[str]:
        """
        Asynchronously read a line from the serial port (via queue).
        For use with asyncio-based applications.
        
        Returns:
            str or None: A line of data if available, None if no data or error
        """
        try:
            # Use asyncio to run queue.get in a thread pool
            line = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.data_queue.get(block=True, timeout=0.1)
            )
            return line
        except queue.Empty:
            return None
        except Exception as e:
            logger.error(f"Error in async read: {e}")
            return None


# Example usage:
if __name__ == "__main__":
    # Define a simple callback function
    def print_data(data):
        print(f">> {data}")
    
    # Create a serial reader
    reader = SerialReader(port='COM4', baudrate=4800, data_callback=print_data)
    
    try:
        # Start reading
        if reader.start_reading():
            print(f"Started reading from {reader.port} at {reader.baudrate} baud")
            
            # Run for 30 seconds
            for _ in range(30):
                time.sleep(1)
                status = reader.get_status()
                
                if reader.is_receiving_data():
                    print(f"Received {status['lines_received']} lines, {status['bytes_received']} bytes")
                else:
                    print("No data received recently")
        
    except KeyboardInterrupt:
        print("\nReading stopped by user")
    
    finally:
        # Always close the connection
        reader.close()
