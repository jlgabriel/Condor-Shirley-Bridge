#!/usr/bin/env python3

"""
Settings for Condor-Shirley-Bridge
Configuration management for the application.
Handles loading, saving, and accessing settings.

Part of the Condor-Shirley-Bridge project.
"""

import json
import os
import logging
from typing import Dict, Any, Optional, Union, List
from pathlib import Path
import dataclasses
from dataclasses import dataclass, field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('settings')


@dataclass
class SerialSettings:
    """Serial port settings for NMEA data"""
    enabled: bool = True
    port: str = "COM4"
    baudrate: int = 4800
    timeout: float = 1.0
    data_freshness_threshold: float = 5.0  # seconds


@dataclass
class UDPSettings:
    """UDP settings for Condor data"""
    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = 55278
    buffer_size: int = 65535
    data_freshness_threshold: float = 5.0  # seconds


@dataclass
class WebSocketSettings:
    """WebSocket server settings for FlyShirley"""
    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = 2992
    path: str = "/api/v1"
    broadcast_interval: float = 0.25  # seconds (4 Hz)


@dataclass
class LogSettings:
    """Logging settings"""
    level: str = "INFO"
    log_to_file: bool = False
    log_file_path: Optional[str] = None
    max_log_files: int = 5
    max_log_size_mb: int = 10


@dataclass
class UISettings:
    """User interface settings"""
    start_minimized: bool = False
    always_on_top: bool = False
    show_advanced: bool = False
    theme: str = "system"  # "system", "light", "dark"
    recent_configs: List[str] = field(default_factory=list)
    startup_check_updates: bool = True


@dataclass
class ApplicationSettings:
    """Main application settings container"""
    serial: SerialSettings = field(default_factory=SerialSettings)
    udp: UDPSettings = field(default_factory=UDPSettings)
    websocket: WebSocketSettings = field(default_factory=WebSocketSettings)
    logging: LogSettings = field(default_factory=LogSettings)
    ui: UISettings = field(default_factory=UISettings)
    version: str = "1.0.0"
    first_run: bool = True


class SettingsEncoder(json.JSONEncoder):
    """Custom JSON encoder for dataclasses"""
    def default(self, obj):
        if dataclasses.is_dataclass(obj):
            return dataclasses.asdict(obj)
        return super().default(obj)


class Settings:
    """
    Settings manager for Condor-Shirley-Bridge.
    Handles loading, saving, and accessing application settings.
    """
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize settings manager.
        
        Args:
            config_file: Path to configuration file (optional)
        """
        # Default settings
        self.settings = ApplicationSettings()
        
        # Configuration file path
        if config_file:
            self.config_file = config_file
        else:
            # Default to user's home directory
            self.config_file = os.path.join(
                str(Path.home()), 
                '.condor_shirley_bridge', 
                'config.json'
            )
            
        # Load settings
        self.load()
    
    def load(self, config_file: Optional[str] = None) -> bool:
        """
        Load settings from file.
        
        Args:
            config_file: Override configuration file path
            
        Returns:
            bool: True if settings were loaded successfully
        """
        if config_file:
            self.config_file = config_file
            
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            # Check if file exists
            if not os.path.exists(self.config_file):
                logger.info(f"Configuration file not found at {self.config_file}")
                self._create_default_config()
                return True
            
            # Load from file
            with open(self.config_file, 'r') as f:
                data = json.load(f)
                
            # Update settings with loaded data
            self._update_from_dict(data)
            
            logger.info(f"Settings loaded from {self.config_file}")
            return True
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing config file: {e}")
            return False
            
        except IOError as e:
            logger.error(f"Error reading config file: {e}")
            return False
            
        except Exception as e:
            logger.error(f"Unexpected error loading config: {e}")
            return False
    
    def save(self, config_file: Optional[str] = None) -> bool:
        """
        Save settings to file.
        
        Args:
            config_file: Override configuration file path
            
        Returns:
            bool: True if settings were saved successfully
        """
        if config_file:
            self.config_file = config_file
            
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            # Save to file
            with open(self.config_file, 'w') as f:
                json.dump(self.settings, f, indent=2, cls=SettingsEncoder)
                
            logger.info(f"Settings saved to {self.config_file}")
            return True
            
        except IOError as e:
            logger.error(f"Error writing config file: {e}")
            return False
            
        except Exception as e:
            logger.error(f"Unexpected error saving config: {e}")
            return False
    
    def _create_default_config(self) -> None:
        """Create default configuration file."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            # Save default settings
            with open(self.config_file, 'w') as f:
                json.dump(self.settings, f, indent=2, cls=SettingsEncoder)
                
            logger.info(f"Default configuration created at {self.config_file}")
            
        except Exception as e:
            logger.error(f"Error creating default config: {e}")
    
    def _update_from_dict(self, data: Dict[str, Any]) -> None:
        """
        Update settings from dictionary.
        
        Args:
            data: Dictionary with settings data
        """
        # Helper function to recursively update dataclasses
        def update_dataclass(obj, data_dict):
            for key, value in data_dict.items():
                if hasattr(obj, key):
                    current_value = getattr(obj, key)
                    # If it's a dataclass and value is a dict, update recursively
                    if dataclasses.is_dataclass(current_value) and isinstance(value, dict):
                        update_dataclass(current_value, value)
                    # For lists with default factory, handle specially
                    elif isinstance(current_value, list) and isinstance(value, list):
                        setattr(obj, key, value)
                    # Direct value assignment for everything else
                    else:
                        # Only set if types are compatible
                        target_type = type(current_value)
                        try:
                            if target_type is bool and isinstance(value, int):
                                # Convert int to bool (0=False, non-zero=True)
                                setattr(obj, key, bool(value))
                            elif value is None or isinstance(value, target_type):
                                # Direct assignment for same type or None
                                setattr(obj, key, value)
                            else:
                                # Try to convert to target type
                                setattr(obj, key, target_type(value))
                        except (ValueError, TypeError):
                            logger.warning(f"Could not convert {key}={value} to {target_type}")
        
        # Update main settings object
        update_dataclass(self.settings, data)
        
        # No longer first run after loading settings
        self.settings.first_run = False
    
    def get(self, section: str, key: Optional[str] = None) -> Any:
        """
        Get a setting value.
        
        Args:
            section: Section name (serial, udp, websocket, logging, ui)
            key: Setting key (if None, returns entire section)
            
        Returns:
            Setting value or None if not found
        """
        try:
            if hasattr(self.settings, section):
                section_obj = getattr(self.settings, section)
                if key is None:
                    return section_obj
                elif hasattr(section_obj, key):
                    return getattr(section_obj, key)
        except Exception as e:
            logger.error(f"Error getting setting {section}.{key}: {e}")
        
        return None
    
    def set(self, section: str, key: str, value: Any) -> bool:
        """
        Set a setting value.
        
        Args:
            section: Section name (serial, udp, websocket, logging, ui)
            key: Setting key
            value: New value
            
        Returns:
            bool: True if setting was changed
        """
        try:
            if hasattr(self.settings, section):
                section_obj = getattr(self.settings, section)
                if hasattr(section_obj, key):
                    # Get current value and type
                    current_value = getattr(section_obj, key)
                    target_type = type(current_value)
                    
                    # Convert value to correct type
                    if target_type is bool and isinstance(value, int):
                        # Convert int to bool (0=False, non-zero=True)
                        typed_value = bool(value)
                    elif value is None or isinstance(value, target_type):
                        # Direct assignment for same type or None
                        typed_value = value
                    else:
                        # Try to convert to target type
                        typed_value = target_type(value)
                    
                    # Set the value
                    setattr(section_obj, key, typed_value)
                    return True
        except (ValueError, TypeError) as e:
            logger.error(f"Error setting {section}.{key}={value}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error setting {section}.{key}: {e}")
        
        return False
    
    def reset_to_defaults(self) -> None:
        """Reset all settings to default values."""
        self.settings = ApplicationSettings()
        logger.info("Settings reset to defaults")
    
    def add_recent_config(self, path: str) -> None:
        """
        Add a configuration file to the recent list.
        
        Args:
            path: Path to configuration file
        """
        # Normalize path
        norm_path = os.path.normpath(path)
        
        # Remove if already in list
        if norm_path in self.settings.ui.recent_configs:
            self.settings.ui.recent_configs.remove(norm_path)
        
        # Add to front of list
        self.settings.ui.recent_configs.insert(0, norm_path)
        
        # Limit list size to 10 items
        if len(self.settings.ui.recent_configs) > 10:
            self.settings.ui.recent_configs = self.settings.ui.recent_configs[:10]
    
    def get_available_serial_ports(self) -> List[str]:
        """
        Get a list of available serial ports.
        
        Returns:
            list: List of available serial port names
        """
        try:
            import serial.tools.list_ports
            ports = [port.device for port in serial.tools.list_ports.comports()]
            return ports
        except Exception as e:
            logger.error(f"Error listing serial ports: {e}")
            return []

    def apply_logging_settings(self) -> None:
        """Apply logging settings to the Python logging system."""
        try:
            # Get logging settings
            log_level = self.settings.logging.level
            log_to_file = self.settings.logging.log_to_file
            log_file_path = self.settings.logging.log_file_path

            # Convert level string to logging level
            level_map = {
                "DEBUG": logging.DEBUG,
                "INFO": logging.INFO,
                "WARNING": logging.WARNING,
                "ERROR": logging.ERROR,
                "CRITICAL": logging.CRITICAL
            }
            level = level_map.get(log_level, logging.INFO)

            # Usar la configuración centralizada
            from condor_shirley_bridge.core.log_config import configure_logging

            # Configurar el sistema de logs
            configure_logging(
                level=level,
                log_to_file=log_to_file,
                log_file_path=log_file_path,
                max_log_files=self.settings.logging.max_log_files,
                max_log_size_mb=self.settings.logging.max_log_size_mb
            )

            logger.info(f"Logging level set to {log_level}")
        except Exception as e:
            logger.error(f"Error applying logging settings: {e}")
    
    def validate(self) -> Dict[str, List[str]]:
        """
        Validate settings for consistency and correctness.
        
        Returns:
            dict: Dictionary of validation errors by section
        """
        errors = {}
        
        # Validate serial settings
        serial_errors = []
        if self.settings.serial.enabled:
            if not self.settings.serial.port:
                serial_errors.append("Serial port cannot be empty")
            if self.settings.serial.baudrate <= 0:
                serial_errors.append("Baudrate must be positive")
            if self.settings.serial.timeout <= 0:
                serial_errors.append("Timeout must be positive")
        if serial_errors:
            errors["serial"] = serial_errors
        
        # Validate UDP settings
        udp_errors = []
        if self.settings.udp.enabled:
            if self.settings.udp.port <= 0 or self.settings.udp.port > 65535:
                udp_errors.append("UDP port must be between 1 and 65535")
            if self.settings.udp.buffer_size <= 0:
                udp_errors.append("Buffer size must be positive")
        if udp_errors:
            errors["udp"] = udp_errors
        
        # Validate WebSocket settings
        websocket_errors = []
        if self.settings.websocket.enabled:
            if self.settings.websocket.port <= 0 or self.settings.websocket.port > 65535:
                websocket_errors.append("WebSocket port must be between 1 and 65535")
            if self.settings.websocket.broadcast_interval <= 0:
                websocket_errors.append("Broadcast interval must be positive")
        if websocket_errors:
            errors["websocket"] = websocket_errors
        
        # Validate logging settings
        logging_errors = []
        if self.settings.logging.log_to_file and not self.settings.logging.log_file_path:
            logging_errors.append("Log file path must be specified when logging to file")
        if self.settings.logging.max_log_files <= 0:
            logging_errors.append("Maximum log files must be positive")
        if self.settings.logging.max_log_size_mb <= 0:
            logging_errors.append("Maximum log size must be positive")
        if logging_errors:
            errors["logging"] = logging_errors
        
        return errors


# Example usage:
if __name__ == "__main__":
    # Create settings manager
    settings = Settings()
    
    # Print current settings
    print("Current Settings:")
    settings_dict = dataclasses.asdict(settings.settings)
    for section, section_settings in settings_dict.items():
        if isinstance(section_settings, dict):
            print(f"\n[{section}]")
            for key, value in section_settings.items():
                print(f"  {key} = {value}")
        else:
            print(f"\n{section} = {section_settings}")
    
    # Validate settings
    validation_errors = settings.validate()
    if validation_errors:
        print("\nValidation Errors:")
        for section, errors in validation_errors.items():
            print(f"[{section}]")
            for error in errors:
                print(f"  - {error}")
    else:
        print("\nSettings are valid.")
    
    # Save settings
    settings.save()
