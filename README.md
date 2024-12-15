# Sensor Monitoring Application

## Overview

This is a Raspberry Pi-based temperature and humidity monitoring application with web interface and relay control. The application uses a DHT22 sensor to collect environmental data, stores readings in a SQLite database, and provides a web dashboard for real-time monitoring and relay management.

## Features

- Real-time temperature and humidity monitoring
- Web-based dashboard with interactive charts
- Configurable relay control based on temperature and humidity thresholds
- Logging of sensor readings and relay state changes
- Manual relay control via web interface
- Responsive design for mobile and desktop

## Hardware Requirements

- Raspberry Pi (tested on Raspberry Pi 4)
- DHT22 temperature and humidity sensor
- Two relays for environmental control
- Jumper wires
- (Optional) Breadboard for connections

## Software Requirements

- Raspberry Pi OS (Debian-based)
- Python 3.7+
- pip
- SQLite3

## Installation

### Manual Installation

1. Clone the repository
2. Install Python dependencies
3. Configure GPIO pins
4. Set up systemd service or use manual startup

## GPIO Configuration

- DHT22 Sensor: GPIO 17
- Relay 1: GPIO 18
- Relay 2: GPIO 19

## Configuration

Edit `config.json` to set temperature and humidity thresholds:

```json
{
    "temperature_threshold": 24.0,
    "temperature_hysteresis": 1.0,
    "humidity_threshold": 60.0,
    "humidity_hysteresis": 2.0
}
```

## Running the Application

- Web Interface: `http://<raspberry_pi_ip>`
- Automatic startup via systemd service
- Manual startup: `python3 app.py`

## Logging

Logs are stored in `sensor_app.log`, capturing:
- Sensor readings
- Relay state changes
- System events
- Errors


## Troubleshooting

- Check `sensor_app.log` for detailed error information
- Verify GPIO pin connections
- Ensure DHT22 sensor is functioning correctly
- Confirm Python dependencies are installed