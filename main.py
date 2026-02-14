#!/usr/bin/env python3
"""
Main entry point for the Turbine Monitoring Edge Device application.

This application runs on Raspberry Pi 4 and:
- Collects vibration data from 4 sensors via ADC
- Performs FFT analysis on each channel
- Transmits data to backend via MQTT
- Buffers data offline when connection is lost

Requirements: 1.1, 2.1, 4.1, 5.1, 12.1
"""

import sys
import signal
import logging
import time
import json
from pathlib import Path
from typing import Optional

# Module imports
from modules.uuid_manager import UUIDManager
from modules.adc_interface import ADCInterface, ADCModel
from modules.signal_processor import SignalProcessor
from modules.mqtt_client import MQTTClient, ConnectionStatus as MQTTStatus
from modules.offline_buffer import OfflineBuffer
from modules.connection_monitor import ConnectionMonitor, ConnectionState
from modules.device_registration import DeviceRegistration

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        # logging.FileHandler('/var/log/turbine-monitor/app.log')
    ]
)

logger = logging.getLogger(__name__)


class TurbineMonitorApp:
    """
    Main application class for turbine monitoring edge device.
    
    Orchestrates all components and implements the main data collection loop.
    """
    
    def __init__(self, config: dict):
        """
        Initialize the application.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.running = False
        
        # Components
        self.uuid_manager: Optional[UUIDManager] = None
        self.adc: Optional[ADCInterface] = None
        self.signal_processor: Optional[SignalProcessor] = None
        self.mqtt_client: Optional[MQTTClient] = None
        self.offline_buffer: Optional[OfflineBuffer] = None
        self.connection_monitor: Optional[ConnectionMonitor] = None
        self.device_registration: Optional[DeviceRegistration] = None
        
        self.device_uuid: Optional[str] = None
        
        logger.info("Turbine Monitor Application initialized")
    
    def initialize(self) -> bool:
        """
        Initialize all components.
        
        Returns:
            True if initialization successful
        """
        try:
            # 1. Initialize UUID Manager
            logger.info("Initializing UUID Manager...")
            self.uuid_manager = UUIDManager()
            self.device_uuid = self.uuid_manager.get_or_create_uuid()
            logger.info(f"Device UUID: {self.device_uuid}")
            
            # 2. Initialize Device Registration
            logger.info("Initializing Device Registration...")
            self.device_registration = DeviceRegistration(
                backend_url=self.config.get("backend_url", "http://localhost:3000")
            )
            
            # Register device if not already registered
            if not self.device_registration.is_registered:
                logger.info("Registering device with backend...")
                success = self.device_registration.register(self.device_uuid)
                if not success:
                    logger.warning("Device registration failed, continuing anyway...")
            else:
                logger.info("Device already registered")
            
            # 3. Initialize ADC Interface
            logger.info("Initializing ADC Interface...")
            adc_config = self.config.get("adc", {})
            self.adc = ADCInterface(
                model=ADCModel.MOCK,  # Use MOCK for development
                sample_rate=adc_config.get("sample_rate", 1000),
                channels=adc_config.get("channels", [0, 1, 2, 3])
            )
            
            # 4. Initialize Signal Processor
            logger.info("Initializing Signal Processor...")
            self.signal_processor = SignalProcessor(
                sample_rate=adc_config.get("sample_rate", 1000),
                window_type="hann"
            )
            
            # 5. Initialize Offline Buffer
            logger.info("Initializing Offline Buffer...")
            buffer_config = self.config.get("offline_buffer", {})
            self.offline_buffer = OfflineBuffer(
                db_path=buffer_config.get("db_path", "./buffer.db"),
                max_size_mb=buffer_config.get("max_size_mb", 100)
            )
            
            # 6. Initialize MQTT Client
            logger.info("Initializing MQTT Client...")
            mqtt_config = self.config.get("mqtt", {})
            self.mqtt_client = MQTTClient(
                device_uuid=self.device_uuid,
                broker_host=mqtt_config.get("broker", "localhost"),
                broker_port=mqtt_config.get("port", 1883),
                use_tls=mqtt_config.get("use_tls", False),
                username=mqtt_config.get("username"),
                password=mqtt_config.get("password")
            )
            
            # 7. Initialize Connection Monitor
            logger.info("Initializing Connection Monitor...")
            self.connection_monitor = ConnectionMonitor(
                backend_url=self.config.get("backend_url", "http://localhost:3000"),
                check_interval=30
            )
            
            # Setup callbacks
            self._setup_callbacks()
            
            logger.info("All components initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}", exc_info=True)
            return False
    
    def _setup_callbacks(self):
        """Setup callbacks for component interactions."""
        # Connection monitor callbacks
        self.connection_monitor.set_on_offline_callback(self._on_offline)
        self.connection_monitor.set_on_sync_start_callback(self._on_sync_start)
        
        # MQTT callbacks
        self.mqtt_client.set_on_connect_callback(self._on_mqtt_connect)
        self.mqtt_client.set_on_disconnect_callback(self._on_mqtt_disconnect)
    
    def _on_offline(self):
        """Callback when connection goes offline."""
        logger.warning("Switched to OFFLINE mode - buffering data locally")
    
    def _on_sync_start(self):
        """Callback when synchronization starts."""
        logger.info("Starting data synchronization...")
        self._synchronize_buffered_data()
    
    def _on_mqtt_connect(self):
        """Callback when MQTT connects."""
        logger.info("MQTT connected")
    
    def _on_mqtt_disconnect(self):
        """Callback when MQTT disconnects."""
        logger.warning("MQTT disconnected")
    
    def start(self):
        """Start the application."""
        logger.info("Starting Turbine Monitor Application...")
        
        # Connect MQTT
        self.mqtt_client.connect()
        
        # Start connection monitor
        self.connection_monitor.start()
        
        # Start main loop
        self.running = True
        self._main_loop()
    
    def stop(self):
        """Stop the application."""
        logger.info("Stopping Turbine Monitor Application...")
        self.running = False
        
        # Stop connection monitor
        if self.connection_monitor:
            self.connection_monitor.stop()
        
        # Disconnect MQTT
        if self.mqtt_client:
            self.mqtt_client.disconnect()
        
        # Close components
        if self.adc:
            self.adc.close()
        if self.offline_buffer:
            self.offline_buffer.close()
        
        logger.info("Application stopped")
    
    def _main_loop(self):
        """
        Main data collection and processing loop.
        
        Requirements: 1.1, 2.1, 4.1, 5.1
        """
        logger.info("Entering main loop...")
        
        sample_count = 0
        
        while self.running:
            try:
                # 1. Read sensor data from all 4 channels
                samples = self.adc.read_samples(num_samples=1000)
                
                # 2. Process FFT on all channels
                fft_results = self.signal_processor.process_channels(samples)
                
                # 3. Prepare data payload
                timestamp = time.time()
                payload = self._prepare_payload(timestamp, samples, fft_results)
                
                # 4. Check connection status and publish or buffer
                if self.connection_monitor.is_online and self.mqtt_client.is_connected:
                    # Online: Publish to MQTT
                    success = self.mqtt_client.publish(payload)
                    if success:
                        sample_count += 1
                        if sample_count % 10 == 0:
                            logger.info(f"Published {sample_count} samples")
                    else:
                        # Publish failed, buffer locally
                        self._buffer_data(timestamp, samples, fft_results)
                else:
                    # Offline: Buffer locally
                    self._buffer_data(timestamp, samples, fft_results)
                
                # 5. Small delay to control sampling rate
                time.sleep(1.0)  # 1 second between readings
                
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                time.sleep(5)  # Wait before retrying
        
        logger.info("Main loop exited")
    
    def _prepare_payload(self, timestamp: float, samples: dict, fft_results: dict) -> dict:
        """
        Prepare data payload for transmission.
        
        Args:
            timestamp: Reading timestamp
            samples: Raw sensor samples
            fft_results: FFT analysis results
            
        Returns:
            Payload dictionary
        """
        channels_data = []
        
        for channel in sorted(samples.keys()):
            channel_data = {
                "channel_id": channel,
                "raw_data": {
                    "samples": samples[channel].tolist()[:100],  # Send first 100 samples
                    "sample_rate": self.adc.sample_rate,
                    "duration": len(samples[channel]) / self.adc.sample_rate
                },
                "fft_data": fft_results[channel].to_dict() if channel in fft_results else None
            }
            channels_data.append(channel_data)
        
        return {
            "device_uuid": self.device_uuid,
            "timestamp": timestamp,
            "channels": channels_data
        }
    
    def _buffer_data(self, timestamp: float, samples: dict, fft_results: dict):
        """
        Buffer data to offline storage.
        
        Args:
            timestamp: Reading timestamp
            samples: Raw sensor samples
            fft_results: FFT analysis results
        """
        try:
            raw_data = {ch: samples[ch].tolist()[:100] for ch in samples}
            fft_data = {ch: fft_results[ch].to_dict() for ch in fft_results}
            
            self.offline_buffer.insert_reading(timestamp, raw_data, fft_data)
            logger.debug("Data buffered offline")
            
        except Exception as e:
            logger.error(f"Failed to buffer data: {e}")
    
    def _synchronize_buffered_data(self):
        """Synchronize buffered data with backend."""
        try:
            # Get unsynced readings
            readings = self.offline_buffer.get_unsynced_readings(limit=100)
            
            if not readings:
                logger.info("No buffered data to synchronize")
                self.connection_monitor.mark_sync_complete()
                return
            
            logger.info(f"Synchronizing {len(readings)} buffered readings...")
            
            synced_ids = []
            for reading in readings:
                # Reconstruct payload
                payload = reading.to_dict()
                payload["device_uuid"] = self.device_uuid
                
                # Publish to MQTT
                if self.mqtt_client.publish(payload):
                    synced_ids.append(reading.id)
                else:
                    logger.warning(f"Failed to sync reading {reading.id}")
                    break
            
            # Mark as synced
            if synced_ids:
                self.offline_buffer.mark_as_synced(synced_ids)
                logger.info(f"Synchronized {len(synced_ids)} readings")
            
            # Mark sync complete
            self.connection_monitor.mark_sync_complete()
            
        except Exception as e:
            logger.error(f"Synchronization error: {e}")


def load_config() -> dict:
    """Load configuration from file or use defaults."""
    config_path = Path("/etc/turbine-monitor/config.json")
    
    if config_path.exists():
        try:
            with open(config_path) as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load config: {e}, using defaults")
    
    # Default configuration
    return {
        "backend_url": "http://localhost:3000",
        "mqtt": {
            "broker": "localhost",
            "port": 1883,
            "use_tls": False
        },
        "adc": {
            "model": "MOCK",
            "sample_rate": 1000,
            "channels": [0, 1, 2, 3]
        },
        "offline_buffer": {
            "db_path": "./buffer.db",
            "max_size_mb": 100
        }
    }


# Global app instance
app: Optional[TurbineMonitorApp] = None


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"Received signal {signum}, shutting down...")
    if app:
        app.stop()
    sys.exit(0)


def main():
    """Main application entry point."""
    global app
    
    logger.info("="*70)
    logger.info("Turbine Monitoring Edge Device")
    logger.info("Version: 1.0.0")
    logger.info("="*70)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Load configuration
        config = load_config()
        
        # Create and initialize application
        app = TurbineMonitorApp(config)
        
        if not app.initialize():
            logger.error("Application initialization failed")
            sys.exit(1)
        
        # Start application
        app.start()
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
