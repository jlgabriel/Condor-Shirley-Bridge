#!/usr/bin/env python3

"""
Constants for Condor-Shirley-Bridge
Centralized configuration values and magic numbers.

Part of the Condor-Shirley-Bridge project.
"""

# =============================================================================
# TIMING CONSTANTS (seconds)
# =============================================================================

COMPONENT_CHECK_INTERVAL = 1.0      # How often to check component status
COMPONENT_CHECK_TIMEOUT = 5.0       # Timeout for component checks
DATA_FRESHNESS_THRESHOLD = 5.0      # How long data is considered fresh
LOG_STATUS_INTERVAL = 10.0          # How often to log status
NO_DATA_WARNING_THRESHOLD = 10.0    # Warn if no data for this long


# =============================================================================
# QUEUE AND BUFFER SIZES
# =============================================================================

SERIAL_QUEUE_MAX_SIZE = 100         # Maximum items in serial data queue
UDP_QUEUE_MAX_SIZE = 100            # Maximum items in UDP data queue
HISTORY_MAX_SIZE = 20               # Maximum historical data points
HISTORY_MAX_AGE = 60.0              # Maximum age of historical data (seconds)


# =============================================================================
# NETWORK CONSTANTS
# =============================================================================

DEFAULT_BROADCAST_INTERVAL = 0.25   # WebSocket broadcast interval (4 Hz)
DEFAULT_SERIAL_BAUDRATE = 4800      # Standard NMEA baudrate
DEFAULT_SERIAL_TIMEOUT = 1.0        # Serial port timeout (seconds)
DEFAULT_UDP_PORT = 55278            # Condor UDP output port
DEFAULT_UDP_HOST = "0.0.0.0"        # Bind to all interfaces
DEFAULT_WEBSOCKET_PORT = 2992       # FlyShirley WebSocket port
DEFAULT_WEBSOCKET_HOST = "0.0.0.0"  # Bind to all interfaces
DEFAULT_WEBSOCKET_PATH = "/api/v1"  # FlyShirley API path
MAX_UDP_BUFFER_SIZE = 65535         # Maximum UDP receive buffer


# =============================================================================
# RECONNECTION CONSTANTS
# =============================================================================

DEFAULT_MAX_RETRIES = 5             # Maximum reconnection attempts
DEFAULT_RETRY_DELAY = 2.0           # Initial retry delay (seconds)
MAX_RECONNECT_DELAY = 64.0          # Maximum delay between retries (exponential backoff cap)


# =============================================================================
# UI CONSTANTS
# =============================================================================

MAX_RECENT_CONFIGS = 10             # Maximum recent config files to track


# =============================================================================
# VALIDATION CONSTANTS - MESSAGE LENGTH
# =============================================================================

MAX_NMEA_LENGTH = 256               # NMEA standard maximum (~82, with buffer)
MAX_UDP_MESSAGE_LENGTH = 4096       # Maximum UDP message length


# =============================================================================
# VALIDATION CONSTANTS - COORDINATES
# =============================================================================

MIN_LATITUDE = -90.0                # Minimum valid latitude (degrees)
MAX_LATITUDE = 90.0                 # Maximum valid latitude (degrees)
MIN_LONGITUDE = -180.0              # Minimum valid longitude (degrees)
MAX_LONGITUDE = 180.0               # Maximum valid longitude (degrees)


# =============================================================================
# VALIDATION CONSTANTS - ALTITUDE (meters)
# =============================================================================

MIN_ALTITUDE_M = -500.0             # Dead Sea level
MAX_ALTITUDE_M = 15000.0            # 15km - maximum realistic for gliders


# =============================================================================
# VALIDATION CONSTANTS - SPEED (knots)
# =============================================================================

MIN_SPEED_KTS = 0.0                 # Minimum speed
MAX_SPEED_KTS = 400.0               # Maximum realistic for gliders


# =============================================================================
# VALIDATION CONSTANTS - VARIOMETER (m/s)
# =============================================================================

MIN_VARIO_MPS = -20.0               # Maximum sink rate
MAX_VARIO_MPS = 20.0                # Maximum climb rate


# =============================================================================
# VALIDATION CONSTANTS - AIRSPEED (m/s)
# =============================================================================

MIN_AIRSPEED_MPS = 0.0              # Minimum airspeed
MAX_AIRSPEED_MPS = 150.0            # ~291 knots - maximum realistic


# =============================================================================
# VALIDATION CONSTANTS - G-FORCE
# =============================================================================

MIN_G_FORCE = -5.0                  # Negative G (inverted flight)
MAX_G_FORCE = 10.0                  # Positive G (extreme maneuvers)


# =============================================================================
# VALIDATION CONSTANTS - HEIGHT AGL (meters)
# =============================================================================

MIN_HEIGHT_AGL = -10.0              # Allow some negative for ground contact
MAX_HEIGHT_AGL = 15000.0            # Maximum height above ground


# =============================================================================
# CLEANUP INTERVALS
# =============================================================================

HISTORY_CLEANUP_INTERVAL = 10       # Clean history every N updates
QUEUE_CLEANUP_CHECK_INTERVAL = 100  # Check queue size every N items
