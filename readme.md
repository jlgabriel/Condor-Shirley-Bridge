# Condor-Shirley-Bridge
[![GitHub license](https://img.shields.io/badge/license-MIT-blue.svg)](

A bridge application that connects Condor Soaring Simulator with the FlyShirley electronic flight bag.

## Overview

Condor-Shirley-Bridge receives data from Condor Soaring Simulator in two formats:
1. NMEA sentences via serial port (virtual COM port)
2. Proprietary UDP messages with additional flight data

It processes this data, combines it, and serves it to FlyShirley via WebSocket in a format that FlyShirley can understand.

## Features

- **Dual-source data integration**: Combines NMEA and UDP data for a complete flight picture
- **WebSocket Server**: Compatible with FlyShirley's WebSocket API
- **User-friendly GUI**: Easy configuration and monitoring
- **Robust configuration**: All aspects are configurable
- **Command-line interface**: For headless operation
- **Comprehensive logging**: Detailed logging for troubleshooting

## Installation

### Requirements

- Python 3.8 or later
- Dependencies:
  - pyserial
  - websockets

### Installation Steps

1. Clone the repository:
   ```
   git clone https://github.com/jlgabriel/Condor-Shirley-Bridge.git
   cd Condor-Shirley-Bridge
   ```

2. Install the package:
   ```
   pip install -e .
   ```

## Usage

### GUI Mode

To start the application with GUI:

```
python -m main.py
```


### CLI Mode

To run in command-line mode:

```
python -m main.py --cli
```

### Command-line Options

- `--cli`: Run in command-line mode (no GUI)
- `--config PATH`: Specify a configuration file
- `--start`: Automatically start the bridge on launch
- `--minimized`: Start minimized (GUI mode only)
- `--log-level LEVEL`: Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `--log-file PATH`: Log to specified file

## Configuration

The application uses a JSON configuration file located at:
- Windows: `C:\Users\<username>\.condor_shirley_bridge\config.json`
- macOS/Linux: `~/.condor_shirley_bridge/config.json`

You can also specify a different configuration file using the `--config` option.

### Default Settings

- Serial: COM4, 4800 baud
- UDP: 0.0.0.0:55278
- WebSocket: 0.0.0.0:2992/api/v1

## How It Works

1. The application connects to Condor Soaring Simulator via:
   - NMEA sentences from a virtual COM port
   - UDP messages on port 55278

2. It processes and combines this data into a unified model.

3. The data is then served to FlyShirley via WebSocket on port 2992, path `/api/v1`.

4. FlyShirley connects to this WebSocket server to receive real-time flight data.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

Based on https://github.com/Airplane-Team/sim-interface by Airplane Team.

Based on https://github.com/jlgabriel/ForeFlight-Shirley-Bridge by Juan Luis Gabriel.

