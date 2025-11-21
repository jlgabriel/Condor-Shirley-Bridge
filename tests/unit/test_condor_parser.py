"""
Unit tests for Condor UDP Parser
"""
import pytest
from condor_shirley_bridge.parsers.condor_parser import CondorUDPParser


class TestCondorUDPParser:
    """Tests for CondorUDPParser class"""

    def test_parser_initialization(self):
        """Test parser initializes correctly"""
        parser = CondorUDPParser()
        assert parser is not None
        assert parser.attitude_data is None
        assert parser.motion_data is None
        assert parser.settings_data is None

    def test_parse_valid_message(self, valid_condor_udp_message):
        """Test parsing valid Condor UDP message"""
        parser = CondorUDPParser()
        result = parser.parse_message(valid_condor_udp_message)

        assert result is True
        assert parser.motion_data is not None
        assert parser.attitude_data is not None

    def test_parse_empty_message(self):
        """Test that empty message is rejected"""
        parser = CondorUDPParser()
        result = parser.parse_message("")

        assert result is False

    def test_parse_too_long_message(self):
        """Test that message exceeding max length is rejected"""
        parser = CondorUDPParser()
        long_message = "key=value\n" * 500  # Exceeds MAX_MESSAGE_LENGTH
        result = parser.parse_message(long_message)

        assert result is False

    def test_parse_motion_data(self):
        """Test parsing motion data"""
        parser = CondorUDPParser()
        message = "airspeed=30.5\naltitude=1000.0\nvario=2.5"
        parser.parse_message(message)

        assert parser.motion_data is not None
        assert parser.motion_data.airspeed == pytest.approx(30.5, rel=0.01)
        assert parser.motion_data.altitude == pytest.approx(1000.0, rel=0.01)
        assert parser.motion_data.vario == pytest.approx(2.5, rel=0.01)

    def test_parse_attitude_data(self):
        """Test parsing attitude data"""
        parser = CondorUDPParser()
        message = "yaw=1.57\npitch=0.1\nbank=0.2"
        parser.parse_message(message)

        assert parser.attitude_data is not None
        assert parser.attitude_data.yaw == pytest.approx(1.57, rel=0.01)
        assert parser.attitude_data.pitch == pytest.approx(0.1, rel=0.01)
        assert parser.attitude_data.bank == pytest.approx(0.2, rel=0.01)

    def test_parse_settings_data(self):
        """Test parsing settings data"""
        parser = CondorUDPParser()
        message = "flaps=3\nMC=2.5\nwater=50\nradiofrequency=123.5"
        parser.parse_message(message)

        assert parser.settings_data is not None
        assert parser.settings_data.flaps == 3
        assert parser.settings_data.mc == pytest.approx(2.5, rel=0.01)
        assert parser.settings_data.water == 50

    def test_validate_numeric_value_valid(self):
        """Test numeric value validation with valid value"""
        parser = CondorUDPParser()
        assert parser._validate_numeric_value("test", 50.0, 0.0, 100.0) is True

    def test_validate_numeric_value_out_of_range(self):
        """Test numeric value validation with out of range values"""
        parser = CondorUDPParser()
        assert parser._validate_numeric_value("test", 150.0, 0.0, 100.0) is False
        assert parser._validate_numeric_value("test", -10.0, 0.0, 100.0) is False

    def test_get_combined_data(self, valid_condor_udp_message):
        """Test getting combined data from parser"""
        parser = CondorUDPParser()
        parser.parse_message(valid_condor_udp_message)

        combined = parser.get_combined_data()

        assert 'yaw_deg' in combined
        assert 'pitch_deg' in combined
        assert 'ias_kts' in combined
        assert 'altitude_m' in combined
        assert 'vario_mps' in combined

    def test_data_freshness(self, valid_condor_udp_message):
        """Test data freshness checking"""
        parser = CondorUDPParser()

        # Initially no data should be fresh
        assert parser.is_data_fresh() is False

        # After parsing, data should be fresh
        parser.parse_message(valid_condor_udp_message)
        assert parser.is_data_fresh() is True

    def test_convert_value_int(self):
        """Test value conversion to int"""
        parser = CondorUDPParser()
        result = parser._convert_value("42")
        assert result == 42
        assert isinstance(result, int)

    def test_convert_value_float(self):
        """Test value conversion to float"""
        parser = CondorUDPParser()
        result = parser._convert_value("3.14")
        assert result == pytest.approx(3.14, rel=0.01)
        assert isinstance(result, float)

    def test_convert_value_scientific(self):
        """Test value conversion with scientific notation"""
        parser = CondorUDPParser()
        result = parser._convert_value("1.5e-3")
        assert result == pytest.approx(0.0015, rel=0.01)
        assert isinstance(result, float)

    def test_rad_to_deg(self):
        """Test radians to degrees conversion"""
        parser = CondorUDPParser()
        result = parser._rad_to_deg(3.14159265359)
        assert result == pytest.approx(180.0, rel=0.01)

    def test_mps_to_knots(self):
        """Test meters per second to knots conversion"""
        parser = CondorUDPParser()
        result = parser._mps_to_knots(10.0)
        assert result == pytest.approx(19.4384, rel=0.01)
