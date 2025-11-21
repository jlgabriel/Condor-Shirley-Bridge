#!/usr/bin/env python3

"""
NMEA Parser for Condor-Shirley-Bridge
Parses NMEA sentences from Condor Soaring Simulator, specifically:
- $GPGGA (Global Positioning System Fix Data)
- $GPRMC (Recommended Minimum Specific GPS/Transit Data)
- $LXWP0 (LX Navigation proprietary sentence for soaring data)

Part of the Condor-Shirley-Bridge project.
"""

import re
import time
import logging
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any, Union

# Validation constants
MAX_NMEA_LENGTH = 256  # NMEA standard maximum is ~82, but allow some buffer
MIN_LATITUDE = -90.0
MAX_LATITUDE = 90.0
MIN_LONGITUDE = -180.0
MAX_LONGITUDE = 180.0
MAX_ALTITUDE_M = 15000.0  # 15km - maximum realistic for gliders
MIN_ALTITUDE_M = -500.0  # Dead Sea level
MAX_SPEED_KTS = 400.0  # Maximum realistic for gliders
MIN_SPEED_KTS = 0.0
MAX_VARIO_MPS = 20.0  # +/- 20 m/s is extreme but possible
MIN_VARIO_MPS = -20.0


@dataclass
class GPSPosition:
    """Position data parsed from NMEA sentences"""
    timestamp: float  # UTC timestamp
    latitude: float  # decimal degrees (north is positive)
    longitude: float  # decimal degrees (east is positive)
    altitude_msl: float  # meters
    ground_speed: float  # knots
    track_true: float  # degrees true
    fix_quality: int  # 0=invalid, 1=GPS fix, 2=DGPS fix
    satellites: int  # number of satellites in view
    valid: bool  # is the position valid


@dataclass
class SoaringData:
    """Soaring-specific data parsed from LXWP0 sentences"""
    timestamp: float  # UTC timestamp
    ias: float  # indicated airspeed in knots
    baro_altitude: float  # barometric altitude in meters
    vario: float  # vertical speed in m/s
    avg_vario: Optional[float]  # Average vario in m/s
    heading: float  # magnetic heading in degrees
    track_bearing: Optional[float]  # true track over ground in degrees
    turn_rate: Optional[float]  # turn rate in degrees/second
    valid: bool  # is the data valid


class NMEAParser:
    """
    Parser for NMEA sentences from Condor Soaring Simulator
    """

    def __init__(self):
        # Configure logger
        self.logger = logging.getLogger('nmea_parser')

        # Store latest parsed data
        self.gps_position: Optional[GPSPosition] = None
        self.soaring_data: Optional[SoaringData] = None

        # For tracking reception status
        self.last_gps_time = 0
        self.last_soaring_time = 0

        # Recognizable sentence patterns
        self.patterns = {
            "GPGGA": re.compile(r'^\$GPGGA'),
            "GPRMC": re.compile(r'^\$GPRMC'),
            "LXWP0": re.compile(r'^\$LXWP0')
        }

    def _validate_sentence_length(self, sentence: str) -> bool:
        """
        Validate NMEA sentence length.

        Args:
            sentence: NMEA sentence to validate

        Returns:
            bool: True if length is valid
        """
        if len(sentence) > MAX_NMEA_LENGTH:
            self.logger.warning(f"Sentence too long: {len(sentence)} chars (max: {MAX_NMEA_LENGTH})")
            return False
        return True

    def _validate_coordinates(self, latitude: float, longitude: float) -> bool:
        """
        Validate latitude and longitude values.

        Args:
            latitude: Latitude in decimal degrees
            longitude: Longitude in decimal degrees

        Returns:
            bool: True if coordinates are valid
        """
        if not (MIN_LATITUDE <= latitude <= MAX_LATITUDE):
            self.logger.error(f"Invalid latitude: {latitude} (must be between {MIN_LATITUDE} and {MAX_LATITUDE})")
            return False
        if not (MIN_LONGITUDE <= longitude <= MAX_LONGITUDE):
            self.logger.error(f"Invalid longitude: {longitude} (must be between {MIN_LONGITUDE} and {MAX_LONGITUDE})")
            return False
        return True

    def _validate_altitude(self, altitude: float) -> bool:
        """
        Validate altitude value.

        Args:
            altitude: Altitude in meters

        Returns:
            bool: True if altitude is valid
        """
        if not (MIN_ALTITUDE_M <= altitude <= MAX_ALTITUDE_M):
            self.logger.warning(f"Altitude out of range: {altitude}m (expected {MIN_ALTITUDE_M} to {MAX_ALTITUDE_M})")
            return False
        return True

    def _validate_speed(self, speed: float) -> bool:
        """
        Validate speed value.

        Args:
            speed: Speed in knots

        Returns:
            bool: True if speed is valid
        """
        if not (MIN_SPEED_KTS <= speed <= MAX_SPEED_KTS):
            self.logger.warning(f"Speed out of range: {speed} kts (expected {MIN_SPEED_KTS} to {MAX_SPEED_KTS})")
            return False
        return True

    def _validate_vario(self, vario: float) -> bool:
        """
        Validate variometer value.

        Args:
            vario: Vertical speed in m/s

        Returns:
            bool: True if vario is valid
        """
        if not (MIN_VARIO_MPS <= vario <= MAX_VARIO_MPS):
            self.logger.warning(f"Vario out of range: {vario} m/s (expected {MIN_VARIO_MPS} to {MAX_VARIO_MPS})")
            return False
        return True

    def parse_sentence(self, sentence: str) -> bool:
        """
        Parse an NMEA sentence and update the corresponding data object
        Returns True if the sentence was recognized and parsed successfully
        """
        sentence = sentence.strip()

        # Quick check for empty input
        if not sentence:
            return False

        # Validate sentence length
        if not self._validate_sentence_length(sentence):
            return False

        # Check for checksum validity (if present)
        if '*' in sentence:
            parts = sentence.split('*')
            if len(parts) == 2 and len(parts[1]) >= 2:
                checksum = int(parts[1][:2], 16)
                calc_checksum = self._calculate_checksum(parts[0])
                if checksum != calc_checksum:
                    self.logger.warning(f"Invalid checksum in sentence: {sentence}")
                    return False  # Invalid checksum

        # Determine sentence type and parse accordingly
        if self.patterns["GPGGA"].match(sentence):
            return self._parse_gpgga(sentence)
        elif self.patterns["GPRMC"].match(sentence):
            return self._parse_gprmc(sentence)
        elif self.patterns["LXWP0"].match(sentence):
            return self._parse_lxwp0(sentence)

        return False  # Unrecognized sentence

    def _calculate_checksum(self, data: str) -> int:
        """Calculate the checksum for an NMEA sentence"""
        # Skip the $ at the beginning
        data = data[1:] if data.startswith('$') else data

        # XOR all bytes
        checksum = 0
        for char in data:
            checksum ^= ord(char)

        return checksum

    def _parse_gpgga(self, sentence: str) -> bool:
        """
        Parse $GPGGA sentence (Global Positioning System Fix Data)
        Format: $GPGGA,time,lat,N/S,lon,E/W,quality,satellites,hdop,altitude,M,geoid,M,age,ref*checksum
        """
        try:
            # Split the sentence into fields
            fields = sentence.split(',')
            if len(fields) < 15:
                self.logger.warning(f"GPGGA sentence has too few fields: {sentence}")
                return False  # Not enough fields

            # Extract values
            time_str = fields[1]
            lat_str = fields[2]
            lat_dir = fields[3]
            lon_str = fields[4]
            lon_dir = fields[5]
            quality = fields[6]
            satellites = fields[7]
            altitude = fields[9]

            # Convert time format HHMMSS.SSS to a timestamp
            if time_str:
                hours = int(time_str[0:2])
                minutes = int(time_str[2:4])
                seconds = float(time_str[4:])
                timestamp = hours * 3600 + minutes * 60 + seconds
            else:
                timestamp = time.time()  # Use system time if not available

            # Convert latitude from DDMM.MMMMM format to decimal degrees
            if lat_str and lat_dir:
                lat_deg = float(lat_str[0:2])
                lat_min = float(lat_str[2:])
                latitude = lat_deg + (lat_min / 60.0)
                if lat_dir == 'S':
                    latitude = -latitude
            else:
                latitude = 0.0

            # Convert longitude from DDDMM.MMMMM format to decimal degrees
            if lon_str and lon_dir:
                lon_deg = float(lon_str[0:3])
                lon_min = float(lon_str[3:])
                longitude = lon_deg + (lon_min / 60.0)
                if lon_dir == 'W':
                    longitude = -longitude
            else:
                longitude = 0.0

            # Parse other numeric values
            fix_quality = int(quality) if quality else 0
            sats = int(satellites) if satellites else 0
            alt_msl = float(altitude) if altitude else 0.0

            # Validate coordinates
            if not self._validate_coordinates(latitude, longitude):
                self.logger.error(f"Invalid coordinates in GPGGA: lat={latitude}, lon={longitude}")
                return False

            # Validate altitude
            if not self._validate_altitude(alt_msl):
                self.logger.warning(f"Suspicious altitude in GPGGA: {alt_msl}m")
                # Don't return False, just warn - altitude could be temporarily invalid

            # Update GPS position (only partial data from GGA)
            if not self.gps_position:
                self.gps_position = GPSPosition(
                    timestamp=timestamp,
                    latitude=latitude,
                    longitude=longitude,
                    altitude_msl=alt_msl,
                    ground_speed=0.0,  # Will be updated by RMC if available
                    track_true=0.0,  # Will be updated by RMC if available
                    fix_quality=fix_quality,
                    satellites=sats,
                    valid=(fix_quality > 0)
                )
            else:
                # Update existing position with GGA data
                self.gps_position.timestamp = timestamp
                self.gps_position.latitude = latitude
                self.gps_position.longitude = longitude
                self.gps_position.altitude_msl = alt_msl
                self.gps_position.fix_quality = fix_quality
                self.gps_position.satellites = sats
                self.gps_position.valid = (fix_quality > 0)

            self.last_gps_time = time.time()
            return True

        except (ValueError, IndexError) as e:
            self.logger.error(f"Error parsing GPGGA: {e} in sentence: {sentence}")
            return False

    def _parse_gprmc(self, sentence: str) -> bool:
        """
        Parse $GPRMC sentence (Recommended Minimum Navigation Information)
        Format: $GPRMC,time,status,lat,N/S,lon,E/W,speed,course,date,mag_var,E/W*checksum
        """
        try:
            # Split the sentence into fields
            fields = sentence.split(',')
            if len(fields) < 12:
                self.logger.warning(f"GPRMC sentence has too few fields: {sentence}")
                return False  # Not enough fields

            # Extract values
            time_str = fields[1]
            status = fields[2]  # A=active, V=void
            lat_str = fields[3]
            lat_dir = fields[4]
            lon_str = fields[5]
            lon_dir = fields[6]
            speed = fields[7]  # Speed over ground in knots
            course = fields[8]  # Course over ground in degrees true

            # Convert time format HHMMSS.SSS to a timestamp
            if time_str:
                hours = int(time_str[0:2])
                minutes = int(time_str[2:4])
                seconds = float(time_str[4:])
                timestamp = hours * 3600 + minutes * 60 + seconds
            else:
                timestamp = time.time()  # Use system time if not available

            # Convert latitude from DDMM.MMMMM format to decimal degrees
            if lat_str and lat_dir:
                lat_deg = float(lat_str[0:2])
                lat_min = float(lat_str[2:])
                latitude = lat_deg + (lat_min / 60.0)
                if lat_dir == 'S':
                    latitude = -latitude
            else:
                latitude = 0.0

            # Convert longitude from DDDMM.MMMMM format to decimal degrees
            if lon_str and lon_dir:
                lon_deg = float(lon_str[0:3])
                lon_min = float(lon_str[3:])
                longitude = lon_deg + (lon_min / 60.0)
                if lon_dir == 'W':
                    longitude = -longitude
            else:
                longitude = 0.0

            # Parse other numeric values
            ground_speed = float(speed) if speed else 0.0
            track_true = float(course) if course else 0.0
            is_valid = (status == 'A')

            # Validate coordinates
            if not self._validate_coordinates(latitude, longitude):
                self.logger.error(f"Invalid coordinates in GPRMC: lat={latitude}, lon={longitude}")
                return False

            # Validate speed
            if not self._validate_speed(ground_speed):
                self.logger.warning(f"Suspicious speed in GPRMC: {ground_speed} kts")
                # Don't return False, just warn

            # Create or update GPS position
            if not self.gps_position:
                self.gps_position = GPSPosition(
                    timestamp=timestamp,
                    latitude=latitude,
                    longitude=longitude,
                    altitude_msl=0.0,  # Will be updated by GGA if available
                    ground_speed=ground_speed,
                    track_true=track_true,
                    fix_quality=1 if is_valid else 0,
                    satellites=0,  # Will be updated by GGA if available
                    valid=is_valid
                )
            else:
                # Update existing position with RMC data
                self.gps_position.timestamp = timestamp
                self.gps_position.latitude = latitude
                self.gps_position.longitude = longitude
                self.gps_position.ground_speed = ground_speed
                self.gps_position.track_true = track_true
                # Only override validity if RMC says it's invalid
                if not is_valid:
                    self.gps_position.valid = False

            self.last_gps_time = time.time()
            return True

        except (ValueError, IndexError) as e:
            self.logger.error(f"Error parsing GPRMC: {e} in sentence: {sentence}")
            return False

    def _parse_lxwp0(self, sentence: str) -> bool:
        """
        Parse $LXWP0 sentence (LX Navigation proprietary for soaring data)
        Format: $LXWP0,logger_stored,IAS,baroAlt,vario,,,,,,,heading,track_bearing,turn_rate*checksum

        Condor's format might vary, so we'll be more flexible about field positions.
        """
        try:
            # Split the sentence into fields
            parts = sentence.split('*')
            fields = parts[0].split(',')
            if len(fields) < 11:  # Need at least 11 fields to have heading
                self.logger.warning(f"LXWP0 sentence has too few fields: {sentence}")
                return False

            # Log the raw sentence for debugging
            self.logger.debug(f"Parsing LXWP0: {sentence} with {len(fields)} fields")

            # Extract values
            # First field is always LXWP0, second is logger_stored
            ias_str = fields[2]  # Indicated airspeed in knots
            alt_str = fields[3]  # Barometric altitude in meters
            vario_str = fields[4]  # Vertical speed in m/s

            # Field 5 is typically average vario but could be empty
            avg_vario_str = fields[5] if len(fields) > 5 else ""

            # Heading is typically at position 11
            heading_str = fields[11] if len(fields) > 11 else ""

            # Track and turn rate positions can vary, we'll try to find them
            track_str = fields[12] if len(fields) > 12 else ""
            turn_rate_str = fields[13] if len(fields) > 13 else ""

            # Parse numeric values
            ias = float(ias_str) if ias_str else 0.0
            baro_alt = float(alt_str) if alt_str else 0.0
            vario = float(vario_str) if vario_str else 0.0
            avg_vario = float(avg_vario_str) if avg_vario_str and avg_vario_str.strip() else None
            heading = float(heading_str) if heading_str else 0.0
            track = float(track_str) if track_str and track_str.strip() else None
            turn_rate = float(turn_rate_str) if turn_rate_str and turn_rate_str.strip() else None

            # Log the extracted values for debugging
            self.logger.debug(f"LXWP0 extracted values: IAS={ias}, Baro={baro_alt}, Vario={vario}, "
                              f"AvgVario={avg_vario}, Heading={heading}, Track={track}, TurnRate={turn_rate}")

            # Validate values
            if not self._validate_speed(ias):
                self.logger.warning(f"Suspicious IAS in LXWP0: {ias} kts")
                # Don't return False, just warn

            if not self._validate_altitude(baro_alt):
                self.logger.warning(f"Suspicious barometric altitude in LXWP0: {baro_alt}m")
                # Don't return False, just warn

            if not self._validate_vario(vario):
                self.logger.warning(f"Suspicious vario in LXWP0: {vario} m/s")
                # Don't return False, just warn

            # Use current time or GPS time if available
            timestamp = self.gps_position.timestamp if self.gps_position else time.time()

            # Create or update soaring data
            self.soaring_data = SoaringData(
                timestamp=timestamp,
                ias=ias,
                baro_altitude=baro_alt,
                vario=vario,
                avg_vario=avg_vario,
                heading=heading,
                track_bearing=track,
                turn_rate=turn_rate,
                valid=True
            )

            self.last_soaring_time = time.time()
            return True

        except (ValueError, IndexError) as e:
            self.logger.error(f"Error parsing LXWP0: {e} in sentence: {sentence}")
            return False

    def is_data_fresh(self) -> Tuple[bool, bool]:
        """
        Check if GPS and soaring data are fresh (received within the last 5 seconds)
        Returns (gps_fresh, soaring_fresh)
        """
        now = time.time()
        gps_fresh = (now - self.last_gps_time) < 5.0
        soaring_fresh = (now - self.last_soaring_time) < 5.0
        return (gps_fresh, soaring_fresh)

    def get_combined_data(self) -> Dict[str, Any]:
        """
        Return a combined dictionary with all available data
        """
        result = {}

        # Check data freshness
        gps_fresh, soaring_fresh = self.is_data_fresh()

        # Add GPS data if available
        if self.gps_position and gps_fresh:
            result.update({
                "latitude": self.gps_position.latitude,
                "longitude": self.gps_position.longitude,
                "altitude_msl": self.gps_position.altitude_msl,
                "ground_speed": self.gps_position.ground_speed,
                "track_true": self.gps_position.track_true,
                "gps_valid": self.gps_position.valid,
                "fix_quality": self.gps_position.fix_quality,
                "satellites": self.gps_position.satellites
            })

        # Add soaring data if available
        if self.soaring_data and soaring_fresh:
            result.update({
                "ias": self.soaring_data.ias,
                "baro_altitude": self.soaring_data.baro_altitude,
                "vario": self.soaring_data.vario,
                "avg_vario": self.soaring_data.avg_vario,
                "heading": self.soaring_data.heading,
                "track_bearing": self.soaring_data.track_bearing,
                "turn_rate": self.soaring_data.turn_rate
            })

        return result


# Example usage:
if __name__ == "__main__":
    # Configure logging for the test
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    parser = NMEAParser()

    # Test with sample sentences
    test_sentences = [
        "$GPGGA,170000.021,4553.3709,N,01353.4357,E,1,12,10,117.4,M,,,,,0000*02",
        "$GPRMC,170000.021,A,4553.3709,N,01353.4357,E,0.00,267.45,,,,*23",
        "$LXWP0,Y,17.5,117.4,0.00,,,,,,268,268,0.0*7A"
    ]

    for sentence in test_sentences:
        result = parser.parse_sentence(sentence)
        print(f"Parsed: {sentence}")
        print(f"Result: {result}")

    # Display combined data
    combined = parser.get_combined_data()
    print("\nCombined Data:")
    for key, value in combined.items():
        print(f"{key}: {value}")