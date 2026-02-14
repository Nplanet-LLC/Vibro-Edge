# Vibro Edge Device

Raspberry Pi edge device software for the Vibro Monitoring System.

## Features

- Real-time vibration data acquisition
- ADC interface (ADS1256)
- Signal processing (FFT, RMS, Peak)
- MQTT communication
- Offline data buffering
- Automatic device registration
- Connection monitoring
- UUID-based device identification

## Hardware Requirements

- Raspberry Pi 4 (recommended) or Pi 3B+
- ADS1256 ADC module
- Vibration sensors (accelerometers)
- MicroSD card (16GB minimum)
- Power supply (5V, 3A)
- Internet connection (WiFi or Ethernet)

## Software Requirements

- Raspberry Pi OS (Bullseye or newer)
- Python 3.9+
- pip3
- SPI enabled

## Installation

### Quick Install

```bash
# Download and run install script
curl -sSL https://raw.githubusercontent.com/Nplanet-LLC/Vibro-Edge/main/install.sh | bash
```

### Manual Installation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python dependencies
sudo apt install -y python3-pip python3-dev python3-venv

# Clone repository
git clone git@github.com:Nplanet-LLC/Vibro-Edge.git
cd Vibro-Edge

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt

# Copy configuration
cp config.example.json config.json

# Edit configuration
nano config.json
```

## Configuration

Edit `config.json`:

```json
{
  "mqtt": {
    "broker": "mqtt.your-server.com",
    "port": 1883,
    "username": "edge_device",
    "password": "your-password",
    "topic_prefix": "vibro"
  },
  "api": {
    "url": "https://api.your-server.com",
    "register_endpoint": "/api/devices/register"
  },
  "adc": {
    "sample_rate": 30000,
    "gain": 1,
    "channels": [0, 1, 2, 3]
  },
  "processing": {
    "window_size": 8192,
    "overlap": 0.5,
    "fft_size": 8192
  },
  "buffer": {
    "max_size": 1000,
    "flush_interval": 60
  }
}
```

## Enable SPI

```bash
# Enable SPI interface
sudo raspi-config
# Navigate to: Interface Options → SPI → Enable

# Reboot
sudo reboot
```

## Running

### Development Mode

```bash
# Activate virtual environment
source venv/bin/activate

# Run main application
python main.py
```

### Production Mode (systemd)

```bash
# Copy service file
sudo cp vibro-edge.service /etc/systemd/system/

# Edit service file with correct paths
sudo nano /etc/systemd/system/vibro-edge.service

# Enable and start service
sudo systemctl enable vibro-edge
sudo systemctl start vibro-edge

# Check status
sudo systemctl status vibro-edge

# View logs
sudo journalctl -u vibro-edge -f
```

## Modules

### ADC Interface (`modules/adc_interface.py`)
- Interfaces with ADS1256 ADC
- Configures sampling rate and gain
- Reads multi-channel data

### Signal Processor (`modules/signal_processor.py`)
- Performs FFT analysis
- Calculates RMS values
- Detects peak frequencies
- Applies windowing functions

### MQTT Client (`modules/mqtt_client.py`)
- Connects to MQTT broker
- Publishes sensor data
- Handles reconnection
- QoS management

### Device Registration (`modules/device_registration.py`)
- Generates unique device UUID
- Registers with backend API
- Stores device credentials

### Offline Buffer (`modules/offline_buffer.py`)
- Buffers data when offline
- Automatic flush when online
- Persistent storage

### Connection Monitor (`modules/connection_monitor.py`)
- Monitors internet connectivity
- Tracks connection status
- Triggers reconnection

### UUID Manager (`modules/uuid_manager.py`)
- Generates hardware-based UUID
- Persistent storage
- Validation

## Testing

```bash
# Run all tests
python -m pytest

# Run specific test
python -m pytest tests/test_adc_interface.py

# Run with coverage
python -m pytest --cov=modules

# Manual ADC test
python test_adc_manual.py
```

## Data Format

### Published MQTT Message

```json
{
  "device_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-02-14T10:30:00Z",
  "channels": [
    {
      "channel": 0,
      "rms": 0.0234,
      "peak_frequency": 120.5,
      "peak_amplitude": 0.0456,
      "waveform": [0.01, 0.02, ...],
      "fft": [0.001, 0.002, ...]
    }
  ],
  "status": "online"
}
```

## Troubleshooting

### SPI Not Working
```bash
# Check SPI is enabled
lsmod | grep spi

# Should see: spi_bcm2835
```

### ADC Not Detected
```bash
# Check wiring
# Verify power supply
# Test with simple read script
python test_adc_manual.py
```

### MQTT Connection Failed
```bash
# Test MQTT broker
mosquitto_pub -h mqtt.server.com -t test -m "hello"

# Check credentials in config.json
# Verify network connectivity
```

### High CPU Usage
```bash
# Reduce sample rate in config.json
# Increase processing interval
# Check for memory leaks
```

## Hardware Setup

### ADS1256 Wiring

| ADS1256 Pin | Raspberry Pi Pin |
|-------------|------------------|
| VCC         | 3.3V (Pin 1)     |
| GND         | GND (Pin 6)      |
| SCLK        | SCLK (Pin 23)    |
| DIN         | MOSI (Pin 19)    |
| DOUT        | MISO (Pin 21)    |
| CS          | CE0 (Pin 24)     |
| DRDY        | GPIO17 (Pin 11)  |

### Sensor Connection

Connect accelerometers to ADC channels:
- Channel 0: X-axis
- Channel 1: Y-axis
- Channel 2: Z-axis
- Channel 3: Temperature (optional)

## Performance

- Sample Rate: Up to 30 kSPS
- FFT Size: 8192 points
- Processing Time: ~50ms per window
- MQTT Publish Rate: 1 Hz
- CPU Usage: ~15-25%
- Memory Usage: ~100 MB

## Updates

```bash
# Pull latest changes
cd Vibro-Edge
git pull

# Update dependencies
pip install -r requirements.txt --upgrade

# Restart service
sudo systemctl restart vibro-edge
```

## Security

- Store credentials securely
- Use encrypted MQTT (TLS)
- Restrict SSH access
- Keep system updated
- Use strong passwords

## Contributing

1. Create a feature branch
2. Make your changes
3. Test on actual hardware
4. Submit a pull request

## License

Proprietary - Nplanet LLC

## Support

For issues or questions, contact the development team.
