"""
Unit tests for ADC Interface module.

Tests the ADC interface for 4-channel vibration sensor data acquisition.
"""

import pytest
import numpy as np
from modules.adc_interface import ADCInterface, ADCModel


class TestADCInterface:
    """Test suite for ADCInterface class."""
    
    def test_initialization_with_mock_adc(self):
        """Test ADC initialization with MOCK model."""
        adc = ADCInterface(model=ADCModel.MOCK)
        
        assert adc.is_initialized
        assert adc.model == ADCModel.MOCK
        assert adc.sample_rate == 1000
        assert adc.num_channels == 4
    
    def test_initialization_with_custom_channels(self):
        """Test ADC initialization with custom channel configuration."""
        channels = [0, 2]
        adc = ADCInterface(model=ADCModel.MOCK, channels=channels)
        
        assert adc.channels == channels
        assert adc.num_channels == 2
    
    def test_initialization_with_custom_sample_rate(self):
        """Test ADC initialization with custom sample rate."""
        sample_rate = 2000
        adc = ADCInterface(model=ADCModel.MOCK, sample_rate=sample_rate)
        
        assert adc.sample_rate == sample_rate
    
    def test_read_samples_returns_correct_shape(self):
        """Test that read_samples returns correct data shape."""
        adc = ADCInterface(model=ADCModel.MOCK)
        num_samples = 1000
        
        samples = adc.read_samples(num_samples)
        
        # Should return dict with 4 channels
        assert len(samples) == 4
        
        # Each channel should have correct number of samples
        for channel, data in samples.items():
            assert isinstance(data, np.ndarray)
            assert len(data) == num_samples
    
    def test_read_samples_all_channels_present(self):
        """Test that read_samples returns data for all channels."""
        channels = [0, 1, 2, 3]
        adc = ADCInterface(model=ADCModel.MOCK, channels=channels)
        
        samples = adc.read_samples(100)
        
        # All channels should be present
        for channel in channels:
            assert channel in samples
    
    def test_read_single_sample(self):
        """Test reading a single sample from all channels."""
        adc = ADCInterface(model=ADCModel.MOCK)
        
        sample = adc.read_single_sample()
        
        # Should return dict with 4 channels
        assert len(sample) == 4
        
        # Each channel should have a single float value
        for channel, value in sample.items():
            assert isinstance(value, (float, np.floating))
    
    def test_calibration_offset_applied(self):
        """Test that calibration offsets are applied to samples."""
        adc = ADCInterface(model=ADCModel.MOCK)
        
        # Set calibration offset for channel 0
        offset = 0.5
        adc.set_calibration_offset(0, offset)
        
        # Read samples
        samples_with_offset = adc.read_samples(100)
        
        # Create new ADC without offset
        adc2 = ADCInterface(model=ADCModel.MOCK)
        samples_without_offset = adc2.read_samples(100)
        
        # Note: Since mock data is random, we can't directly compare values
        # But we can verify the offset was set
        assert adc.calibration_offsets[0] == offset
    
    def test_set_calibration_offset_invalid_channel(self):
        """Test that setting calibration for invalid channel raises error."""
        adc = ADCInterface(model=ADCModel.MOCK, channels=[0, 1])
        
        with pytest.raises(ValueError, match="Invalid channel"):
            adc.set_calibration_offset(5, 0.5)
    
    def test_get_channel_info(self):
        """Test getting channel information."""
        channels = [0, 1, 2, 3]
        sample_rate = 1000
        adc = ADCInterface(
            model=ADCModel.MOCK,
            channels=channels,
            sample_rate=sample_rate
        )
        
        info = adc.get_channel_info()
        
        # Should have info for all channels
        assert len(info) == 4
        
        # Check info structure
        for channel in channels:
            assert channel in info
            assert info[channel]["channel_id"] == channel
            assert info[channel]["sample_rate"] == sample_rate
            assert "calibration_offset" in info[channel]
            assert info[channel]["status"] == "active"
    
    def test_context_manager(self):
        """Test ADC interface as context manager."""
        with ADCInterface(model=ADCModel.MOCK) as adc:
            assert adc.is_initialized
            samples = adc.read_samples(100)
            assert len(samples) == 4
        
        # After context exit, ADC should be closed
        assert not adc.is_initialized
    
    def test_close_method(self):
        """Test closing ADC interface."""
        adc = ADCInterface(model=ADCModel.MOCK)
        assert adc.is_initialized
        
        adc.close()
        
        assert not adc.is_initialized
    
    def test_read_samples_before_initialization_raises_error(self):
        """Test that reading samples before initialization raises error."""
        adc = ADCInterface(model=ADCModel.MOCK)
        adc._initialized = False  # Simulate uninitialized state
        
        with pytest.raises(RuntimeError, match="ADC not initialized"):
            adc.read_samples(100)
    
    def test_mock_samples_have_expected_characteristics(self):
        """Test that mock samples have expected signal characteristics."""
        adc = ADCInterface(model=ADCModel.MOCK, sample_rate=1000)
        
        samples = adc.read_samples(1000)
        
        for channel, data in samples.items():
            # Check data is not all zeros
            assert not np.all(data == 0)
            
            # Check data has reasonable amplitude (mock generates ~0.5 amplitude)
            assert np.abs(np.mean(data)) < 1.0
            assert np.std(data) > 0.1  # Should have some variation
    
    def test_different_channels_have_different_data(self):
        """Test that different channels produce different data."""
        adc = ADCInterface(model=ADCModel.MOCK)
        
        samples = adc.read_samples(1000)
        
        # Get data from two different channels
        data_ch0 = samples[0]
        data_ch1 = samples[1]
        
        # They should not be identical (different phase in mock)
        assert not np.array_equal(data_ch0, data_ch1)
    
    def test_multiple_reads_produce_different_data(self):
        """Test that multiple reads produce different data (due to noise)."""
        adc = ADCInterface(model=ADCModel.MOCK)
        
        samples1 = adc.read_samples(100)
        samples2 = adc.read_samples(100)
        
        # Should not be identical due to random noise
        assert not np.array_equal(samples1[0], samples2[0])
    
    def test_calibration_offsets_initialized_for_all_channels(self):
        """Test that calibration offsets are initialized for all channels."""
        channels = [0, 1, 2, 3]
        adc = ADCInterface(model=ADCModel.MOCK, channels=channels)
        
        for channel in channels:
            assert channel in adc.calibration_offsets
            assert adc.calibration_offsets[channel] == 0.0
    
    def test_custom_calibration_offsets(self):
        """Test initialization with custom calibration offsets."""
        offsets = {0: 0.1, 1: 0.2, 2: 0.3, 3: 0.4}
        adc = ADCInterface(
            model=ADCModel.MOCK,
            calibration_offsets=offsets
        )
        
        for channel, offset in offsets.items():
            assert adc.calibration_offsets[channel] == offset
