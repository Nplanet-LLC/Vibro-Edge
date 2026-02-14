"""
UUID Management Module

This module handles device UUID generation and persistence for the edge device.
It ensures each device has a unique identifier that persists across reboots.

Requirements: 3.1, 3.2, 3.6
"""

import uuid
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Default configuration path
DEFAULT_CONFIG_PATH = "/etc/turbine-monitor/device.conf"


class UUIDManager:
    """
    Manages device UUID generation, storage, and retrieval.
    
    The UUID is generated once on first boot and stored persistently
    in a JSON configuration file. Subsequent boots load the existing UUID.
    """
    
    def __init__(self, config_path: str = DEFAULT_CONFIG_PATH):
        """
        Initialize the UUID Manager.
        
        Args:
            config_path: Path to the device configuration file
        """
        self.config_path = Path(config_path)
        self._uuid: Optional[str] = None
        logger.info(f"UUID Manager initialized with config path: {self.config_path}")
    
    def generate_uuid(self) -> str:
        """
        Generate a new UUID v4.
        
        Returns:
            A new UUID v4 as a string
            
        Requirements: 3.1
        """
        new_uuid = str(uuid.uuid4())
        logger.info(f"Generated new UUID: {new_uuid}")
        return new_uuid
    
    def save_uuid(self, device_uuid: str) -> None:
        """
        Save the UUID to persistent storage.
        
        Creates the configuration directory if it doesn't exist and
        stores the UUID in JSON format.
        
        Args:
            device_uuid: The UUID to save
            
        Raises:
            IOError: If unable to write to the configuration file
            ValueError: If the UUID is invalid
            
        Requirements: 3.2
        """
        if not device_uuid:
            raise ValueError("UUID cannot be empty")
        
        # Validate UUID format
        try:
            uuid.UUID(device_uuid)
        except ValueError as e:
            raise ValueError(f"Invalid UUID format: {device_uuid}") from e
        
        # Create directory if it doesn't exist
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Prepare configuration data
        config_data = {
            "device_uuid": device_uuid,
            "version": "1.0"
        }
        
        # Write to file
        try:
            with open(self.config_path, 'w') as f:
                json.dump(config_data, f, indent=2)
            logger.info(f"UUID saved to {self.config_path}")
        except IOError as e:
            logger.error(f"Failed to save UUID to {self.config_path}: {e}")
            raise
    
    def load_uuid(self) -> Optional[str]:
        """
        Load the UUID from persistent storage.
        
        Returns:
            The stored UUID as a string, or None if no UUID is stored
            
        Raises:
            IOError: If unable to read the configuration file
            ValueError: If the configuration file is corrupted
            
        Requirements: 3.6
        """
        if not self.config_path.exists():
            logger.info(f"Configuration file not found at {self.config_path}")
            return None
        
        try:
            with open(self.config_path, 'r') as f:
                config_data = json.load(f)
            
            device_uuid = config_data.get("device_uuid")
            
            if not device_uuid:
                logger.warning("Configuration file exists but contains no UUID")
                return None
            
            # Validate UUID format
            try:
                uuid.UUID(device_uuid)
            except ValueError as e:
                raise ValueError(f"Invalid UUID in configuration file: {device_uuid}") from e
            
            logger.info(f"UUID loaded from {self.config_path}: {device_uuid}")
            return device_uuid
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse configuration file: {e}")
            raise ValueError(f"Corrupted configuration file at {self.config_path}") from e
        except IOError as e:
            logger.error(f"Failed to read configuration file: {e}")
            raise
    
    def get_or_create_uuid(self) -> str:
        """
        Get the existing UUID or create a new one if it doesn't exist.
        
        This is the main method to use for obtaining the device UUID.
        It handles the logic of loading an existing UUID or generating
        and saving a new one on first boot.
        
        Returns:
            The device UUID as a string
            
        Requirements: 3.1, 3.2, 3.6
        """
        # Return cached UUID if available
        if self._uuid:
            return self._uuid
        
        # Try to load existing UUID
        self._uuid = self.load_uuid()
        
        # Generate and save new UUID if none exists
        if not self._uuid:
            logger.info("No existing UUID found, generating new one")
            self._uuid = self.generate_uuid()
            self.save_uuid(self._uuid)
        
        return self._uuid
    
    @property
    def uuid(self) -> str:
        """
        Get the device UUID (property accessor).
        
        Returns:
            The device UUID as a string
        """
        return self.get_or_create_uuid()


# Convenience functions for simple usage
def generate_uuid() -> str:
    """
    Generate a new UUID v4.
    
    Returns:
        A new UUID v4 as a string
    """
    manager = UUIDManager()
    return manager.generate_uuid()


def save_uuid(device_uuid: str, config_path: str = DEFAULT_CONFIG_PATH) -> None:
    """
    Save a UUID to persistent storage.
    
    Args:
        device_uuid: The UUID to save
        config_path: Path to the configuration file
    """
    manager = UUIDManager(config_path)
    manager.save_uuid(device_uuid)


def load_uuid(config_path: str = DEFAULT_CONFIG_PATH) -> Optional[str]:
    """
    Load a UUID from persistent storage.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        The stored UUID or None if not found
    """
    manager = UUIDManager(config_path)
    return manager.load_uuid()
