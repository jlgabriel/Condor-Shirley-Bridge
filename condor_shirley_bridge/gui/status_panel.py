#!/usr/bin/env python3

"""
Status Panel for Condor-Shirley-Bridge
Displays real-time status information for the bridge components.

Part of the Condor-Shirley-Bridge project.
"""

import tkinter as tk
from tkinter import ttk
import logging
from typing import Dict, Any, Optional
import time
import math

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('gui.status_panel')


class StatusPanel:
    """
    Panel that displays status information for the bridge components.
    
    Shows connection status, data rates, and flight data.
    """
    def __init__(self, parent):
        """
        Initialize the status panel.
        
        Args:
            parent: Parent widget
        """
        self.parent = parent
        
        # Create the main frame
        self.frame = ttk.Frame(parent, padding="10")
        
        # Split into left and right sides
        self.left_frame = ttk.Frame(self.frame)
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.right_frame = ttk.Frame(self.frame)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Create connection status panel (left side)
        self._create_connection_panel()
        
        # Create flight data panel (right side)
        self._create_flight_data_panel()
    
    def _create_connection_panel(self) -> None:
        """Create the connection status panel."""
        # Connection status frame
        self.conn_frame = ttk.LabelFrame(self.left_frame, text="Connection Status", padding="10")
        self.conn_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Bridge status
        self.bridge_frame = ttk.Frame(self.conn_frame)
        self.bridge_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(self.bridge_frame, text="Bridge Status:").pack(side=tk.LEFT)
        self.bridge_status = ttk.Label(self.bridge_frame, text="Stopped")
        self.bridge_status.pack(side=tk.RIGHT)
        
        # Uptime
        self.uptime_frame = ttk.Frame(self.conn_frame)
        self.uptime_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(self.uptime_frame, text="Uptime:").pack(side=tk.LEFT)
        self.uptime_value = ttk.Label(self.uptime_frame, text="00:00:00")
        self.uptime_value.pack(side=tk.RIGHT)
        
        # Separator
        ttk.Separator(self.conn_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        # Serial status
        self.serial_frame = ttk.LabelFrame(self.conn_frame, text="Serial (NMEA)", padding="5")
        self.serial_frame.pack(fill=tk.X, pady=5)
        
        # Serial port
        serial_port_frame = ttk.Frame(self.serial_frame)
        serial_port_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(serial_port_frame, text="Port:").pack(side=tk.LEFT)
        self.serial_port = ttk.Label(serial_port_frame, text="COM4")
        self.serial_port.pack(side=tk.RIGHT)
        
        # Serial status
        serial_status_frame = ttk.Frame(self.serial_frame)
        serial_status_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(serial_status_frame, text="Status:").pack(side=tk.LEFT)
        self.serial_status = ttk.Label(serial_status_frame, text="Disconnected", foreground="red")
        self.serial_status.pack(side=tk.RIGHT)
        
        # Serial data rate
        serial_rate_frame = ttk.Frame(self.serial_frame)
        serial_rate_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(serial_rate_frame, text="Data Rate:").pack(side=tk.LEFT)
        self.serial_rate = ttk.Label(serial_rate_frame, text="0 lines/sec")
        self.serial_rate.pack(side=tk.RIGHT)
        
        # UDP status
        self.udp_frame = ttk.LabelFrame(self.conn_frame, text="UDP (Condor)", padding="5")
        self.udp_frame.pack(fill=tk.X, pady=5)
        
        # UDP port
        udp_port_frame = ttk.Frame(self.udp_frame)
        udp_port_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(udp_port_frame, text="Port:").pack(side=tk.LEFT)
        self.udp_port = ttk.Label(udp_port_frame, text="55278")
        self.udp_port.pack(side=tk.RIGHT)
        
        # UDP status
        udp_status_frame = ttk.Frame(self.udp_frame)
        udp_status_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(udp_status_frame, text="Status:").pack(side=tk.LEFT)
        self.udp_status = ttk.Label(udp_status_frame, text="Disconnected", foreground="red")
        self.udp_status.pack(side=tk.RIGHT)
        
        # UDP data rate
        udp_rate_frame = ttk.Frame(self.udp_frame)
        udp_rate_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(udp_rate_frame, text="Data Rate:").pack(side=tk.LEFT)
        self.udp_rate = ttk.Label(udp_rate_frame, text="0 msgs/sec")
        self.udp_rate.pack(side=tk.RIGHT)
        
        # WebSocket status
        self.ws_frame = ttk.LabelFrame(self.conn_frame, text="WebSocket (FlyShirley)", padding="5")
        self.ws_frame.pack(fill=tk.X, pady=5)
        
        # WebSocket port
        ws_port_frame = ttk.Frame(self.ws_frame)
        ws_port_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(ws_port_frame, text="Port:").pack(side=tk.LEFT)
        self.ws_port = ttk.Label(ws_port_frame, text="2992")
        self.ws_port.pack(side=tk.RIGHT)
        
        # WebSocket status
        ws_status_frame = ttk.Frame(self.ws_frame)
        ws_status_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(ws_status_frame, text="Status:").pack(side=tk.LEFT)
        self.ws_status = ttk.Label(ws_status_frame, text="Disconnected", foreground="red")
        self.ws_status.pack(side=tk.RIGHT)
        
        # WebSocket clients
        ws_clients_frame = ttk.Frame(self.ws_frame)
        ws_clients_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(ws_clients_frame, text="Clients:").pack(side=tk.LEFT)
        self.ws_clients = ttk.Label(ws_clients_frame, text="0")
        self.ws_clients.pack(side=tk.RIGHT)
        
        # WebSocket broadcast rate
        ws_rate_frame = ttk.Frame(self.ws_frame)
        ws_rate_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(ws_rate_frame, text="Broadcast Rate:").pack(side=tk.LEFT)
        self.ws_rate = ttk.Label(ws_rate_frame, text="0 Hz")
        self.ws_rate.pack(side=tk.RIGHT)
    
    def _create_flight_data_panel(self) -> None:
        """Create the flight data panel."""
        # Flight data frame
        self.flight_frame = ttk.LabelFrame(self.right_frame, text="Flight Data", padding="10")
        self.flight_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Position data
        self.position_frame = ttk.LabelFrame(self.flight_frame, text="Position", padding="5")
        self.position_frame.pack(fill=tk.X, pady=5)
        
        # Latitude
        lat_frame = ttk.Frame(self.position_frame)
        lat_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(lat_frame, text="Latitude:").pack(side=tk.LEFT)
        self.latitude = ttk.Label(lat_frame, text="0.00000°")
        self.latitude.pack(side=tk.RIGHT)
        
        # Longitude
        lon_frame = ttk.Frame(self.position_frame)
        lon_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(lon_frame, text="Longitude:").pack(side=tk.LEFT)
        self.longitude = ttk.Label(lon_frame, text="0.00000°")
        self.longitude.pack(side=tk.RIGHT)
        
        # Altitude
        alt_frame = ttk.Frame(self.position_frame)
        alt_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(alt_frame, text="Altitude MSL:").pack(side=tk.LEFT)
        self.altitude = ttk.Label(alt_frame, text="0 ft")
        self.altitude.pack(side=tk.RIGHT)
        
        # Height AGL
        agl_frame = ttk.Frame(self.position_frame)
        agl_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(agl_frame, text="Height AGL:").pack(side=tk.LEFT)
        self.height_agl = ttk.Label(agl_frame, text="0 ft")
        self.height_agl.pack(side=tk.RIGHT)
        
        # Ground speed
        gs_frame = ttk.Frame(self.position_frame)
        gs_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(gs_frame, text="Ground Speed:").pack(side=tk.LEFT)
        self.ground_speed = ttk.Label(gs_frame, text="0 kts")
        self.ground_speed.pack(side=tk.RIGHT)
        
        # Track
        track_frame = ttk.Frame(self.position_frame)
        track_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(track_frame, text="Track:").pack(side=tk.LEFT)
        self.track = ttk.Label(track_frame, text="0°")
        self.track.pack(side=tk.RIGHT)
        
        # Attitude data
        self.attitude_frame = ttk.LabelFrame(self.flight_frame, text="Attitude", padding="5")
        self.attitude_frame.pack(fill=tk.X, pady=5)
        
        # Heading
        heading_frame = ttk.Frame(self.attitude_frame)
        heading_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(heading_frame, text="Heading:").pack(side=tk.LEFT)
        self.heading = ttk.Label(heading_frame, text="0°")
        self.heading.pack(side=tk.RIGHT)
        
        # Pitch
        pitch_frame = ttk.Frame(self.attitude_frame)
        pitch_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(pitch_frame, text="Pitch:").pack(side=tk.LEFT)
        self.pitch = ttk.Label(pitch_frame, text="0°")
        self.pitch.pack(side=tk.RIGHT)
        
        # Bank
        bank_frame = ttk.Frame(self.attitude_frame)
        bank_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(bank_frame, text="Bank:").pack(side=tk.LEFT)
        self.bank = ttk.Label(bank_frame, text="0°")
        self.bank.pack(side=tk.RIGHT)
        
        # Turn rate
        turn_rate_frame = ttk.Frame(self.attitude_frame)
        turn_rate_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(turn_rate_frame, text="Turn Rate:").pack(side=tk.LEFT)
        self.turn_rate = ttk.Label(turn_rate_frame, text="0°/s")
        self.turn_rate.pack(side=tk.RIGHT)
        
        # G-force
        g_force_frame = ttk.Frame(self.attitude_frame)
        g_force_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(g_force_frame, text="G-Force:").pack(side=tk.LEFT)
        self.g_force = ttk.Label(g_force_frame, text="1.0 G")
        self.g_force.pack(side=tk.RIGHT)
        
        # Soaring data
        self.soaring_frame = ttk.LabelFrame(self.flight_frame, text="Soaring", padding="5")
        self.soaring_frame.pack(fill=tk.X, pady=5)
        
        # IAS
        ias_frame = ttk.Frame(self.soaring_frame)
        ias_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(ias_frame, text="IAS:").pack(side=tk.LEFT)
        self.ias = ttk.Label(ias_frame, text="0 kts")
        self.ias.pack(side=tk.RIGHT)
        
        # Vario
        vario_frame = ttk.Frame(self.soaring_frame)
        vario_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(vario_frame, text="Vario:").pack(side=tk.LEFT)
        self.vario = ttk.Label(vario_frame, text="0.0 m/s")
        self.vario.pack(side=tk.RIGHT)
        
        # Netto vario
        netto_frame = ttk.Frame(self.soaring_frame)
        netto_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(netto_frame, text="Netto:").pack(side=tk.LEFT)
        self.netto = ttk.Label(netto_frame, text="0.0 m/s")
        self.netto.pack(side=tk.RIGHT)
        
        # Average vario
        avg_vario_frame = ttk.Frame(self.soaring_frame)
        avg_vario_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(avg_vario_frame, text="Avg Vario:").pack(side=tk.LEFT)
        self.avg_vario = ttk.Label(avg_vario_frame, text="0.0 m/s")
        self.avg_vario.pack(side=tk.RIGHT)
        
        # Data sources
        self.sources_frame = ttk.LabelFrame(self.flight_frame, text="Data Sources", padding="5")
        self.sources_frame.pack(fill=tk.X, pady=5)
        
        # NMEA source
        nmea_frame = ttk.Frame(self.sources_frame)
        nmea_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(nmea_frame, text="NMEA Data:").pack(side=tk.LEFT)
        self.nmea_status = ttk.Label(nmea_frame, text="No Data", foreground="red")
        self.nmea_status.pack(side=tk.RIGHT)
        
        # Condor UDP source
        udp_frame = ttk.Frame(self.sources_frame)
        udp_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(udp_frame, text="Condor UDP:").pack(side=tk.LEFT)
        self.udp_data_status = ttk.Label(udp_frame, text="No Data", foreground="red")
        self.udp_data_status.pack(side=tk.RIGHT)
    
    def update_status(self, status: Dict[str, Any]) -> None:
        """
        Update the status display with current bridge status.
        
        Args:
            status: Bridge status dictionary
        """
        if not status:
            return
        
        # Update bridge status
        running = status.get('running', False)
        self.bridge_status.config(
            text="Running" if running else "Stopped",
            foreground="green" if running else "red"
        )
        
        # Update uptime
        uptime_secs = status.get('uptime', 0)
        hours, remainder = divmod(int(uptime_secs), 3600)
        minutes, seconds = divmod(remainder, 60)
        self.uptime_value.config(text=f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        
        # Update serial status
        if 'serial' in status and status['serial']:
            serial = status['serial']
            
            # Port
            self.serial_port.config(text=serial.get('port', 'Unknown'))
            
            # Connection status
            connected = serial.get('connected', False)
            self.serial_status.config(
                text="Connected" if connected else "Disconnected",
                foreground="green" if connected else "red"
            )
            
            # Data rate
            lines_per_sec = serial.get('data_rate_lps', 0)
            self.serial_rate.config(text=f"{lines_per_sec:.1f} lines/sec")
        
        # Update UDP status
        if 'udp' in status and status['udp']:
            udp = status['udp']
            
            # Port
            self.udp_port.config(text=str(udp.get('port', 0)))
            
            # Connection status
            bound = udp.get('bound', False)
            self.udp_status.config(
                text="Bound" if bound else "Disconnected",
                foreground="green" if bound else "red"
            )
            
            # Data rate
            msgs_per_sec = udp.get('data_rate_mps', 0)
            self.udp_rate.config(text=f"{msgs_per_sec:.1f} msgs/sec")
        
        # Update WebSocket status
        if 'websocket' in status and status['websocket']:
            ws = status['websocket']
            
            # Port
            self.ws_port.config(text=str(ws.get('port', 0)))
            
            # Connection status
            ws_running = ws.get('running', False)
            self.ws_status.config(
                text="Running" if ws_running else "Stopped",
                foreground="green" if ws_running else "red"
            )
            
            # Clients
            clients = ws.get('connections', 0)
            self.ws_clients.config(text=str(clients))
            
            # Broadcast rate
            broadcast_hz = ws.get('broadcast_frequency', 0)
            self.ws_rate.config(text=f"{broadcast_hz:.1f} Hz")
        
        # Update flight data if available
        sim_data = status.get('data', {})
        if not sim_data and 'sim_data' in status:
            # Get flight data from data sources
            nmea_active = False
            udp_active = False
            
            if 'sim_data' in status:
                data_sources = status['sim_data']
                
                # Check NMEA status
                if 'nmea' in data_sources:
                    nmea = data_sources['nmea']
                    nmea_active = nmea.get('fresh', False)
                    self.nmea_status.config(
                        text="Active" if nmea_active else "No Data",
                        foreground="green" if nmea_active else "red"
                    )
                
                # Check UDP status
                if 'condor_udp' in data_sources:
                    udp = data_sources['condor_udp']
                    udp_active = udp.get('fresh', False)
                    self.udp_data_status.config(
                        text="Active" if udp_active else "No Data",
                        foreground="green" if udp_active else "red"
                    )
        
        # Get flight data - either from 'data' key or directly from status
        # We check multiple keys that could have the same info
        flight_data = sim_data if sim_data else status
        
        # Update position data
        if 'latitude' in flight_data:
            self.latitude.config(text=f"{flight_data['latitude']:.5f}°")
        
        if 'longitude' in flight_data:
            self.longitude.config(text=f"{flight_data['longitude']:.5f}°")
        
        if 'altitude_msl' in flight_data:
            alt_ft = flight_data['altitude_msl'] * 3.28084  # m to ft
            self.altitude.config(text=f"{alt_ft:.0f} ft")
        
        if 'height_agl' in flight_data:
            agl_ft = flight_data['height_agl'] * 3.28084  # m to ft
            self.height_agl.config(text=f"{agl_ft:.0f} ft")
        
        if 'ground_speed' in flight_data:
            self.ground_speed.config(text=f"{flight_data['ground_speed']:.1f} kts")
        
        if 'track_true' in flight_data:
            self.track.config(text=f"{flight_data['track_true']:.1f}°")
        
        # Update attitude data
        if 'heading' in flight_data:
            self.heading.config(text=f"{flight_data['heading']:.1f}°")
        elif 'yaw_deg' in flight_data:
            self.heading.config(text=f"{flight_data['yaw_deg']:.1f}°")
        
        if 'pitch_deg' in flight_data:
            self.pitch.config(text=f"{flight_data['pitch_deg']:.1f}°")
        
        if 'bank_deg' in flight_data:
            self.bank.config(text=f"{flight_data['bank_deg']:.1f}°")
        
        if 'turn_rate' in flight_data:
            self.turn_rate.config(text=f"{flight_data['turn_rate']:.1f}°/s")
        
        if 'g_force' in flight_data:
            self.g_force.config(text=f"{flight_data['g_force']:.1f} G")
        
        # Update soaring data
        if 'ias' in flight_data:
            self.ias.config(text=f"{flight_data['ias']:.1f} kts")
        elif 'ias_kts' in flight_data:
            self.ias.config(text=f"{flight_data['ias_kts']:.1f} kts")
        
        if 'vario' in flight_data:
            self.vario.config(text=f"{flight_data['vario']:.1f} m/s")
        elif 'vario_mps' in flight_data:
            self.vario.config(text=f"{flight_data['vario_mps']:.1f} m/s")
        
        if 'netto_vario_mps' in flight_data:
            self.netto.config(text=f"{flight_data['netto_vario_mps']:.1f} m/s")
        
        if 'avg_vario' in flight_data:
            self.avg_vario.config(text=f"{flight_data['avg_vario']:.1f} m/s")


# Example usage:
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Status Panel Test")
    
    # Create a notebook to simulate the parent
    notebook = ttk.Notebook(root)
    notebook.pack(fill=tk.BOTH, expand=True)
    
    # Create the status panel
    status_panel = StatusPanel(notebook)
    notebook.add(status_panel.frame, text="Status")
    
    # Simulate status updates
    def update_test():
        # Create a test status dictionary
        status = {
            "running": True,
            "uptime": time.time() % 86400,  # Cycle through a day
            "error_count": 0,
            "serial": {
                "port": "COM4",
                "connected": True,
                "data_rate_lps": 5.0,
            },
            "udp": {
                "port": 55278,
                "bound": True,
                "data_rate_mps": 10.0,
            },
            "websocket": {
                "port": 2992,
                "running": True,
                "connections": 1,
                "broadcast_frequency": 4.0,
            },
            "sim_data": {
                "nmea": {"fresh": True},
                "condor_udp": {"fresh": True}
            },
            # Flight data
            "latitude": 47.0 + math.sin(time.time() * 0.1) * 0.1,
            "longitude": -122.0 + math.cos(time.time() * 0.1) * 0.1,
            "altitude_msl": 1500.0 + math.sin(time.time() * 0.2) * 100.0,
            "height_agl": 900.0 + math.sin(time.time() * 0.2) * 100.0,
            "ground_speed": 50.0 + math.sin(time.time() * 0.3) * 10.0,
            "track_true": (time.time() * 10) % 360,
            "heading": (time.time() * 5) % 360,
            "pitch_deg": math.sin(time.time()) * 10.0,
            "bank_deg": math.sin(time.time() * 0.5) * 30.0,
            "turn_rate": math.sin(time.time() * 0.7) * 5.0,
            "g_force": 1.0 + math.sin(time.time() * 0.5) * 0.5,
            "ias": 60.0 + math.sin(time.time() * 0.2) * 10.0,
            "vario": math.sin(time.time() * 0.5) * 2.0,
            "netto_vario_mps": math.sin(time.time() * 0.6) * 3.0,
            "avg_vario": math.sin(time.time() * 0.1) * 1.0,
        }
        
        # Update the panel
        status_panel.update_status(status)
        
        # Schedule next update
        root.after(100, update_test)
    
    # Start updates
    update_test()
    
    root.mainloop()
