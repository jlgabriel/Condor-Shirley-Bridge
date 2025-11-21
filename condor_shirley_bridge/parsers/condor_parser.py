#!/usr/bin/env python3

"""
Condor UDP Parser for Condor-Shirley-Bridge
Parses UDP messages from Condor Soaring Simulator in key=value format.

Part of the Condor-Shirley-Bridge project.
"""

import re
import time
import logging
from dataclasses import dataclass
from typing import Dict, Optional, Any, Union
from condor_shirley_bridge import constants

# Configure logging
logger = logging.getLogger('condor_parser')


@dataclass
class CondorAttitudeData:
    """Attitude data parsed from Condor UDP messages"""
    timestamp: float  # System time when received
    yaw: float  # Yaw angle in radians
    pitch: float  # Pitch angle in radians
    bank: float  # Bank/roll angle in radians
    quaternion_x: float  # Quaternion x component
    quaternion_y: float  # Quaternion y component
    quaternion_z: float  # Quaternion z component
    quaternion_w: float  # Quaternion w component
    roll_rate: float  # Roll rate in radians/second
    pitch_rate: float  # Pitch rate in radians/second
    yaw_rate: float  # Yaw rate in radians/second
    yawstring_angle: float  # Yaw string angle in radians


@dataclass
class CondorMotionData:
    """Motion and environment data parsed from Condor UDP messages"""
    timestamp: float  # System time when received
    time: float  # Simulation time
    airspeed: float  # Indicated airspeed (m/s)
    altitude: float  # Altitude MSL (meters)
    vario: float  # Vertical speed (m/s)
    evario: float  # Energy-compensated vario (m/s)
    netto_vario: float  # Netto vario (m/s)
    ax: float  # Acceleration X component (m/s²)
    ay: float  # Acceleration Y component (m/s²)
    az: float  # Acceleration Z component (m/s²)
    vx: float  # Velocity X component (m/s)
    vy: float  # Velocity Y component (m/s)
    vz: float  # Velocity Z component (m/s)
    g_force: float  # G-force
    height: float  # Height above ground (meters)
    wheel_height: float  # Wheel height (meters)
    turbulence_strength: float  # Turbulence strength
    surface_roughness: float  # Surface roughness


@dataclass
class CondorSettingsData:
    """Settings and configuration data parsed from Condor UDP messages"""
    timestamp: float  # System time when received
    flaps: int  # Flaps setting
    mc: float  # MacCready setting
    water: int  # Water ballast
    radio_frequency: float  # Radio frequency


class CondorUDPParser:
    """
    Parser for UDP messages from Condor Soaring Simulator in key=value format
    """
    def __init__(self):
        # Store latest parsed data
        self.attitude_data: Optional[CondorAttitudeData] = None
        self.motion_data: Optional[CondorMotionData] = None
        self.settings_data: Optional[CondorSettingsData] = None
        
        # For tracking reception status
        self.last_data_time = 0
        
        # Compiled regex for key=value pairs
        self.kv_pattern = re.compile(r'([a-zA-Z_]+)=([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)')

    def _validate_message_length(self, message: str) -> bool:
        """
        Validate message length.

        Args:
            message: UDP message to validate

        Returns:
            bool: True if length is valid
        """
        if len(message) > constants.MAX_UDP_MESSAGE_LENGTH:
            logger.warning(f"Message too long: {len(message)} chars (max: {constants.MAX_UDP_MESSAGE_LENGTH})")
            return False
        return True

    def _validate_numeric_value(self, name: str, value: float, min_val: float, max_val: float) -> bool:
        """
        Validate a numeric value is within expected range.

        Args:
            name: Name of the value (for logging)
            value: Value to validate
            min_val: Minimum valid value
            max_val: Maximum valid value

        Returns:
            bool: True if value is valid
        """
        if not (min_val <= value <= max_val):
            logger.warning(f"{name} out of range: {value} (expected {min_val} to {max_val})")
            return False
        return True

    def parse_message(self, message: str) -> bool:
        """
        Parse a UDP message from Condor in key=value format
        Returns True if any data was successfully parsed
        """
        if not message:
            return False

        # Validate message length
        if not self._validate_message_length(message):
            return False

        # Current timestamp for all new data objects
        current_time = time.time()
        
        # Extract all key=value pairs
        pairs = self.kv_pattern.findall(message)
        if not pairs:
            return False
            
        # Convert to dictionary
        data_dict = {key: self._convert_value(value) for key, value in pairs}
        
        # Update data objects based on extracted values
        self._update_attitude_data(data_dict, current_time)
        self._update_motion_data(data_dict, current_time)
        self._update_settings_data(data_dict, current_time)
        
        self.last_data_time = current_time
        return True
    
    def _convert_value(self, value_str: str) -> Union[float, int]:
        """Convert string value to appropriate number type"""
        try:
            # Try converting to int first if no decimal point
            if '.' not in value_str and 'e' not in value_str.lower():
                return int(value_str)
            return float(value_str)
        except ValueError:
            # If conversion fails, return as float
            return 0.0
    
    def _update_attitude_data(self, data_dict: Dict[str, Any], timestamp: float) -> None:
        """Update attitude data from dictionary of values"""
        # Check if required attitude fields exist
        attitude_fields = {
            'yaw', 'pitch', 'bank', 
            'quaternionx', 'quaterniony', 'quaternionz', 'quaternionw',
            'rollrate', 'pitchrate', 'yawrate', 'yawstringangle'
        }
        
        # Only update if we have at least some of the key attitude fields
        if not any(field in data_dict for field in ['yaw', 'pitch', 'bank', 'quaternionx']):
            return
            
        # Create new attitude data object with default values for missing fields
        self.attitude_data = CondorAttitudeData(
            timestamp=timestamp,
            yaw=data_dict.get('yaw', 0.0),
            pitch=data_dict.get('pitch', 0.0),
            bank=data_dict.get('bank', 0.0),
            quaternion_x=data_dict.get('quaternionx', 0.0),
            quaternion_y=data_dict.get('quaterniony', 0.0),
            quaternion_z=data_dict.get('quaternionz', 0.0),
            quaternion_w=data_dict.get('quaternionw', 1.0),  # Default to identity quaternion
            roll_rate=data_dict.get('rollrate', 0.0),
            pitch_rate=data_dict.get('pitchrate', 0.0),
            yaw_rate=data_dict.get('yawrate', 0.0),
            yawstring_angle=data_dict.get('yawstringangle', 0.0)
        )
    
    def _update_motion_data(self, data_dict: Dict[str, Any], timestamp: float) -> None:
        """Update motion and environment data from dictionary of values"""
        # Check if required motion fields exist
        motion_fields = {
            'time', 'airspeed', 'altitude', 'vario', 'evario', 'nettovario',
            'ax', 'ay', 'az', 'vx', 'vy', 'vz', 'gforce',
            'height', 'wheelheight', 'turbulencestrength', 'surfaceroughness'
        }

        # Only update if we have at least some of the key motion fields
        if not any(field in data_dict for field in ['airspeed', 'altitude', 'vario']):
            return

        # Validate critical values
        if 'altitude' in data_dict:
            self._validate_numeric_value('altitude', data_dict['altitude'], constants.MIN_ALTITUDE_M, constants.MAX_ALTITUDE_M)

        if 'airspeed' in data_dict:
            self._validate_numeric_value('airspeed', data_dict['airspeed'], constants.MIN_AIRSPEED_MPS, constants.MAX_AIRSPEED_MPS)

        if 'vario' in data_dict:
            self._validate_numeric_value('vario', data_dict['vario'], constants.MIN_VARIO_MPS, constants.MAX_VARIO_MPS)

        if 'evario' in data_dict:
            self._validate_numeric_value('evario', data_dict['evario'], constants.MIN_VARIO_MPS, constants.MAX_VARIO_MPS)

        if 'nettovario' in data_dict:
            self._validate_numeric_value('nettovario', data_dict['nettovario'], constants.MIN_VARIO_MPS, constants.MAX_VARIO_MPS)

        if 'gforce' in data_dict:
            self._validate_numeric_value('gforce', data_dict['gforce'], constants.MIN_G_FORCE, constants.MAX_G_FORCE)

        if 'height' in data_dict:
            self._validate_numeric_value('height', data_dict['height'], constants.MIN_HEIGHT_AGL, constants.MAX_HEIGHT_AGL)

        # Create new motion data object with default values for missing fields
        self.motion_data = CondorMotionData(
            timestamp=timestamp,
            time=data_dict.get('time', time.time()),
            airspeed=data_dict.get('airspeed', 0.0),
            altitude=data_dict.get('altitude', 0.0),
            vario=data_dict.get('vario', 0.0),
            evario=data_dict.get('evario', 0.0),
            netto_vario=data_dict.get('nettovario', 0.0),
            ax=data_dict.get('ax', 0.0),
            ay=data_dict.get('ay', 0.0),
            az=data_dict.get('az', 0.0),
            vx=data_dict.get('vx', 0.0),
            vy=data_dict.get('vy', 0.0),
            vz=data_dict.get('vz', 0.0),
            g_force=data_dict.get('gforce', 1.0),
            height=data_dict.get('height', 0.0),
            wheel_height=data_dict.get('wheelheight', 0.0),
            turbulence_strength=data_dict.get('turbulencestrength', 0.0),
            surface_roughness=data_dict.get('surfaceroughness', 0.0)
        )
    
    def _update_settings_data(self, data_dict: Dict[str, Any], timestamp: float) -> None:
        """Update settings data from dictionary of values"""
        # Check if any settings fields exist
        settings_fields = {'flaps', 'MC', 'water', 'radiofrequency'}
        
        # Only create settings data if at least one setting field exists
        if not any(field in data_dict for field in settings_fields):
            return
            
        # Create new settings data object with default values for missing fields
        self.settings_data = CondorSettingsData(
            timestamp=timestamp,
            flaps=data_dict.get('flaps', 0),
            mc=data_dict.get('MC', 0.0),
            water=data_dict.get('water', 0),
            radio_frequency=data_dict.get('radiofrequency', 123.5)
        )
    
    def is_data_fresh(self) -> bool:
        """
        Check if data is fresh (received within the last 5 seconds)
        """
        return (time.time() - self.last_data_time) < 5.0
    
    def get_combined_data(self) -> Dict[str, Any]:
        """
        Return a combined dictionary with all available data
        """
        result = {}
        
        # Check data freshness
        if not self.is_data_fresh():
            return result
        
        # Add attitude data if available
        if self.attitude_data:
            result.update({
                # Convert radians to degrees for compatibility
                "yaw_deg": self._rad_to_deg(self.attitude_data.yaw),
                "pitch_deg": self._rad_to_deg(self.attitude_data.pitch),
                "bank_deg": self._rad_to_deg(self.attitude_data.bank),
                # Keep quaternions as is
                "quaternion_x": self.attitude_data.quaternion_x,
                "quaternion_y": self.attitude_data.quaternion_y,
                "quaternion_z": self.attitude_data.quaternion_z,
                "quaternion_w": self.attitude_data.quaternion_w,
                # Convert rates from radians to degrees
                "roll_rate_deg": self._rad_to_deg(self.attitude_data.roll_rate),
                "pitch_rate_deg": self._rad_to_deg(self.attitude_data.pitch_rate),
                "yaw_rate_deg": self._rad_to_deg(self.attitude_data.yaw_rate),
                "yawstring_angle_deg": self._rad_to_deg(self.attitude_data.yawstring_angle)
            })
        
        # Add motion data if available
        if self.motion_data:
            result.update({
                "sim_time": self.motion_data.time,
                # Convert m/s to knots for airspeed
                "ias_kts": self._mps_to_knots(self.motion_data.airspeed),
                "altitude_m": self.motion_data.altitude,
                "vario_mps": self.motion_data.vario,
                "evario_mps": self.motion_data.evario,
                "netto_vario_mps": self.motion_data.netto_vario,
                # Accelerations
                "accel_x": self.motion_data.ax,
                "accel_y": self.motion_data.ay, 
                "accel_z": self.motion_data.az,
                # Velocities
                "vel_x": self.motion_data.vx,
                "vel_y": self.motion_data.vy,
                "vel_z": self.motion_data.vz,
                # Other motion data
                "g_force": self.motion_data.g_force,
                "height_agl": self.motion_data.height,
                "wheel_height": self.motion_data.wheel_height,
                "turbulence": self.motion_data.turbulence_strength,
                "surface_roughness": self.motion_data.surface_roughness
            })
        
        # Add settings data if available
        if self.settings_data:
            result.update({
                "flaps": self.settings_data.flaps,
                "mc_setting": self.settings_data.mc,
                "water_ballast": self.settings_data.water,
                "radio_frequency": self.settings_data.radio_frequency
            })
            
        return result
    
    @staticmethod
    def _rad_to_deg(rad: float) -> float:
        """Convert radians to degrees"""
        return rad * 180.0 / 3.14159265358979
    
    @staticmethod
    def _mps_to_knots(mps: float) -> float:
        """Convert meters per second to knots"""
        return mps * 1.94384


# Example usage:
if __name__ == "__main__":
    parser = CondorUDPParser()
    
    # Test with sample UDP message
    test_message = """time=17.0000042330833
airspeed=0.126630261540413
altitude=117.328384399414
vario=-0.000376310548745096
evario=-0.000250873708864674
nettovario=-1.07004904747009
integrator=-8.38934184343998E-8
compass=0
yawstringangle=0.892712593078613
radiofrequency=123.5
yaw=4.67416524887085
pitch=2.23245751840295E-6
bank=0
quaternionx=4.29906467616092E-5
quaterniony=2.94698907055135E-7
quaternionz=0.0191108118742704
quaternionw=0.999817371368408
ax=-0.0140609405934811
ay=0.323577255010605
az=-8.06892871856689
vx=-0.00010999284859281
vy=0.0021741115488112
vz=-0.056265689432621
rollrate=0.0127795934677124
pitchrate=0.000720927026122808
yawrate=0.00025870418176055
gforce=0.177481718870235
height=0.670997619628906
wheelheight=-0.00165487907361239
turbulencestrength=0.488081604242325
surfaceroughness=6
flaps=3
MC=0
water=0"""
    
    result = parser.parse_message(test_message)
    print(f"Message parsed successfully: {result}")
    
    # Display combined data
    combined = parser.get_combined_data()
    print("\nCombined Data:")
    for key, value in combined.items():
        print(f"{key}: {value}")
