"""
Signal Processing Module

This module performs FFT analysis on vibration sensor data from all 4 channels.
Processes time-domain signals to extract frequency-domain information.

Requirements: 2.1, 2.2, 2.3
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FFTResult:
    """
    Container for FFT analysis results for a single channel.
    
    Attributes:
        channel: Channel number
        frequencies: Array of frequency bins (Hz)
        amplitudes: Array of amplitude values
        phases: Array of phase values (radians)
        peak_frequency: Dominant frequency (Hz)
        rms_value: RMS value of the signal
        sample_rate: Sampling rate used (Hz)
    """
    channel: int
    frequencies: np.ndarray
    amplitudes: np.ndarray
    phases: np.ndarray
    peak_frequency: float
    rms_value: float
    sample_rate: int
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "channel": self.channel,
            "frequencies": self.frequencies.tolist(),
            "amplitudes": self.amplitudes.tolist(),
            "phases": self.phases.tolist(),
            "peak_frequency": float(self.peak_frequency),
            "rms_value": float(self.rms_value),
            "sample_rate": self.sample_rate
        }


class SignalProcessor:
    """
    Signal processor for multi-channel FFT analysis.
    
    Processes vibration data from 4 channels independently, applying
    windowing functions and computing frequency spectra.
    """
    
    def __init__(
        self,
        sample_rate: int = 1000,
        window_type: str = "hann",
        min_frequency: float = 0.0,
        max_frequency: Optional[float] = None
    ):
        """
        Initialize the signal processor.
        
        Args:
            sample_rate: Sampling rate in Hz
            window_type: Window function type ('hann', 'hamming', 'blackman', 'none')
            min_frequency: Minimum frequency for analysis (Hz)
            max_frequency: Maximum frequency for analysis (Hz), defaults to Nyquist
            
        Requirements: 2.1
        """
        self.sample_rate = sample_rate
        self.window_type = window_type.lower()
        self.min_frequency = min_frequency
        self.max_frequency = max_frequency or (sample_rate / 2.0)
        
        # Validate parameters
        if self.max_frequency > sample_rate / 2.0:
            logger.warning(f"Max frequency {self.max_frequency} exceeds Nyquist "
                          f"frequency {sample_rate/2.0}, clamping to Nyquist")
            self.max_frequency = sample_rate / 2.0
        
        logger.info(f"Signal Processor initialized: sample_rate={sample_rate}Hz, "
                   f"window={window_type}, freq_range=[{min_frequency}, {self.max_frequency}]Hz")
    
    def process_channels(
        self,
        channel_data: Dict[int, np.ndarray]
    ) -> Dict[int, FFTResult]:
        """
        Process FFT analysis for all channels.
        
        Args:
            channel_data: Dictionary mapping channel number to time-domain samples
            
        Returns:
            Dictionary mapping channel number to FFT results
            
        Requirements: 2.1, 2.2, 2.3
        """
        logger.debug(f"Processing {len(channel_data)} channels")
        
        results = {}
        for channel, samples in channel_data.items():
            try:
                result = self.process_single_channel(channel, samples)
                results[channel] = result
            except Exception as e:
                logger.error(f"Error processing channel {channel}: {e}")
                raise
        
        logger.debug(f"Processed {len(results)} channels successfully")
        return results
    
    def process_single_channel(
        self,
        channel: int,
        samples: np.ndarray
    ) -> FFTResult:
        """
        Process FFT analysis for a single channel.
        
        Args:
            channel: Channel number
            samples: Time-domain samples
            
        Returns:
            FFT analysis results
            
        Requirements: 2.1, 2.2, 2.3
        """
        if len(samples) == 0:
            raise ValueError(f"Channel {channel}: No samples provided")
        
        # Apply window function
        windowed_samples = self._apply_window(samples)
        
        # Compute FFT
        fft_result = np.fft.rfft(windowed_samples)
        frequencies = np.fft.rfftfreq(len(samples), 1.0 / self.sample_rate)
        
        # Compute amplitudes (magnitude spectrum)
        amplitudes = np.abs(fft_result) / len(samples)
        # Double the amplitude for all frequencies except DC and Nyquist
        amplitudes[1:-1] *= 2
        
        # Compute phases
        phases = np.angle(fft_result)
        
        # Filter to frequency range of interest
        freq_mask = (frequencies >= self.min_frequency) & (frequencies <= self.max_frequency)
        frequencies = frequencies[freq_mask]
        amplitudes = amplitudes[freq_mask]
        phases = phases[freq_mask]
        
        # Find peak frequency
        peak_idx = np.argmax(amplitudes)
        peak_frequency = frequencies[peak_idx]
        
        # Calculate RMS value
        rms_value = np.sqrt(np.mean(samples ** 2))
        
        logger.debug(f"Channel {channel}: peak_freq={peak_frequency:.2f}Hz, "
                    f"rms={rms_value:.4f}")
        
        return FFTResult(
            channel=channel,
            frequencies=frequencies,
            amplitudes=amplitudes,
            phases=phases,
            peak_frequency=peak_frequency,
            rms_value=rms_value,
            sample_rate=self.sample_rate
        )
    
    def _apply_window(self, samples: np.ndarray) -> np.ndarray:
        """
        Apply window function to samples.
        
        Args:
            samples: Time-domain samples
            
        Returns:
            Windowed samples
            
        Requirements: 2.1
        """
        n = len(samples)
        
        if self.window_type == "hann":
            window = np.hanning(n)
        elif self.window_type == "hamming":
            window = np.hamming(n)
        elif self.window_type == "blackman":
            window = np.blackman(n)
        elif self.window_type == "none":
            window = np.ones(n)
        else:
            logger.warning(f"Unknown window type '{self.window_type}', using Hann")
            window = np.hanning(n)
        
        return samples * window
    
    def compute_power_spectrum(
        self,
        channel_data: Dict[int, np.ndarray]
    ) -> Dict[int, Tuple[np.ndarray, np.ndarray]]:
        """
        Compute power spectral density for all channels.
        
        Args:
            channel_data: Dictionary mapping channel number to time-domain samples
            
        Returns:
            Dictionary mapping channel number to (frequencies, power) tuples
        """
        results = {}
        
        for channel, samples in channel_data.items():
            windowed = self._apply_window(samples)
            fft_result = np.fft.rfft(windowed)
            frequencies = np.fft.rfftfreq(len(samples), 1.0 / self.sample_rate)
            
            # Power spectral density
            power = (np.abs(fft_result) ** 2) / len(samples)
            
            # Filter to frequency range
            freq_mask = (frequencies >= self.min_frequency) & (frequencies <= self.max_frequency)
            frequencies = frequencies[freq_mask]
            power = power[freq_mask]
            
            results[channel] = (frequencies, power)
        
        return results
    
    def compute_cross_correlation(
        self,
        channel1_data: np.ndarray,
        channel2_data: np.ndarray
    ) -> Tuple[np.ndarray, float]:
        """
        Compute cross-correlation between two channels.
        
        Args:
            channel1_data: Time-domain samples from channel 1
            channel2_data: Time-domain samples from channel 2
            
        Returns:
            Tuple of (correlation values, max correlation coefficient)
        """
        if len(channel1_data) != len(channel2_data):
            raise ValueError("Channels must have same length for cross-correlation")
        
        # Normalize signals
        ch1_norm = (channel1_data - np.mean(channel1_data)) / np.std(channel1_data)
        ch2_norm = (channel2_data - np.mean(channel2_data)) / np.std(channel2_data)
        
        # Compute cross-correlation
        correlation = np.correlate(ch1_norm, ch2_norm, mode='full')
        correlation = correlation / len(channel1_data)
        
        max_corr = np.max(np.abs(correlation))
        
        return correlation, max_corr
    
    def detect_harmonics(
        self,
        fft_result: FFTResult,
        fundamental_freq: Optional[float] = None,
        num_harmonics: int = 5,
        tolerance: float = 2.0
    ) -> List[Tuple[int, float, float]]:
        """
        Detect harmonic frequencies in FFT result.
        
        Args:
            fft_result: FFT analysis result
            fundamental_freq: Fundamental frequency (Hz), uses peak if None
            num_harmonics: Number of harmonics to detect
            tolerance: Frequency tolerance for harmonic detection (Hz)
            
        Returns:
            List of (harmonic_number, frequency, amplitude) tuples
        """
        if fundamental_freq is None:
            fundamental_freq = fft_result.peak_frequency
        
        harmonics = []
        
        for n in range(1, num_harmonics + 1):
            expected_freq = n * fundamental_freq
            
            # Find peaks near expected harmonic frequency
            freq_mask = np.abs(fft_result.frequencies - expected_freq) < tolerance
            if np.any(freq_mask):
                masked_amps = fft_result.amplitudes[freq_mask]
                masked_freqs = fft_result.frequencies[freq_mask]
                
                max_idx = np.argmax(masked_amps)
                detected_freq = masked_freqs[max_idx]
                detected_amp = masked_amps[max_idx]
                
                harmonics.append((n, float(detected_freq), float(detected_amp)))
        
        return harmonics
    
    def compute_thd(self, fft_result: FFTResult, num_harmonics: int = 5) -> float:
        """
        Compute Total Harmonic Distortion (THD).
        
        Args:
            fft_result: FFT analysis result
            num_harmonics: Number of harmonics to include
            
        Returns:
            THD value (ratio, not percentage)
        """
        harmonics = self.detect_harmonics(fft_result, num_harmonics=num_harmonics)
        
        if len(harmonics) < 2:
            return 0.0
        
        # Fundamental amplitude (first harmonic)
        fundamental_amp = harmonics[0][2]
        
        # Sum of harmonic amplitudes (excluding fundamental)
        harmonic_sum = sum(h[2] ** 2 for h in harmonics[1:])
        
        # THD = sqrt(sum of harmonic powers) / fundamental amplitude
        thd = np.sqrt(harmonic_sum) / fundamental_amp if fundamental_amp > 0 else 0.0
        
        return float(thd)
    
    def get_frequency_bands(
        self,
        fft_result: FFTResult,
        bands: List[Tuple[float, float]]
    ) -> Dict[str, float]:
        """
        Get energy in specific frequency bands.
        
        Args:
            fft_result: FFT analysis result
            bands: List of (low_freq, high_freq) tuples
            
        Returns:
            Dictionary mapping band name to energy value
        """
        band_energies = {}
        
        for i, (low, high) in enumerate(bands):
            mask = (fft_result.frequencies >= low) & (fft_result.frequencies <= high)
            energy = np.sum(fft_result.amplitudes[mask] ** 2)
            band_energies[f"band_{i}_{low}-{high}Hz"] = float(energy)
        
        return band_energies


def compute_rms(samples: np.ndarray) -> float:
    """
    Compute RMS (Root Mean Square) value of a signal.
    
    Args:
        samples: Time-domain samples
        
    Returns:
        RMS value
        
    Requirements: 2.2
    """
    return float(np.sqrt(np.mean(samples ** 2)))


def find_peak_frequency(frequencies: np.ndarray, amplitudes: np.ndarray) -> float:
    """
    Find the peak (dominant) frequency in a spectrum.
    
    Args:
        frequencies: Frequency bins
        amplitudes: Amplitude values
        
    Returns:
        Peak frequency in Hz
        
    Requirements: 2.2
    """
    peak_idx = np.argmax(amplitudes)
    return float(frequencies[peak_idx])
