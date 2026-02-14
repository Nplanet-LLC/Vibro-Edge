# Edge Device (Raspberry Pi)

Python application for Raspberry Pi 4 that collects vibration data from 4 sensors, performs FFT analysis, and transmits data to the backend via MQTT.

## Features

- 4-channel ADC interface (SPI)
- Real-time FFT analysis per channel
- Offline data buffering (SQLite)
- MQTT client with auto-reconnect
- Automatic device registration

## Hardware Requirements

- Raspberry Pi 4 (4GB RAM)
- Multi-channel ADC (ADS1256 or 4x ADS1115)
- 4x Vibration sensors
- WiFi connection

## Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure device
sudo mkdir -p /etc/turbine-monitor
sudo cp config.example.json /etc/turbine-monitor/config.json
sudo nano /etc/turbine-monitor/config.json

# Run application
python main.py
```

## Configuration

Edit `/etc/turbine-monitor/config.json`:

```json
{
  "mqtt": {
    "broker": "mqtt.yourdomain.com",
    "port": 8883,
    "use_tls": true
  },
  "adc": {
    "model": "ADS1256",
    "sample_rate": 1000,
    "channels": [0, 1, 2, 3]
  },
  "backend_url": "https://api.yourdomain.com"
}
```

## Development

```bash
# Run tests
pytest tests/

# Run with debug logging
python main.py --debug
```
