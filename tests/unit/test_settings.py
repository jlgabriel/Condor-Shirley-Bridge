"""
Unit tests for Settings
"""
import pytest
import os
import json
from condor_shirley_bridge.core.settings import Settings


class TestSettings:
    """Tests for Settings class"""

    def test_settings_initialization(self, temp_config_file):
        """Test settings initializes with defaults"""
        settings = Settings(temp_config_file)
        assert settings is not None
        assert settings.settings.serial.port == "COM4"
        assert settings.settings.serial.baudrate == 4800

    def test_load_nonexistent_creates_default(self, temp_config_file):
        """Test loading nonexistent config creates default"""
        # Remove the temp file
        os.remove(temp_config_file)

        settings = Settings(temp_config_file)
        assert os.path.exists(temp_config_file)

    def test_save_and_load(self, temp_config_file):
        """Test saving and loading settings"""
        settings = Settings(temp_config_file)

        # Modify a setting
        settings.set('serial', 'port', 'COM5')
        settings.save()

        # Load in new instance
        settings2 = Settings(temp_config_file)
        assert settings2.get('serial', 'port') == 'COM5'

    def test_get_setting(self):
        """Test getting settings"""
        settings = Settings()
        serial_port = settings.get('serial', 'port')
        assert serial_port is not None

        # Get entire section
        serial_settings = settings.get('serial')
        assert serial_settings.port is not None

    def test_set_setting(self):
        """Test setting values"""
        settings = Settings()

        # Set a value
        result = settings.set('serial', 'baudrate', 9600)
        assert result is True
        assert settings.get('serial', 'baudrate') == 9600

    def test_set_invalid_section(self):
        """Test setting invalid section returns False"""
        settings = Settings()
        result = settings.set('invalid_section', 'key', 'value')
        assert result is False

    def test_set_invalid_key(self):
        """Test setting invalid key returns False"""
        settings = Settings()
        result = settings.set('serial', 'invalid_key', 'value')
        assert result is False

    def test_validate_valid_settings(self):
        """Test validating valid settings"""
        settings = Settings()
        errors = settings.validate()
        assert len(errors) == 0

    def test_validate_invalid_serial_port(self):
        """Test validation catches invalid serial port"""
        settings = Settings()
        settings.set('serial', 'port', '')  # Empty port
        errors = settings.validate()
        assert 'serial' in errors

    def test_validate_invalid_baudrate(self):
        """Test validation catches invalid baudrate"""
        settings = Settings()
        settings.set('serial', 'baudrate', -1)  # Negative baudrate
        errors = settings.validate()
        assert 'serial' in errors

    def test_validate_invalid_udp_port(self):
        """Test validation catches invalid UDP port"""
        settings = Settings()
        settings.set('udp', 'port', 70000)  # Port out of range
        errors = settings.validate()
        assert 'udp' in errors

    def test_reset_to_defaults(self):
        """Test resetting to defaults"""
        settings = Settings()
        settings.set('serial', 'port', 'COM10')

        settings.reset_to_defaults()
        assert settings.get('serial', 'port') == 'COM4'

    def test_add_recent_config(self, temp_config_file):
        """Test adding to recent configs"""
        settings = Settings()
        settings.add_recent_config(temp_config_file)

        recent = settings.settings.ui.recent_configs
        assert temp_config_file in recent

    def test_recent_config_limit(self):
        """Test recent configs list is limited"""
        settings = Settings()

        # Add more than 10 configs
        for i in range(15):
            settings.add_recent_config(f"/path/to/config{i}.json")

        recent = settings.settings.ui.recent_configs
        assert len(recent) <= 10

    def test_reconnection_parameters_in_settings(self):
        """Test that new reconnection parameters are in settings"""
        settings = Settings()
        serial_settings = settings.get('serial')

        assert hasattr(serial_settings, 'max_retries')
        assert hasattr(serial_settings, 'retry_delay')
        assert serial_settings.max_retries == 5
        assert serial_settings.retry_delay == 2.0

        udp_settings = settings.get('udp')
        assert hasattr(udp_settings, 'max_retries')
        assert hasattr(udp_settings, 'retry_delay')
