#!/usr/bin/env python3

"""
Condor-Shirley-Bridge
A bridge between Condor Soaring Simulator and FlyShirley.

This package provides a bridge application that connects
Condor Soaring Simulator with the FlyShirley electronic flight bag.
It receives data from Condor in NMEA and UDP formats, processes it,
and serves it to FlyShirley via WebSocket.

Main components:
- Parsers: Convert Condor's data formats to a unified representation
- IO: Handle communication with Condor and FlyShirley
- Core: Central data model and bridge orchestration
- GUI: User interface for configuration and monitoring

Based on ForeFlight-Shirley-Bridge by Juan Luis Gabriel.
"""

from condor_shirley_bridge.parsers import NMEAParser, CondorUDPParser
from condor_shirley_bridge.io import SerialReader, UDPReceiver, WebSocketServer
from condor_shirley_bridge.core import SimData, Settings, Bridge
from condor_shirley_bridge.gui import MainWindow, StatusPanel, SettingsDialog

__version__ = "1.0.0"
__author__ = "Juan Luis Gabriel"
__license__ = "MIT"

__all__ = [
    'NMEAParser', 'CondorUDPParser',
    'SerialReader', 'UDPReceiver', 'WebSocketServer',
    'SimData', 'Settings', 'Bridge',
    'MainWindow', 'StatusPanel', 'SettingsDialog'
]
