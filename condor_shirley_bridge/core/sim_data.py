#!/usr/bin/env python3

"""
SimData for Condor-Shirley-Bridge
Central data model that combines and processes data
from multiple sources (NMEA, UDP) into a unified
format for transmission to FlyShirley.

Part of the Condor-Shirley-Bridge project.
"""

import time
import threading
import logging
import asyncio
from typing import Dict, Any, Optional, List, Set, Tuple
from dataclasses import dataclass, field
import math
from condor_shirley_bridge import constants

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('sim_data')


@dataclass
class DataSourceStatus:
    """Status information for a data source"""
    name: str
    connected: bool = False
    last_update_time: float = 0.0
    update_count: int = 0
    error_count: int = 0
    data_freshness_threshold: float = constants.DATA_FRESHNESS_THRESHOLD
    
    @property
    def is_fresh(self) -> bool:
        """Check if data is fresh (updated within threshold)"""
        return (time.time() - self.last_update_time) < self.data_freshness_threshold
    
    @property
    def last_update_ago(self) -> float:
        """Get seconds since last update"""
        return time.time() - self.last_update_time if self.last_update_time > 0 else float('inf')
    
    def update(self) -> None:
        """Mark as updated"""
        self.last_update_time = time.time()
        self.update_count += 1
        self.connected = True
    
    def error(self) -> None:
        """Record an error"""
        self.error_count += 1
    
    def disconnect(self) -> None:
        """Mark as disconnected"""
        self.connected = False
        self.last_update_time = 0.0


class SimData:
    """
    Central data model that combines and processes data from multiple sources.
    
    This class maintains the current state of the simulation by integrating
    data from different sources (NMEA, UDP) and providing a unified view.
    It also handles data fusion, interpolation, and validation.
    """
    def __init__(self):
        """Initialize the simulation data model."""
        # Lock for thread safety
        self._lock = threading.RLock()
        
        # Main data storage
        self._data: Dict[str, Any] = {}
        
        # Keep track of sources that have contributed to the data
        self._sources: Dict[str, DataSourceStatus] = {
            "nmea": DataSourceStatus(name="NMEA"),
            "condor_udp": DataSourceStatus(name="Condor UDP")
        }
        
        # For data that changes over time, keep history for interpolation
        self._history: Dict[str, List[Dict[str, Any]]] = {
            "position": [],
            "attitude": [],
            "motion": []
        }
        self._history_max_size = constants.HISTORY_MAX_SIZE
        self._update_counter = 0  # Track updates for periodic cleanup

        # Keep track of available fields from each source
        self._source_fields: Dict[str, Set[str]] = {
            "nmea": set(),
            "condor_udp": set()
        }

        # Timestamp of last update
        self._last_update_time = 0.0
    
    def update_from_nmea(self, nmea_data: Dict[str, Any]) -> None:
        """
        Update the simulation data with NMEA data.

        Args:
            nmea_data: Dictionary of NMEA data from NMEAParser
        """
        with self._lock:
            # Skip if no data
            if not nmea_data:
                return

            # Track fields provided by NMEA
            self._source_fields["nmea"].update(nmea_data.keys())

            # Update the data dictionary
            # We selectively merge, as NMEA data might be incomplete or less accurate for some fields
            self._merge_nmea_data(nmea_data)

            # Update source status
            self._sources["nmea"].update()

            # Update last update time
            self._last_update_time = time.time()

            # Periodic cleanup of old history data
            self._update_counter += 1
            if self._update_counter % constants.HISTORY_CLEANUP_INTERVAL == 0:
                self._cleanup_old_history()
    
    def update_from_condor_udp(self, udp_data: Dict[str, Any]) -> None:
        """
        Update the simulation data with Condor UDP data.

        Args:
            udp_data: Dictionary of UDP data from CondorUDPParser
        """
        with self._lock:
            # Skip if no data
            if not udp_data:
                return

            # Track fields provided by Condor UDP
            self._source_fields["condor_udp"].update(udp_data.keys())

            # Update the data dictionary
            # We selectively merge, as UDP data might be more accurate for some fields
            self._merge_udp_data(udp_data)

            # Update source status
            self._sources["condor_udp"].update()

            # Update last update time
            self._last_update_time = time.time()

            # Periodic cleanup of old history data
            self._update_counter += 1
            if self._update_counter % constants.HISTORY_CLEANUP_INTERVAL == 0:
                self._cleanup_old_history()
    
    def _merge_nmea_data(self, nmea_data: Dict[str, Any]) -> None:
        """
        Merge NMEA data into the central data model.
        NMEA data is authoritative for position, but may be supplemented by UDP data.
        
        Args:
            nmea_data: Dictionary of NMEA data
        """
        # Position data (GPS)
        if "latitude" in nmea_data and "longitude" in nmea_data:
            position = {
                "latitude": nmea_data["latitude"],
                "longitude": nmea_data["longitude"],
                "timestamp": time.time()
            }
            
            # Add altitude if available
            if "altitude_msl" in nmea_data:
                position["altitude_msl"] = nmea_data["altitude_msl"]
            
            # Add ground speed and track if available
            if "ground_speed" in nmea_data:
                position["ground_speed"] = nmea_data["ground_speed"]
            if "track_true" in nmea_data:
                position["track_true"] = nmea_data["track_true"]
            
            # Add GPS-related fields
            for field in ["fix_quality", "satellites", "gps_valid"]:
                if field in nmea_data:
                    position[field] = nmea_data[field]
            
            # Update position in data
            self._data.update(position)
            
            # Add to position history
            self._add_to_history("position", position)
        
        # Soaring data (from LXWP0)
        soaring_fields = ["ias", "baro_altitude", "vario", "avg_vario", "heading", "track_bearing", "turn_rate"]
        for field in soaring_fields:
            if field in nmea_data:
                self._data[field] = nmea_data[field]
        
        # If we have heading from NMEA, add it to attitude data
        if "heading" in nmea_data:
            attitude = {"heading": nmea_data["heading"], "timestamp": time.time()}
            self._add_to_history("attitude", attitude)
    
    def _merge_udp_data(self, udp_data: Dict[str, Any]) -> None:
        """
        Merge Condor UDP data into the central data model.
        UDP data is authoritative for attitude and additional flight data.
        
        Args:
            udp_data: Dictionary of UDP data
        """
        # Attitude data
        attitude_fields = ["yaw_deg", "pitch_deg", "bank_deg", 
                          "quaternion_x", "quaternion_y", "quaternion_z", "quaternion_w",
                          "roll_rate_deg", "pitch_rate_deg", "yaw_rate_deg", 
                          "yawstring_angle_deg"]
        
        attitude = {"timestamp": time.time()}
        has_attitude = False
        
        for field in attitude_fields:
            if field in udp_data:
                attitude[field] = udp_data[field]
                self._data[field] = udp_data[field]
                has_attitude = True
        
        if has_attitude:
            self._add_to_history("attitude", attitude)
        
        # Motion data
        motion_fields = ["sim_time", "ias_kts", "altitude_m", "vario_mps", "evario_mps", 
                        "netto_vario_mps", "accel_x", "accel_y", "accel_z",
                        "vel_x", "vel_y", "vel_z", "g_force", "height_agl", 
                        "wheel_height", "turbulence", "surface_roughness"]
        
        motion = {"timestamp": time.time()}
        has_motion = False
        
        for field in motion_fields:
            if field in udp_data:
                # Some fields may need processing
                if field == "ias_kts" and "ias" not in self._data:
                    # Only use if we don't have IAS from NMEA
                    self._data["ias"] = udp_data[field]
                elif field == "altitude_m" and "altitude_msl" not in self._data:
                    # Only use if we don't have altitude from NMEA
                    self._data["altitude_msl"] = udp_data[field]
                elif field == "vario_mps" and "vario" not in self._data:
                    # Only use if we don't have vario from NMEA
                    self._data["vario"] = udp_data[field]
                else:
                    # All other fields
                    self._data[field] = udp_data[field]
                
                motion[field] = udp_data[field]
                has_motion = True
        
        if has_motion:
            self._add_to_history("motion", motion)
        
        # Settings data
        settings_fields = ["flaps", "mc_setting", "water_ballast", "radio_frequency"]
        for field in settings_fields:
            if field in udp_data:
                self._data[field] = udp_data[field]
        
        # If both UDP and NMEA have contradicting data, prioritize appropriately
        self._resolve_data_conflicts()
    
    def _resolve_data_conflicts(self) -> None:
        """Resolve any conflicts between data sources based on priorities."""
        # For example, prefer NMEA heading if it's fresher
        nmea_fresh = self._sources["nmea"].is_fresh
        udp_fresh = self._sources["condor_udp"].is_fresh
        
        if nmea_fresh and udp_fresh:
            # Both sources are fresh, prioritize:
            # - NMEA for position, ground speed, track
            # - UDP for attitude (except heading if LXWP0 is available)
            # - Prefer LXWP0 for IAS, vario if available
            pass
        
        # If we have ground speed from NMEA but not IAS, estimate IAS
        if "ground_speed" in self._data and "ias" not in self._data:
            # Simple approximation: IAS ~= ground speed
            # In a real implementation, you'd account for wind
            self._data["ias"] = self._data["ground_speed"]
        
        # If we have yaw_deg from UDP but not heading, use yaw as heading
        if "yaw_deg" in self._data and "heading" not in self._data:
            # Convert from -180..180 to 0..360 if needed
            yaw = self._data["yaw_deg"]
            self._data["heading"] = (yaw + 360) % 360
    
    def _add_to_history(self, category: str, data: Dict[str, Any]) -> None:
        """
        Add a data point to the historical record for interpolation.

        Args:
            category: Category of data ('position', 'attitude', 'motion')
            data: Data point to add
        """
        if category in self._history:
            # Ensure the timestamp is included
            if "timestamp" not in data:
                data["timestamp"] = time.time()

            # Add to history
            self._history[category].append(data)

            # Limit history size
            if len(self._history[category]) > self._history_max_size:
                self._history[category].pop(0)

    def _cleanup_old_history(self) -> None:
        """
        Clean up old history entries that exceed the maximum age.
        This prevents memory leaks from stale historical data.
        """
        current_time = time.time()
        max_age = constants.HISTORY_MAX_AGE

        for category in self._history:
            # Remove entries older than max_age
            self._history[category] = [
                entry for entry in self._history[category]
                if current_time - entry.get("timestamp", 0) < max_age
            ]

            # Log cleanup if significant data was removed
            if len(self._history[category]) == 0:
                logger.debug(f"History cleanup: All {category} entries were stale")

    def get_data(self) -> Dict[str, Any]:
        with self._lock:
            # Return a copy to prevent external modification
            data = self._data.copy()
            logger.debug(f"SimData.get_data() returning: {data}")
            return data
    
    def get_source_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get the status of all data sources.
        
        Returns:
            dict: Status of all data sources
        """
        with self._lock:
            result = {}
            for name, source in self._sources.items():
                result[name] = {
                    "connected": source.connected,
                    "fresh": source.is_fresh,
                    "last_update_ago": source.last_update_ago,
                    "update_count": source.update_count,
                    "error_count": source.error_count,
                    "fields_provided": list(self._source_fields.get(name, set()))
                }
            return result
    
    def is_active(self) -> bool:
        """
        Check if simulation data is actively being updated.
        
        Returns:
            bool: True if any data source is providing fresh data
        """
        with self._lock:
            return any(source.is_fresh for source in self._sources.values())
    
    def get_last_update_time(self) -> float:
        """
        Get the timestamp of the last data update.
        
        Returns:
            float: Timestamp of last update (seconds since epoch)
        """
        with self._lock:
            return self._last_update_time
    
    def interpolate(self, category: str, timestamp: Optional[float] = None) -> Dict[str, Any]:
        """
        Interpolate data between historical points.
        Useful for smoothing or estimating values between updates.
        
        Args:
            category: Category of data to interpolate ('position', 'attitude', 'motion')
            timestamp: Target timestamp (defaults to current time)
            
        Returns:
            dict: Interpolated data
        """
        with self._lock:
            if category not in self._history or not self._history[category]:
                return {}
                
            if timestamp is None:
                timestamp = time.time()
                
            # Check if we have enough points to interpolate
            if len(self._history[category]) < 2:
                return self._history[category][-1].copy()
                
            # Find the two closest points
            # Assuming history is ordered by timestamp
            history = self._history[category]
            
            # If timestamp is before the earliest point, use the earliest
            if timestamp <= history[0]["timestamp"]:
                return history[0].copy()
                
            # If timestamp is after the latest point, use the latest
            if timestamp >= history[-1]["timestamp"]:
                return history[-1].copy()
                
            # Find the two points to interpolate between
            for i in range(len(history) - 1):
                if history[i]["timestamp"] <= timestamp <= history[i+1]["timestamp"]:
                    # Found our interval
                    t1 = history[i]["timestamp"]
                    t2 = history[i+1]["timestamp"]
                    point1 = history[i]
                    point2 = history[i+1]
                    
                    # Calculate interpolation factor
                    if t2 == t1:  # Avoid division by zero
                        factor = 0.0
                    else:
                        factor = (timestamp - t1) / (t2 - t1)
                        
                    # Interpolate each numeric field
                    result = {"timestamp": timestamp}
                    for key in point1:
                        if key != "timestamp" and key in point2:
                            if isinstance(point1[key], (int, float)) and isinstance(point2[key], (int, float)):
                                result[key] = point1[key] + factor * (point2[key] - point1[key])
                            else:
                                # Non-numeric or missing in one point, use the closest point's value
                                result[key] = point2[key] if factor > 0.5 else point1[key]
                                
                    return result
            
            # Fallback - shouldn't reach here with proper data
            return history[-1].copy()
    
    def reset(self) -> None:
        """Reset all data to initial state."""
        with self._lock:
            self._data.clear()
            for category in self._history:
                self._history[category].clear()
            for source in self._sources.values():
                source.disconnect()
            for source_fields in self._source_fields.values():
                source_fields.clear()
            self._last_update_time = 0.0
            
            logger.info("SimData reset to initial state")
    
    async def wait_for_data(self, timeout: float = 30.0) -> bool:
        """
        Wait asynchronously until data is available from any source.
        Useful during startup to ensure we have data before proceeding.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            bool: True if data became available, False if timeout
        """
        start_time = time.time()
        while (time.time() - start_time) < timeout:
            if self.is_active():
                return True
            await asyncio.sleep(0.1)
        return False


# Example usage:
if __name__ == "__main__":
    import random
    
    # Create SimData instance
    sim_data = SimData()
    
    # Sample NMEA data
    nmea_data = {
        "latitude": 47.123,
        "longitude": -122.456,
        "altitude_msl": 1500.0,
        "ground_speed": 55.5,
        "track_true": 270.0,
        "fix_quality": 1,
        "satellites": 8,
        "gps_valid": True,
        "ias": 60.0,
        "vario": 1.2,
        "heading": 268.0,
        "turn_rate": 0.5
    }
    
    # Sample UDP data
    udp_data = {
        "yaw_deg": 269.0,
        "pitch_deg": 2.5,
        "bank_deg": 15.0,
        "roll_rate_deg": 0.2,
        "g_force": 1.2,
        "altitude_m": 1510.0,  # Slight difference from NMEA
        "vario_mps": 1.0,      # Slight difference from NMEA
        "height_agl": 950.0,
        "turbulence": 0.3
    }
    
    # Update with sample data
    sim_data.update_from_nmea(nmea_data)
    sim_data.update_from_condor_udp(udp_data)
    
    # Print combined data
    combined = sim_data.get_data()
    print("Combined Data:")
    for key, value in combined.items():
        print(f"  {key}: {value}")
    
    # Print source status
    status = sim_data.get_source_status()
    print("\nSource Status:")
    for source, info in status.items():
        print(f"  {source}: {'Fresh' if info['fresh'] else 'Stale'}, {len(info['fields_provided'])} fields")
