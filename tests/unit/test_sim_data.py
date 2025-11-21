"""
Unit tests for SimData
"""
import pytest
from condor_shirley_bridge.core.sim_data import SimData


class TestSimData:
    """Tests for SimData class"""

    def test_sim_data_initialization(self):
        """Test SimData initializes correctly"""
        sim_data = SimData()
        assert sim_data is not None
        assert not sim_data.is_active()

    def test_update_from_nmea(self, sample_nmea_data):
        """Test updating data from NMEA source"""
        sim_data = SimData()
        sim_data.update_from_nmea(sample_nmea_data)

        data = sim_data.get_data()
        assert 'latitude' in data
        assert 'longitude' in data
        assert 'altitude_msl' in data
        assert data['latitude'] == pytest.approx(45.889515, rel=0.001)

    def test_update_from_condor_udp(self, sample_udp_data):
        """Test updating data from Condor UDP source"""
        sim_data = SimData()
        sim_data.update_from_condor_udp(sample_udp_data)

        data = sim_data.get_data()
        assert 'yaw_deg' in data
        assert 'pitch_deg' in data
        assert 'bank_deg' in data

    def test_combined_updates(self, sample_nmea_data, sample_udp_data):
        """Test that both NMEA and UDP data are combined"""
        sim_data = SimData()
        sim_data.update_from_nmea(sample_nmea_data)
        sim_data.update_from_condor_udp(sample_udp_data)

        data = sim_data.get_data()
        # Should have data from both sources
        assert 'latitude' in data  # From NMEA
        assert 'yaw_deg' in data    # From UDP

    def test_is_active(self, sample_nmea_data):
        """Test is_active() returns correct status"""
        sim_data = SimData()
        assert sim_data.is_active() is False

        sim_data.update_from_nmea(sample_nmea_data)
        assert sim_data.is_active() is True

    def test_get_source_status(self, sample_nmea_data, sample_udp_data):
        """Test getting source status"""
        sim_data = SimData()
        sim_data.update_from_nmea(sample_nmea_data)
        sim_data.update_from_condor_udp(sample_udp_data)

        status = sim_data.get_source_status()
        assert 'nmea' in status
        assert 'condor_udp' in status
        assert status['nmea']['fresh'] is True
        assert status['condor_udp']['fresh'] is True

    def test_reset(self, sample_nmea_data):
        """Test resetting data"""
        sim_data = SimData()
        sim_data.update_from_nmea(sample_nmea_data)

        assert sim_data.is_active() is True

        sim_data.reset()
        assert sim_data.is_active() is False
        data = sim_data.get_data()
        assert len(data) == 0

    def test_get_last_update_time(self, sample_nmea_data):
        """Test getting last update time"""
        sim_data = SimData()
        assert sim_data.get_last_update_time() == 0.0

        sim_data.update_from_nmea(sample_nmea_data)
        assert sim_data.get_last_update_time() > 0.0

    @pytest.mark.asyncio
    async def test_wait_for_data(self, sample_nmea_data):
        """Test waiting for data async"""
        import asyncio

        sim_data = SimData()

        # Create task to wait for data
        wait_task = asyncio.create_task(sim_data.wait_for_data(timeout=2.0))

        # Add data after a short delay
        await asyncio.sleep(0.1)
        sim_data.update_from_nmea(sample_nmea_data)

        # Wait task should complete
        result = await wait_task
        assert result is True

    @pytest.mark.asyncio
    async def test_wait_for_data_timeout(self):
        """Test waiting for data timeout"""
        sim_data = SimData()

        # Should timeout since no data is added
        result = await sim_data.wait_for_data(timeout=0.5)
        assert result is False
