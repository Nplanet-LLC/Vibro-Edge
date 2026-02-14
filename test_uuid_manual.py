"""
Manual test script for UUID Manager to verify functionality.
"""

import sys
import tempfile
from pathlib import Path

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent))

from modules.uuid_manager import UUIDManager

def test_uuid_manager():
    """Test UUID manager functionality."""
    print("Testing UUID Manager...")
    
    # Create temporary config path
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "device.conf"
        
        # Test 1: Generate and save UUID
        print("\n1. Testing UUID generation and save...")
        manager = UUIDManager(str(config_path))
        uuid1 = manager.get_or_create_uuid()
        print(f"   Generated UUID: {uuid1}")
        assert len(uuid1) == 36, "UUID should be 36 characters"
        print("   ✓ UUID generated successfully")
        
        # Test 2: Load existing UUID
        print("\n2. Testing UUID persistence...")
        manager2 = UUIDManager(str(config_path))
        uuid2 = manager2.get_or_create_uuid()
        print(f"   Loaded UUID: {uuid2}")
        assert uuid1 == uuid2, "UUIDs should match"
        print("   ✓ UUID persisted correctly")
        
        # Test 3: Verify file exists
        print("\n3. Testing file creation...")
        assert config_path.exists(), "Config file should exist"
        print(f"   Config file created at: {config_path}")
        print("   ✓ File created successfully")
        
        print("\n✅ All tests passed!")
        return True

if __name__ == "__main__":
    try:
        test_uuid_manager()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
