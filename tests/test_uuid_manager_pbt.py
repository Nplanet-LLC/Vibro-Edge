"""
Property-Based Tests for UUID Manager module.

Uses Hypothesis to test universal properties that should hold
across all valid executions.

Feature: turbine-monitoring
Property 1: UUID Persistence
"""

import pytest
import uuid
from pathlib import Path
from hypothesis import given, strategies as st, settings
from modules.uuid_manager import UUIDManager


class TestUUIDPersistenceProperty:
    """
    Property-Based Tests for UUID Persistence.
    
    **Property 1: UUID Persistence**
    **Validates: Requirements 3.2, 3.6**
    
    For any Edge_Device, if a Device_UUID is generated on first boot,
    then all subsequent boots should load the same Device_UUID from
    persistent storage.
    """
    
    @pytest.fixture
    def temp_config_path(self, tmp_path):
        """Create a temporary configuration path for testing."""
        return str(tmp_path / "device.conf")
    
    @given(st.integers(min_value=2, max_value=10))
    @settings(max_examples=100)
    def test_uuid_persistence_across_multiple_loads(self, temp_config_path, num_loads):
        """
        Property Test: UUID remains consistent across multiple load operations.
        
        **Property 1: UUID Persistence**
        **Validates: Requirements 3.2, 3.6**
        
        Given: A UUID is generated and saved
        When: The UUID is loaded multiple times (2-10 times)
        Then: All loaded UUIDs should be identical to the original
        
        This tests that the UUID persists correctly across multiple
        manager instances and load operations.
        """
        # First manager instance - generate and save UUID
        manager1 = UUIDManager(temp_config_path)
        original_uuid = manager1.get_or_create_uuid()
        
        # Validate it's a proper UUID
        uuid_obj = uuid.UUID(original_uuid)
        assert uuid_obj.version == 4
        
        # Load the UUID multiple times with new manager instances
        loaded_uuids = []
        for _ in range(num_loads):
            manager = UUIDManager(temp_config_path)
            loaded_uuid = manager.get_or_create_uuid()
            loaded_uuids.append(loaded_uuid)
        
        # Property: All loaded UUIDs must match the original
        for loaded_uuid in loaded_uuids:
            assert loaded_uuid == original_uuid, \
                f"UUID changed after reload: expected {original_uuid}, got {loaded_uuid}"
        
        # Additional check: All loaded UUIDs should be identical to each other
        assert len(set(loaded_uuids)) == 1, \
            "Multiple loads returned different UUIDs"
    
    @given(st.text(min_size=1, max_size=50, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),
        blacklist_characters='/'
    )))
    @settings(max_examples=50)
    def test_uuid_persistence_with_various_config_paths(self, tmp_path, path_suffix):
        """
        Property Test: UUID persistence works with various valid path names.
        
        **Property 1: UUID Persistence**
        **Validates: Requirements 3.2, 3.6**
        
        Given: Various valid configuration file paths
        When: A UUID is saved and then loaded
        Then: The loaded UUID should match the saved UUID
        
        This tests that UUID persistence works regardless of the
        specific path used (as long as it's valid).
        """
        # Create a valid config path with the generated suffix
        config_path = str(tmp_path / f"config_{path_suffix}.conf")
        
        # Generate and save UUID
        manager1 = UUIDManager(config_path)
        saved_uuid = manager1.get_or_create_uuid()
        
        # Load UUID with new manager instance
        manager2 = UUIDManager(config_path)
        loaded_uuid = manager2.get_or_create_uuid()
        
        # Property: Loaded UUID must match saved UUID
        assert loaded_uuid == saved_uuid, \
            f"UUID not persisted correctly at path {config_path}"
    
    def test_uuid_persistence_after_file_exists(self, temp_config_path):
        """
        Property Test: Once a UUID file exists, it should never be regenerated.
        
        **Property 1: UUID Persistence**
        **Validates: Requirements 3.2, 3.6**
        
        Given: A UUID has been generated and saved
        When: Multiple manager instances are created
        Then: No new UUID should be generated; the existing one should always be loaded
        
        This ensures that the "first boot" UUID generation only happens once.
        """
        # First boot - generate UUID
        manager1 = UUIDManager(temp_config_path)
        first_uuid = manager1.get_or_create_uuid()
        
        # Verify file exists
        assert Path(temp_config_path).exists()
        
        # Subsequent "boots" - should load existing UUID
        for i in range(10):
            manager = UUIDManager(temp_config_path)
            loaded_uuid = manager.get_or_create_uuid()
            
            # Property: Should always get the same UUID
            assert loaded_uuid == first_uuid, \
                f"UUID changed on boot {i+2}: expected {first_uuid}, got {loaded_uuid}"
    
    def test_uuid_persistence_survives_manager_recreation(self, temp_config_path):
        """
        Property Test: UUID persists even when manager objects are destroyed and recreated.
        
        **Property 1: UUID Persistence**
        **Validates: Requirements 3.2, 3.6**
        
        Given: A UUID is saved by one manager instance
        When: That manager is destroyed and a new one is created
        Then: The new manager should load the same UUID
        
        This simulates the real-world scenario of device reboots.
        """
        # Create manager, generate UUID, then destroy it
        original_uuid = None
        manager1 = UUIDManager(temp_config_path)
        original_uuid = manager1.get_or_create_uuid()
        del manager1  # Explicitly destroy the manager
        
        # Create new manager - simulates device reboot
        manager2 = UUIDManager(temp_config_path)
        reboot_uuid = manager2.get_or_create_uuid()
        
        # Property: UUID should survive manager destruction
        assert reboot_uuid == original_uuid, \
            "UUID did not persist after manager recreation"
    
    @given(st.lists(st.integers(min_value=1, max_value=5), min_size=1, max_size=10))
    @settings(max_examples=50)
    def test_uuid_persistence_with_interleaved_operations(self, temp_config_path, operation_sequence):
        """
        Property Test: UUID remains consistent with interleaved save/load operations.
        
        **Property 1: UUID Persistence**
        **Validates: Requirements 3.2, 3.6**
        
        Given: A sequence of manager creation operations
        When: Multiple managers are created and destroyed in various patterns
        Then: All managers should see the same UUID
        
        This tests that UUID persistence is robust under various
        operation patterns.
        """
        # First manager - establish the UUID
        manager = UUIDManager(temp_config_path)
        original_uuid = manager.get_or_create_uuid()
        
        # Perform interleaved operations based on the sequence
        all_uuids = [original_uuid]
        for _ in operation_sequence:
            # Create new manager and get UUID
            new_manager = UUIDManager(temp_config_path)
            new_uuid = new_manager.get_or_create_uuid()
            all_uuids.append(new_uuid)
        
        # Property: All UUIDs should be identical
        assert len(set(all_uuids)) == 1, \
            f"UUID changed during operations: {set(all_uuids)}"
        assert all(u == original_uuid for u in all_uuids), \
            "Some UUIDs don't match the original"
