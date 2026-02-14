"""
Manual Property-Based Test Runner for UUID Persistence.

This script manually runs property-based tests without requiring pytest.

Feature: turbine-monitoring
Property 1: UUID Persistence
"""

import sys
import tempfile
from pathlib import Path

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent))

from modules.uuid_manager import UUIDManager
import uuid


def test_uuid_persistence_across_multiple_loads():
    """
    Property Test: UUID remains consistent across multiple load operations.
    
    **Property 1: UUID Persistence**
    **Validates: Requirements 3.2, 3.6**
    """
    print("\n" + "="*70)
    print("Property Test 1: UUID Persistence Across Multiple Loads")
    print("="*70)
    
    passed = 0
    failed = 0
    
    # Run 100 test cases with different numbers of loads
    for test_num in range(1, 101):
        num_loads = (test_num % 9) + 2  # 2-10 loads
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "device.conf"
            
            try:
                # First manager instance - generate and save UUID
                manager1 = UUIDManager(str(config_path))
                original_uuid = manager1.get_or_create_uuid()
                
                # Validate it's a proper UUID
                uuid_obj = uuid.UUID(original_uuid)
                assert uuid_obj.version == 4
                
                # Load the UUID multiple times with new manager instances
                loaded_uuids = []
                for _ in range(num_loads):
                    manager = UUIDManager(str(config_path))
                    loaded_uuid = manager.get_or_create_uuid()
                    loaded_uuids.append(loaded_uuid)
                
                # Property: All loaded UUIDs must match the original
                for loaded_uuid in loaded_uuids:
                    assert loaded_uuid == original_uuid, \
                        f"UUID changed after reload: expected {original_uuid}, got {loaded_uuid}"
                
                # Additional check: All loaded UUIDs should be identical
                assert len(set(loaded_uuids)) == 1, \
                    "Multiple loads returned different UUIDs"
                
                passed += 1
                if test_num % 20 == 0:
                    print(f"  Progress: {test_num}/100 tests passed")
                    
            except AssertionError as e:
                failed += 1
                print(f"  ❌ Test {test_num} FAILED: {e}")
                return False
            except Exception as e:
                failed += 1
                print(f"  ❌ Test {test_num} ERROR: {e}")
                return False
    
    print(f"\n  ✅ All 100 test cases passed!")
    print(f"  Total: {passed} passed, {failed} failed")
    return True


def test_uuid_persistence_after_file_exists():
    """
    Property Test: Once a UUID file exists, it should never be regenerated.
    
    **Property 1: UUID Persistence**
    **Validates: Requirements 3.2, 3.6**
    """
    print("\n" + "="*70)
    print("Property Test 2: UUID Never Regenerated After First Boot")
    print("="*70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "device.conf"
        
        try:
            # First boot - generate UUID
            manager1 = UUIDManager(str(config_path))
            first_uuid = manager1.get_or_create_uuid()
            print(f"  First boot UUID: {first_uuid}")
            
            # Verify file exists
            assert config_path.exists(), "Config file should exist"
            
            # Subsequent "boots" - should load existing UUID
            for i in range(10):
                manager = UUIDManager(str(config_path))
                loaded_uuid = manager.get_or_create_uuid()
                
                # Property: Should always get the same UUID
                assert loaded_uuid == first_uuid, \
                    f"UUID changed on boot {i+2}: expected {first_uuid}, got {loaded_uuid}"
            
            print(f"  ✅ UUID remained consistent across 10 simulated reboots")
            return True
            
        except AssertionError as e:
            print(f"  ❌ Test FAILED: {e}")
            return False
        except Exception as e:
            print(f"  ❌ Test ERROR: {e}")
            return False


def test_uuid_persistence_survives_manager_recreation():
    """
    Property Test: UUID persists when manager objects are destroyed and recreated.
    
    **Property 1: UUID Persistence**
    **Validates: Requirements 3.2, 3.6**
    """
    print("\n" + "="*70)
    print("Property Test 3: UUID Survives Manager Recreation")
    print("="*70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "device.conf"
        
        try:
            # Create manager, generate UUID, then destroy it
            original_uuid = None
            manager1 = UUIDManager(str(config_path))
            original_uuid = manager1.get_or_create_uuid()
            print(f"  Original UUID: {original_uuid}")
            del manager1  # Explicitly destroy the manager
            
            # Create new manager - simulates device reboot
            manager2 = UUIDManager(str(config_path))
            reboot_uuid = manager2.get_or_create_uuid()
            print(f"  After reboot UUID: {reboot_uuid}")
            
            # Property: UUID should survive manager destruction
            assert reboot_uuid == original_uuid, \
                "UUID did not persist after manager recreation"
            
            print(f"  ✅ UUID persisted after manager destruction")
            return True
            
        except AssertionError as e:
            print(f"  ❌ Test FAILED: {e}")
            return False
        except Exception as e:
            print(f"  ❌ Test ERROR: {e}")
            return False


def test_uuid_persistence_with_interleaved_operations():
    """
    Property Test: UUID remains consistent with interleaved operations.
    
    **Property 1: UUID Persistence**
    **Validates: Requirements 3.2, 3.6**
    """
    print("\n" + "="*70)
    print("Property Test 4: UUID Consistency With Interleaved Operations")
    print("="*70)
    
    passed = 0
    failed = 0
    
    # Run 50 test cases with different operation sequences
    for test_num in range(1, 51):
        # Generate a random-ish sequence of operations
        operation_sequence = [(test_num * i) % 5 + 1 for i in range((test_num % 10) + 1)]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "device.conf"
            
            try:
                # First manager - establish the UUID
                manager = UUIDManager(str(config_path))
                original_uuid = manager.get_or_create_uuid()
                
                # Perform interleaved operations
                all_uuids = [original_uuid]
                for _ in operation_sequence:
                    # Create new manager and get UUID
                    new_manager = UUIDManager(str(config_path))
                    new_uuid = new_manager.get_or_create_uuid()
                    all_uuids.append(new_uuid)
                
                # Property: All UUIDs should be identical
                assert len(set(all_uuids)) == 1, \
                    f"UUID changed during operations: {set(all_uuids)}"
                assert all(u == original_uuid for u in all_uuids), \
                    "Some UUIDs don't match the original"
                
                passed += 1
                if test_num % 10 == 0:
                    print(f"  Progress: {test_num}/50 tests passed")
                    
            except AssertionError as e:
                failed += 1
                print(f"  ❌ Test {test_num} FAILED: {e}")
                return False
            except Exception as e:
                failed += 1
                print(f"  ❌ Test {test_num} ERROR: {e}")
                return False
    
    print(f"\n  ✅ All 50 test cases passed!")
    print(f"  Total: {passed} passed, {failed} failed")
    return True


def main():
    """Run all property-based tests."""
    print("\n" + "="*70)
    print("PROPERTY-BASED TESTS FOR UUID PERSISTENCE")
    print("Feature: turbine-monitoring")
    print("Property 1: UUID Persistence")
    print("Validates: Requirements 3.2, 3.6")
    print("="*70)
    
    all_passed = True
    
    # Run all property tests
    all_passed &= test_uuid_persistence_across_multiple_loads()
    all_passed &= test_uuid_persistence_after_file_exists()
    all_passed &= test_uuid_persistence_survives_manager_recreation()
    all_passed &= test_uuid_persistence_with_interleaved_operations()
    
    print("\n" + "="*70)
    if all_passed:
        print("✅ ALL PROPERTY-BASED TESTS PASSED")
        print("="*70)
        return 0
    else:
        print("❌ SOME PROPERTY-BASED TESTS FAILED")
        print("="*70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
