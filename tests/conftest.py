"""
Shared pytest fixtures for Condor-Shirley-Bridge tests
"""
import pytest
import tempfile
import os


@pytest.fixture
def temp_config_file():
    """Create a temporary config file for testing"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write('{}')
        temp_path = f.name

    yield temp_path

    # Cleanup
    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.fixture
def valid_gpgga_sentence():
    """Valid GPGGA NMEA sentence for testing"""
    return "$GPGGA,170000.021,4553.3709,N,01353.4357,E,1,12,10,117.4,M,,,,,0000*02"


@pytest.fixture
def valid_gprmc_sentence():
    """Valid GPRMC NMEA sentence for testing"""
    return "$GPRMC,170000.021,A,4553.3709,N,01353.4357,E,50.00,267.45,010120,,,*14"


@pytest.fixture
def valid_lxwp0_sentence():
    """Valid LXWP0 NMEA sentence for testing"""
    return "$LXWP0,Y,17.5,117.4,0.50,,,,,,268,268,0.0*7F"


@pytest.fixture
def invalid_checksum_sentence():
    """NMEA sentence with invalid checksum"""
    return "$GPGGA,170000.021,4553.3709,N,01353.4357,E,1,12,10,117.4,M,,,,,0000*FF"


@pytest.fixture
def malformed_gpgga_sentence():
    """Malformed GPGGA sentence with missing fields"""
    return "$GPGGA,170000.021,4553.3709*02"


@pytest.fixture
def valid_condor_udp_message():
    """Valid Condor UDP message for testing"""
    return """time=17.0
airspeed=30.5
altitude=1000.0
vario=2.5
evario=2.3
nettovario=2.0
yaw=1.57
pitch=0.1
bank=0.2
gforce=1.2
height=950.0"""


@pytest.fixture
def sample_nmea_data():
    """Sample NMEA parsed data"""
    return {
        "latitude": 45.889515,
        "longitude": 13.890595,
        "altitude_msl": 117.4,
        "ground_speed": 50.0,
        "track_true": 267.45,
        "fix_quality": 1,
        "satellites": 12,
        "gps_valid": True,
        "ias": 60.0,
        "vario": 2.5,
        "heading": 268.0
    }


@pytest.fixture
def sample_udp_data():
    """Sample Condor UDP parsed data"""
    return {
        "yaw_deg": 90.0,
        "pitch_deg": 5.0,
        "bank_deg": 15.0,
        "ias_kts": 65.0,
        "altitude_m": 1000.0,
        "vario_mps": 2.0,
        "g_force": 1.2,
        "height_agl": 950.0
    }
