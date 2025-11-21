"""
Integration tests for data flow
"""
import pytest
from condor_shirley_bridge.parsers.nmea_parser import NMEAParser
from condor_shirley_bridge.parsers.condor_parser import CondorUDPParser
from condor_shirley_bridge.core.sim_data import SimData


class TestDataFlow:
    """Integration tests for complete data flow"""

    def test_nmea_to_simdata_flow(self):
        """Test data flow from NMEA parser to SimData"""
        # Create parser and sim data
        nmea_parser = NMEAParser()
        sim_data = SimData()

        # Parse NMEA sentences (with correct checksums)
        nmea_parser.parse_sentence("$GPGGA,170000.021,4553.3709,N,01353.4357,E,1,12,10,117.4,M,,,,,0000*02")
        nmea_parser.parse_sentence("$GPRMC,170000.021,A,4553.3709,N,01353.4357,E,50.00,267.45,010120,,,*14")
        nmea_parser.parse_sentence("$LXWP0,Y,60.0,117.4,2.50,,,,,,268,268,0.5*7D")

        # Get combined data and update sim_data
        nmea_data = nmea_parser.get_combined_data()
        sim_data.update_from_nmea(nmea_data)

        # Verify data flow
        data = sim_data.get_data()
        assert 'latitude' in data
        assert 'longitude' in data
        assert 'altitude_msl' in data
        assert 'ias' in data
        assert 'vario' in data

    def test_udp_to_simdata_flow(self):
        """Test data flow from Condor UDP parser to SimData"""
        # Create parser and sim data
        condor_parser = CondorUDPParser()
        sim_data = SimData()

        # Parse UDP message
        message = """time=17.0
airspeed=30.5
altitude=1000.0
vario=2.5
yaw=1.57
pitch=0.1
bank=0.2
gforce=1.2
height=950.0"""
        condor_parser.parse_message(message)

        # Get combined data and update sim_data
        udp_data = condor_parser.get_combined_data()
        sim_data.update_from_condor_udp(udp_data)

        # Verify data flow
        data = sim_data.get_data()
        assert 'yaw_deg' in data
        assert 'pitch_deg' in data
        assert 'bank_deg' in data
        assert 'ias' in data  # sim_data normalizes ias_kts to ias for consistency

    def test_combined_data_flow(self):
        """Test combined data flow from both sources"""
        # Create parsers and sim data
        nmea_parser = NMEAParser()
        condor_parser = CondorUDPParser()
        sim_data = SimData()

        # Parse NMEA data
        nmea_parser.parse_sentence("$GPGGA,170000.021,4553.3709,N,01353.4357,E,1,12,10,117.4,M,,,,,0000*02")
        nmea_data = nmea_parser.get_combined_data()
        sim_data.update_from_nmea(nmea_data)

        # Parse UDP data
        udp_message = "airspeed=30.5\nyaw=1.57\npitch=0.1\nbank=0.2"
        condor_parser.parse_message(udp_message)
        udp_data = condor_parser.get_combined_data()
        sim_data.update_from_condor_udp(udp_data)

        # Verify combined data
        data = sim_data.get_data()
        # Should have data from NMEA
        assert 'latitude' in data
        assert 'longitude' in data
        # Should have data from UDP
        assert 'yaw_deg' in data
        assert 'pitch_deg' in data

    def test_data_validation_in_flow(self):
        """Test that validation works throughout the flow"""
        nmea_parser = NMEAParser()
        sim_data = SimData()

        # Try to parse sentence with invalid coordinates (lat > 90)
        invalid_sentence = "$GPGGA,170000.021,9553.3709,N,01353.4357,E,1,12,10,117.4,M,,,,,0000*3A"
        result = nmea_parser.parse_sentence(invalid_sentence)

        # Should be rejected due to validation
        assert result is False
        assert nmea_parser.gps_position is None

    def test_source_status_tracking(self):
        """Test that source status is tracked properly"""
        nmea_parser = NMEAParser()
        condor_parser = CondorUDPParser()
        sim_data = SimData()

        # Initially no sources active
        assert sim_data.is_active() is False

        # Add NMEA data
        nmea_parser.parse_sentence("$GPGGA,170000.021,4553.3709,N,01353.4357,E,1,12,10,117.4,M,,,,,0000*02")
        nmea_data = nmea_parser.get_combined_data()
        sim_data.update_from_nmea(nmea_data)

        # Should be active now
        assert sim_data.is_active() is True

        # Check source status
        status = sim_data.get_source_status()
        assert status['nmea']['fresh'] is True
        assert status['condor_udp']['fresh'] is False

        # Add UDP data
        condor_parser.parse_message("airspeed=30.5\naltitude=1000.0")
        udp_data = condor_parser.get_combined_data()
        sim_data.update_from_condor_udp(udp_data)

        # Both sources should be fresh now
        status = sim_data.get_source_status()
        assert status['nmea']['fresh'] is True
        assert status['condor_udp']['fresh'] is True
