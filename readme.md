# Condor-Shirley-Bridge

A bridge application connecting Condor Soaring Simulator with the FlyShirley electronic flight bag.

## Overview

Condor-Shirley-Bridge bridges the gap between Condor Soaring Simulator and FlyShirley by:

1. Collecting flight data from Condor Soaring Simulator in two formats:
   - NMEA sentences via a virtual COM port
   - Proprietary UDP messages with extended flight parameters

2. Processing and combining this data into a unified flight model

3. Serving the processed data to FlyShirley via WebSocket in a compatible format

The result is a seamless integration that enriches your virtual soaring experience with FlyShirley's powerful electronic flight bag features.

## Features

- **Dual-source data integration** - Merges position data from NMEA with attitude data from UDP
- **Complete flight parameters** - Position, altitude, speed, vario, attitude, G-force, and more
- **WebSocket API** - Compatible with FlyShirley's WebSocket client
- **User-friendly GUI** - Easy configuration and real-time status monitoring
- **Comprehensive settings** - Configure all aspects of the connection
- **Dual-mode operation** - Run with GUI or in headless CLI mode
- **Detailed logging** - Configurable logging for troubleshooting

## Installation

### Prerequisites

- Python 3.8 or later
- Condor Soaring Simulator with NMEA and UDP output enabled
- FlyShirley application (configured to use WebSocket)

### Dependencies

- pyserial - For serial port communication
- websockets - For WebSocket server functionality
- tkinter - For the GUI (usually comes with Python)

### Installation Steps

1. Clone the repository:
   ```
   git clone https://github.com/jlgabriel/Condor-Shirley-Bridge.git
   cd Condor-Shirley-Bridge
   ```

2. Install the package and dependencies:
   ```
   pip install -e .
   ```

3. Run the application:
   ```
   python -m condor_shirley_bridge
   ```

## Configuration

### Condor Setup

1. In Condor, enable NMEA output to a virtual COM port
   - Use a virtual serial port tool like com0com if needed
   - Default port is COM4 at 4800 baud

2. Enable UDP output in Condor
   - Should be sending to IP 127.0.0.1 port 55278

### FlyShirley Setup

Configure FlyShirley to connect to the WebSocket server:
- Address: ws://localhost:2992/api/v1
- (Or use the IP address of the computer running the bridge if different)

### Bridge Configuration

The application uses a configuration file located at:
- Windows: `C:\Users\<username>\.condor_shirley_bridge\config.json`
- macOS/Linux: `~/.condor_shirley_bridge/config.json`

Default settings:
- Serial: COM4, 4800 baud
- UDP: 0.0.0.0:55278
- WebSocket: 0.0.0.0:2992/api/v1

You can modify these settings through the GUI or by editing the configuration file directly.

## Usage

### GUI Mode

To start with the graphical interface:

```
python -m condor_shirley_bridge
```

The GUI provides:
- Status indicators for all connections
- Real-time flight data display
- Settings configuration
- Start/stop controls

### CLI Mode

For headless operation:

```
python -m condor_shirley_bridge --cli
```

### Command-line Options

```
usage: condor_shirley_bridge [-h] [--cli] [--config CONFIG] [--start] [--minimized]
                            [--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}] [--log-file LOG_FILE]

options:
  -h, --help            show this help message and exit
  --cli                 Run in command-line mode (no GUI)
  --config CONFIG, -c CONFIG
                        Path to configuration file
  --start               Automatically start the bridge on launch
  --minimized           Start minimized (GUI mode only)
  --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Set logging level
  --log-file LOG_FILE   Log to specified file
```

## How It Works

1. **Data Collection**:
   - NMEA Parser interprets serial data from Condor
   - UDP Receiver collects proprietary Condor messages

2. **Data Processing**:
   - SimData module combines data from both sources
   - Resolves conflicts and fills in missing information
   - Converts units as necessary

3. **Data Distribution**:
   - WebSocket Server broadcasts to FlyShirley at configurable intervals
   - Data is formatted according to FlyShirley's API expectations

## Development

### Project Structure

```
condor_shirley_bridge/
├── core/              # Core functionality
│   ├── bridge.py      # Main orchestrator
│   ├── settings.py    # Configuration management
│   └── sim_data.py    # Flight data model
├── gui/               # GUI components
│   ├── main_window.py # Main application window
│   ├── status_panel.py # Flight data display
│   └── settings_dialog.py # Settings configuration
├── io/                # Input/output components
│   ├── serial_reader.py # NMEA serial port reader
│   ├── udp_receiver.py # Condor UDP receiver
│   └── websocket_server.py # FlyShirley interface
└── parsers/           # Data parsers
    ├── nmea_parser.py # NMEA sentence parser
    └── condor_parser.py # Condor UDP parser
```

### Building from Source

To build the project from source:

```
python setup.py build
python setup.py install
```

## Troubleshooting

### Common Issues

**No NMEA data received**:
- Verify Condor is configured to output NMEA
- Check the correct COM port is selected
- Ensure no other application is using the COM port

**No UDP data received**:
- Confirm Condor is configured to send UDP data
- Check firewall settings
- Verify correct port number

**FlyShirley not connecting**:
- Ensure WebSocket server is running
- Check network connectivity between devices
- Verify WebSocket URI format in FlyShirley

**Application crashing**:
- Check log file for error details
- Verify all dependencies are installed
- Try running with `--log-level DEBUG` for more information

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Thanks to the Condor Soaring Simulator Team for the great gliding experience.

- Based on https://github.com/Airplane-Team/sim-interface by Airplane Team.

- Based on https://github.com/jlgabriel/ForeFlight-Shirley-Bridge by Juan Luis Gabriel.

