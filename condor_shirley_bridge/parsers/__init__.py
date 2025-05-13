#!/usr/bin/env python3

"""
Package initialization for condor_shirley_bridge.parsers
Module for parsing data from Condor Soaring Simulator.

Part of the Condor-Shirley-Bridge project.
"""

from condor_shirley_bridge.parsers.nmea_parser import NMEAParser
from condor_shirley_bridge.parsers.condor_parser import CondorUDPParser

__all__ = ['NMEAParser', 'CondorUDPParser']
