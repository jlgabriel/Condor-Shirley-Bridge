"""
Unit tests for NMEA Parser
"""
import pytest
from condor_shirley_bridge.parsers.nmea_parser import NMEAParser


class TestNMEAParser:
    """Tests for NMEAParser class"""

    def test_parser_initialization(self):
        """Test parser initializes correctly"""
        parser = NMEAParser()
        assert parser is not None
        assert parser.gps_position is None
        assert parser.soaring_data is None

    def test_parse_valid_gpgga(self, valid_gpgga_sentence):
        """Test parsing valid GPGGA sentence"""
        parser = NMEAParser()
        result = parser.parse_sentence(valid_gpgga_sentence)

        assert result is True
        assert parser.gps_position is not None
        assert parser.gps_position.valid is True
        assert 45 < parser.gps_position.latitude < 46
        assert 13 < parser.gps_position.longitude < 14
        assert parser.gps_position.altitude_msl == pytest.approx(117.4, rel=0.01)
        assert parser.gps_position.satellites == 12

    def test_parse_valid_gprmc(self, valid_gprmc_sentence):
        """Test parsing valid GPRMC sentence"""
        parser = NMEAParser()
        result = parser.parse_sentence(valid_gprmc_sentence)

        assert result is True
        assert parser.gps_position is not None
        assert parser.gps_position.valid is True
        assert parser.gps_position.ground_speed == pytest.approx(50.0, rel=0.01)
        assert parser.gps_position.track_true == pytest.approx(267.45, rel=0.01)

    def test_parse_valid_lxwp0(self, valid_lxwp0_sentence):
        """Test parsing valid LXWP0 sentence"""
        parser = NMEAParser()
        result = parser.parse_sentence(valid_lxwp0_sentence)

        assert result is True
        assert parser.soaring_data is not None
        assert parser.soaring_data.valid is True
        assert parser.soaring_data.ias == pytest.approx(17.5, rel=0.01)
        assert parser.soaring_data.vario == pytest.approx(0.5, rel=0.01)

    def test_parse_invalid_checksum(self, invalid_checksum_sentence):
        """Test that invalid checksum is rejected"""
        parser = NMEAParser()
        result = parser.parse_sentence(invalid_checksum_sentence)

        assert result is False

    def test_parse_malformed_sentence(self, malformed_gpgga_sentence):
        """Test that malformed sentence is rejected"""
        parser = NMEAParser()
        result = parser.parse_sentence(malformed_gpgga_sentence)

        assert result is False

    def test_parse_empty_sentence(self):
        """Test that empty sentence is rejected"""
        parser = NMEAParser()
        result = parser.parse_sentence("")

        assert result is False

    def test_parse_too_long_sentence(self):
        """Test that sentence exceeding max length is rejected"""
        parser = NMEAParser()
        long_sentence = "A" * 300  # Exceeds MAX_NMEA_LENGTH
        result = parser.parse_sentence(long_sentence)

        assert result is False

    def test_validate_coordinates_valid(self):
        """Test coordinate validation with valid values"""
        parser = NMEAParser()
        assert parser._validate_coordinates(45.0, 13.0) is True

    def test_validate_coordinates_invalid_latitude(self):
        """Test coordinate validation with invalid latitude"""
        parser = NMEAParser()
        assert parser._validate_coordinates(95.0, 13.0) is False
        assert parser._validate_coordinates(-95.0, 13.0) is False

    def test_validate_coordinates_invalid_longitude(self):
        """Test coordinate validation with invalid longitude"""
        parser = NMEAParser()
        assert parser._validate_coordinates(45.0, 185.0) is False
        assert parser._validate_coordinates(45.0, -185.0) is False

    def test_validate_altitude_valid(self):
        """Test altitude validation with valid value"""
        parser = NMEAParser()
        assert parser._validate_altitude(1000.0) is True

    def test_validate_altitude_out_of_range(self):
        """Test altitude validation with out of range values"""
        parser = NMEAParser()
        assert parser._validate_altitude(20000.0) is False
        assert parser._validate_altitude(-1000.0) is False

    def test_validate_speed_valid(self):
        """Test speed validation with valid value"""
        parser = NMEAParser()
        assert parser._validate_speed(50.0) is True

    def test_validate_speed_out_of_range(self):
        """Test speed validation with out of range values"""
        parser = NMEAParser()
        assert parser._validate_speed(500.0) is False
        assert parser._validate_speed(-10.0) is False

    def test_validate_vario_valid(self):
        """Test vario validation with valid value"""
        parser = NMEAParser()
        assert parser._validate_vario(2.5) is True
        assert parser._validate_vario(-2.5) is True

    def test_validate_vario_out_of_range(self):
        """Test vario validation with out of range values"""
        parser = NMEAParser()
        assert parser._validate_vario(25.0) is False
        assert parser._validate_vario(-25.0) is False

    def test_get_combined_data(self):
        """Test getting combined data from parser"""
        parser = NMEAParser()

        # Parse both GPS and soaring data
        parser.parse_sentence("$GPGGA,170000.021,4553.3709,N,01353.4357,E,1,12,10,117.4,M,,,,,0000*02")
        parser.parse_sentence("$LXWP0,Y,17.5,117.4,0.50,,,,,,268,268,0.0*7F")

        combined = parser.get_combined_data()

        assert 'latitude' in combined
        assert 'longitude' in combined
        assert 'altitude_msl' in combined
        assert 'ias' in combined
        assert 'vario' in combined
        assert 'heading' in combined

    def test_data_freshness(self):
        """Test data freshness checking"""
        parser = NMEAParser()

        # Initially no data should be fresh
        gps_fresh, soaring_fresh = parser.is_data_fresh()
        assert gps_fresh is False
        assert soaring_fresh is False

        # After parsing, data should be fresh
        parser.parse_sentence("$GPGGA,170000.021,4553.3709,N,01353.4357,E,1,12,10,117.4,M,,,,,0000*02")
        gps_fresh, soaring_fresh = parser.is_data_fresh()
        assert gps_fresh is True

    def test_checksum_calculation(self):
        """Test NMEA checksum calculation"""
        parser = NMEAParser()

        # Known checksum: GPGGA sentence should calculate to 0x02
        data = "GPGGA,170000.021,4553.3709,N,01353.4357,E,1,12,10,117.4,M,,,,,0000"
        checksum = parser._calculate_checksum(f"${data}")

        assert checksum == 0x02
