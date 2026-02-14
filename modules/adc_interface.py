"""
ADC Interface Module

This module handles communication with multi-channel ADC hardware for
reading vibration sensor data from 4 channels simultaneously.

Supports:
- ADS1256 (8-channel, 24-bit ADC via SPI)
- 4x ADS1115 (16-bit ADC via I2C)

Requirements: 1.1, 1.2, 1.5, 1.6
"""

import logging
import time
import numpy as np
from typing import Dict, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class ADCModel(Enum):
    """Supported ADC models."""
    ADS1256 = "ADS1256"  # 8-channel, 24-bit, SPI
    ADS1115 = "ADS1115"  # 4x 16-bit, I2C
    MOCK = "MOCK"        # Mock ADC for testing


class ADCInterface:
    """
    Interface for reading vibration sensor data from 4-channel ADC.
    
    This class provides a unified interface for different ADC hardware,
    supporting continuous sampling at 1000 Hz per channel.
    """
    
    def __init__(
        self,
        model: ADCModel = ADCModel.MOCK,
        sample_rate: int = 1000,
        channels: List[int] = [0, 1, 2, 3],
        calibration_offsets: Optional[Dict[int, float]] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Initialize the ADC interface.
        
        Args:
            model: ADC model to use (ADS1256, ADS1115, or MOCK)
            sample_rate: Sampling rate in Hz (default: 1000)
            channels: List of channel numbers to read (default: [0,1,2,3])
            calibration_offsets: Optional dict of calibration offsets per channel
            max_retries: Maximum number of initialization retries
            retry_delay: Delay between retries in seconds
            
        Requirements: 1.1, 1.5
        """
        self.model = model
        self.sample_rate = sample_rate
        self.channels = channels
        self.calibration_offsets = calibration_offsets or {ch: 0.0 for ch in channels}
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        self._adc = None
        self._initialized = False
        
        logger.info(f"ADC Interface initialized: model={model.value}, "
                   f"sample_rate={sample_rate}Hz, channels={channels}")
        
        # Initialize ADC hardware
        self._initialize_adc()
    
    def _initialize_adc(self) -> None:
        """
        Initialize ADC hardware with retry logic.
        
        Requirements: 1.5
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"Initializing ADC (attempt {attempt}/{self.max_retries})...")
                
                if self.model == ADCModel.MOCK:
                    self._initialize_mock_adc()
                elif self.model == ADCModel.ADS1256:
                    self._initialize_ads1256()
                elif self.model == ADCModel.ADS1115:
                    self._initialize_ads1115()
                else:
                    raise ValueError(f"Unsupported ADC model: {self.model}")
                
                self._initialized = True
                logger.info("ADC initialized successfully")
                return
                
            except Exception as e:
                logger.error(f"ADC initialization failed (attempt {attempt}): {e}")
                
                if attempt < self.max_retries:
                    logger.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    logger.error("ADC initialization failed after all retries")
                    raise RuntimeError(f"Failed to initialize ADC after {self.max_retries} attempts") from e
    
    def _initialize_mock_adc(self) -> None:
        """Initialize mock ADC for testing."""
        logger.info("Initializing MOCK ADC for testing")
        self._adc = {"type": "mock", "channels": self.channels}
    
    def _initialize_ads1256(self) -> None:
        """
        Initialize ADS1256 ADC via SPI.
        
        Note: This requires the spidev library and actual hardware.
        For development on Windows, use MOCK mode.
        """
        try:
            import spidev
            
            # Initialize SPI
            spi = spidev.SpiDev()
            spi.open(0, 0)  # Bus 0, Device 0
            spi.max_speed_hz = 1000000
            
            self._adc = {
                "type": "ADS1256",
                "spi": spi,
                "channels": self.channels
            }
            
            logger.info("ADS1256 initialized via SPI")
            
        except ImportError:
            logger.warning("spidev not available, using MOCK mode")
            self._initialize_mock_adc()
        except Exception as e:
            raise RuntimeError(f"Failed to initialize ADS1256: {e}") from e
    
    def _initialize_ads1115(self) -> None:
        """
        Initialize 4x ADS1115 ADCs via I2C.
        
        Note: This requires the Adafruit CircuitPython library and actual hardware.
        For development on Windows, use MOCK mode.
        """
        try:
            import board
            import busio
            import adafruit_ads1x15.ads1115 as ADS
            from adafruit_ads1x15.analog_in import AnalogIn
            
            # Initialize I2C
            i2c = busio.I2C(board.SCL, board.SDA)
            
            # Initialize 4 ADS1115 chips (one per channel)
            # Addresses: 0x48, 0x49, 0x4A, 0x4B
            adcs = []
            for i, addr in enumerate([0x48, 0x49, 0x4A, 0x4B]):
                if i in self.channels:
                    adc = ADS.ADS1115(i2c, address=addr)
                    adcs.append(adc)
            
            self._adc = {
                "type": "ADS1115",
                "adcs": adcs,
                "channels": self.channels
            }
            
            logger.info(f"Initialized {len(adcs)} ADS1115 ADCs via I2C")
            
        except ImportError:
            logger.warning("Adafruit CircuitPython not available, using MOCK mode")
            self._initialize_mock_adc()
        except Exception as e:
            raise RuntimeError(f"Failed to initialize ADS1115: {e}") from e
    
    def read_samples(self, num_samples: int = 1000) -> Dict[int, np.ndarray]:
        """
        Read samples from all channels simultaneously.
        
        Args:
            num_samples: Number of samples to read per channel
            
        Returns:
            Dictionary mapping channel number to numpy array of samples
            
        Requirements: 1.1, 1.2, 1.6
        """
        if not self._initialized:
            raise RuntimeError("ADC not initialized")
        
        logger.debug(f"Reading {num_samples} samples from {len(self.channels)} channels")
        
        # Read samples based on ADC type
        if self._adc["type"] == "mock":
            samples = self._read_mock_samples(num_samples)
        elif self._adc["type"] == "ADS1256":
            samples = self._read_ads1256_samples(num_samples)
        elif self._adc["type"] == "ADS1115":
            samples = self._read_ads1115_samples(num_samples)
        else:
            raise RuntimeError(f"Unknown ADC type: {self._adc['type']}")
        
        # Apply calibration offsets
        calibrated_samples = {}
        for channel, data in samples.items():
            offset = self.calibration_offsets.get(channel, 0.0)
            calibrated_samples[channel] = data - offset
        
        logger.debug(f"Read {num_samples} samples from channels {list(calibrated_samples.keys())}")
        
        return calibrated_samples
    
    def _read_mock_samples(self, num_samples: int) -> Dict[int, np.ndarray]:
        """
        Generate mock samples for testing.
        
        Generates synthetic vibration data with:
        - Base frequency: 50 Hz (typical turbine vibration)
        - Amplitude: 0.5 units
        - Noise: 0.1 units
        - Different phase for each channel
        """
        samples = {}
        
        # Time array
        t = np.linspace(0, num_samples / self.sample_rate, num_samples)
        
        for i, channel in enumerate(self.channels):
            # Generate synthetic vibration signal
            # Base frequency: 50 Hz with harmonics
            base_freq = 50.0
            phase = i * np.pi / 4  # Different phase per channel
            
            signal = (
                0.5 * np.sin(2 * np.pi * base_freq * t + phase) +
                0.2 * np.sin(2 * np.pi * base_freq * 2 * t + phase) +
                0.1 * np.sin(2 * np.pi * base_freq * 3 * t + phase) +
                0.1 * np.random.randn(num_samples)  # Noise
            )
            
            samples[channel] = signal
        
        return samples
    
    def _read_ads1256_samples(self, num_samples: int) -> Dict[int, np.ndarray]:
        """
        Read samples from ADS1256 ADC.
        
        Note: This is a placeholder implementation. Actual implementation
        would require proper SPI communication protocol for ADS1256.
        """
        logger.warning("ADS1256 reading not fully implemented, using mock data")
        return self._read_mock_samples(num_samples)
    
    def _read_ads1115_samples(self, num_samples: int) -> Dict[int, np.ndarray]:
        """
        Read samples from ADS1115 ADCs.
        
        Note: This is a placeholder implementation. Actual implementation
        would require proper I2C communication and timing.
        """
        logger.warning("ADS1115 reading not fully implemented, using mock data")
        return self._read_mock_samples(num_samples)
    
    def read_single_sample(self) -> Dict[int, float]:
        """
        Read a single sample from all channels.
        
        Returns:
            Dictionary mapping channel number to sample value
        """
        samples = self.read_samples(num_samples=1)
        return {ch: data[0] for ch, data in samples.items()}
    
    def set_calibration_offset(self, channel: int, offset: float) -> None:
        """
        Set calibration offset for a specific channel.
        
        Args:
            channel: Channel number
            offset: Calibration offset value
            
        Requirements: 1.6
        """
        if channel not in self.channels:
            raise ValueError(f"Invalid channel: {channel}")
        
        self.calibration_offsets[channel] = offset
        logger.info(f"Set calibration offset for channel {channel}: {offset}")
    
    def get_channel_info(self) -> Dict[int, Dict[str, any]]:
        """
        Get information about all channels.
        
        Returns:
            Dictionary with channel information
        """
        info = {}
        for channel in self.channels:
            info[channel] = {
                "channel_id": channel,
                "sample_rate": self.sample_rate,
                "calibration_offset": self.calibration_offsets.get(channel, 0.0),
                "status": "active" if self._initialized else "inactive"
            }
        return info
    
    def close(self) -> None:
        """Close ADC connection and cleanup resources."""
        if self._adc:
            if self._adc["type"] == "ADS1256" and "spi" in self._adc:
                try:
                    self._adc["spi"].close()
                    logger.info("SPI connection closed")
                except Exception as e:
                    logger.error(f"Error closing SPI: {e}")
            
            self._adc = None
            self._initialized = False
            logger.info("ADC interface closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    @property
    def is_initialized(self) -> bool:
        """Check if ADC is initialized."""
        return self._initialized
    
    @property
    def num_channels(self) -> int:
        """Get number of active channels."""
        return len(self.channels)
