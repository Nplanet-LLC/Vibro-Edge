"""
Manual test script for ADC Interface to verify functionality.
"""

import sys
from pathlib import Path
import numpy as np

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent))

from modules.adc_interface import ADCInterface, ADCModel


def test_adc_interface():
    """Test ADC interface functionality."""
    print("Testing ADC Interface...")
    
    # Test 1: Initialization
    print("\n1. Testing ADC initialization...")
    adc = ADCInterface(model=ADCModel.MOCK, sample_rate=1000)
    print(f"   ADC Model: {adc.model.value}")
    print(f"   Sample Rate: {adc.sample_rate} Hz")
    print(f"   Channels: {adc.channels}")
    print(f"   Initialized: {adc.is_initialized}")
    assert adc.is_initialized, "ADC should be initialized"
    print("   ✓ ADC initialized successfully")
    
    # Test 2: Read samples
    print("\n2. Testing sample reading...")
    num_samples = 1000
    samples = adc.read_samples(num_samples)
    print(f"   Requested samples: {num_samples}")
    print(f"   Channels read: {list(samples.keys())}")
    for channel, data in samples.items():
        print(f"   Channel {channel}: {len(data)} samples, "
              f"mean={np.mean(data):.3f}, std={np.std(data):.3f}")
    assert len(samples) == 4, "Should read 4 channels"
    assert all(len(data) == num_samples for data in samples.values()), \
        "All channels should have correct number of samples"
    print("   ✓ Samples read successfully")
    
    # Test 3: Single sample
    print("\n3. Testing single sample reading...")
    single = adc.read_single_sample()
    print(f"   Single sample: {single}")
    assert len(single) == 4, "Should read 4 channels"
    print("   ✓ Single sample read successfully")
    
    # Test 4: Calibration
    print("\n4. Testing calibration offsets...")
    adc.set_calibration_offset(0, 0.5)
    print(f"   Set offset for channel 0: 0.5")
    print(f"   Calibration offsets: {adc.calibration_offsets}")
    assert adc.calibration_offsets[0] == 0.5
    print("   ✓ Calibration offset set successfully")
    
    # Test 5: Channel info
    print("\n5. Testing channel information...")
    info = adc.get_channel_info()
    for channel, ch_info in info.items():
        print(f"   Channel {channel}: {ch_info}")
    assert len(info) == 4, "Should have info for 4 channels"
    print("   ✓ Channel info retrieved successfully")
    
    # Test 6: Context manager
    print("\n6. Testing context manager...")
    with ADCInterface(model=ADCModel.MOCK) as adc2:
        samples2 = adc2.read_samples(100)
        print(f"   Read {len(samples2[0])} samples in context")
    print(f"   ADC closed: {not adc2.is_initialized}")
    assert not adc2.is_initialized, "ADC should be closed after context"
    print("   ✓ Context manager works correctly")
    
    # Test 7: Close
    print("\n7. Testing close method...")
    adc.close()
    print(f"   ADC closed: {not adc.is_initialized}")
    assert not adc.is_initialized, "ADC should be closed"
    print("   ✓ ADC closed successfully")
    
    print("\n✅ All tests passed!")
    return True


if __name__ == "__main__":
    try:
        test_adc_interface()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
