"""
Unit tests for UUID Manager module.

Tests the UUID generation, storage, and retrieval functionality.
"""

import pytest
import json
import uuid
from pathlib import Path
from modules.uuid_manager import UUIDManager, generate_uuid, save_uuid, load_uuid


class TestUUIDManager:
    """Test suite for UUIDManager class."""
    
    @pytest.fixture
    def temp_config_path(self, tmp_path):
        """Create a temporary configuration path for testing."""
        return str(tmp_path / "test_device.conf")
    
    @pytest.fixture
    def uuid_manager(self, temp_config_path):
        """Create a UUIDManager instance with temporary config path."""
        return UUIDManager(temp_config_path)
    
    def test_generate_uuid_returns_valid_uuid(self, uuid_manager):
        """Test that generate_uuid returns a valid UUID v4."""
        generated_uuid = uuid_manager.generate_uuid()
        
        # Should be a string
        assert isinstance(generated_uuid, str)
        
        # Should be a valid UUID
        uuid_obj = uuid.UUID(generated_uuid)
        assert uuid_obj.version == 4
    
    def test_generate_uuid_returns_unique_values(self, uuid_manager):
        """Test that generate_uuid returns different UUIDs each time."""
        uuid1 = uuid_manager.generate_uuid()
        uuid2 = uuid_manager.generate_uuid()
        
        assert uuid1 != uuid2
    
    def test_save_uuid_creates_config_file(self, uuid_manager, temp_config_path):
        """Test that save_uuid creates the configuration file."""
        test_uuid = str(uuid.uuid4())
        uuid_manager.save_uuid(test_uuid)
        
        # File should exist
        assert Path(temp_config_path).exists()
    
    def test_save_uuid_creates_directory_if_not_exists(self, tmp_path):
        """Test that save_uuid creates parent directories if they don't exist."""
        nested_path = tmp_path / "nested" / "dir" / "device.conf"
        manager = UUIDManager(str(nested_path))
        
        test_uuid = str(uuid.uuid4())
        manager.save_uuid(test_uuid)
        
        # File and directories should exist
        assert nested_path.exists()
    
    def test_save_uuid_stores_valid_json(self, uuid_manager, temp_config_path):
        """Test that save_uuid stores data in valid JSON format."""
        test_uuid = str(uuid.uuid4())
        uuid_manager.save_uuid(test_uuid)
        
        # Read and parse JSON
        with open(temp_config_path, 'r') as f:
            data = json.load(f)
        
        assert "device_uuid" in data
        assert data["device_uuid"] == test_uuid
        assert "version" in data
    
    def test_save_uuid_rejects_empty_uuid(self, uuid_manager):
        """Test that save_uuid raises ValueError for empty UUID."""
        with pytest.raises(ValueError, match="UUID cannot be empty"):
            uuid_manager.save_uuid("")
    
    def test_save_uuid_rejects_invalid_uuid(self, uuid_manager):
        """Test that save_uuid raises ValueError for invalid UUID format."""
        with pytest.raises(ValueError, match="Invalid UUID format"):
            uuid_manager.save_uuid("not-a-valid-uuid")
    
    def test_load_uuid_returns_saved_uuid(self, uuid_manager):
        """Test that load_uuid returns the UUID that was saved."""
        test_uuid = str(uuid.uuid4())
        uuid_manager.save_uuid(test_uuid)
        
        loaded_uuid = uuid_manager.load_uuid()
        
        assert loaded_uuid == test_uuid
    
    def test_load_uuid_returns_none_if_file_not_exists(self, uuid_manager):
        """Test that load_uuid returns None if configuration file doesn't exist."""
        loaded_uuid = uuid_manager.load_uuid()
        
        assert loaded_uuid is None
    
    def test_load_uuid_raises_error_for_corrupted_file(self, uuid_manager, temp_config_path):
        """Test that load_uuid raises ValueError for corrupted JSON file."""
        # Create corrupted JSON file
        Path(temp_config_path).parent.mkdir(parents=True, exist_ok=True)
        with open(temp_config_path, 'w') as f:
            f.write("{ invalid json }")
        
        with pytest.raises(ValueError, match="Corrupted configuration file"):
            uuid_manager.load_uuid()
    
    def test_load_uuid_raises_error_for_invalid_uuid_in_file(self, uuid_manager, temp_config_path):
        """Test that load_uuid raises ValueError if stored UUID is invalid."""
        # Create file with invalid UUID
        Path(temp_config_path).parent.mkdir(parents=True, exist_ok=True)
        with open(temp_config_path, 'w') as f:
            json.dump({"device_uuid": "invalid-uuid"}, f)
        
        with pytest.raises(ValueError, match="Invalid UUID in configuration file"):
            uuid_manager.load_uuid()
    
    def test_get_or_create_uuid_returns_existing_uuid(self, uuid_manager):
        """Test that get_or_create_uuid returns existing UUID if available."""
        # Save a UUID first
        test_uuid = str(uuid.uuid4())
        uuid_manager.save_uuid(test_uuid)
        
        # get_or_create_uuid should return the same UUID
        result_uuid = uuid_manager.get_or_create_uuid()
        
        assert result_uuid == test_uuid
    
    def test_get_or_create_uuid_generates_new_uuid_if_none_exists(self, uuid_manager, temp_config_path):
        """Test that get_or_create_uuid generates and saves new UUID if none exists."""
        # No UUID saved yet
        result_uuid = uuid_manager.get_or_create_uuid()
        
        # Should be a valid UUID
        uuid_obj = uuid.UUID(result_uuid)
        assert uuid_obj.version == 4
        
        # Should be saved to file
        assert Path(temp_config_path).exists()
        
        # Loading again should return the same UUID
        loaded_uuid = uuid_manager.load_uuid()
        assert loaded_uuid == result_uuid
    
    def test_get_or_create_uuid_caches_uuid(self, uuid_manager):
        """Test that get_or_create_uuid caches the UUID in memory."""
        # First call
        uuid1 = uuid_manager.get_or_create_uuid()
        
        # Second call should return cached value (same instance)
        uuid2 = uuid_manager.get_or_create_uuid()
        
        assert uuid1 == uuid2
        assert uuid1 is uuid2  # Same object reference
    
    def test_uuid_property_returns_device_uuid(self, uuid_manager):
        """Test that the uuid property returns the device UUID."""
        result_uuid = uuid_manager.uuid
        
        # Should be a valid UUID
        uuid_obj = uuid.UUID(result_uuid)
        assert uuid_obj.version == 4
    
    def test_uuid_persistence_across_instances(self, temp_config_path):
        """Test that UUID persists across different UUIDManager instances."""
        # Create first instance and generate UUID
        manager1 = UUIDManager(temp_config_path)
        uuid1 = manager1.get_or_create_uuid()
        
        # Create second instance and load UUID
        manager2 = UUIDManager(temp_config_path)
        uuid2 = manager2.get_or_create_uuid()
        
        # Should be the same UUID
        assert uuid1 == uuid2


class TestConvenienceFunctions:
    """Test suite for convenience functions."""
    
    @pytest.fixture
    def temp_config_path(self, tmp_path):
        """Create a temporary configuration path for testing."""
        return str(tmp_path / "test_device.conf")
    
    def test_generate_uuid_function(self):
        """Test the generate_uuid convenience function."""
        result = generate_uuid()
        
        # Should be a valid UUID
        uuid_obj = uuid.UUID(result)
        assert uuid_obj.version == 4
    
    def test_save_uuid_function(self, temp_config_path):
        """Test the save_uuid convenience function."""
        test_uuid = str(uuid.uuid4())
        save_uuid(test_uuid, temp_config_path)
        
        # File should exist
        assert Path(temp_config_path).exists()
        
        # Should contain the UUID
        with open(temp_config_path, 'r') as f:
            data = json.load(f)
        assert data["device_uuid"] == test_uuid
    
    def test_load_uuid_function(self, temp_config_path):
        """Test the load_uuid convenience function."""
        test_uuid = str(uuid.uuid4())
        save_uuid(test_uuid, temp_config_path)
        
        loaded_uuid = load_uuid(temp_config_path)
        
        assert loaded_uuid == test_uuid
    
    def test_load_uuid_function_returns_none_if_not_exists(self, temp_config_path):
        """Test that load_uuid function returns None if file doesn't exist."""
        result = load_uuid(temp_config_path)
        
        assert result is None
