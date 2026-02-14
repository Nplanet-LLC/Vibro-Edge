"""
Device Registration Module

This module handles device registration with the backend server,
including sending registration requests and storing authentication tokens.

Requirements: 3.3, 3.4, 3.5
"""

import logging
import json
import time
import socket
from pathlib import Path
from typing import Dict, Optional

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

logger = logging.getLogger(__name__)

# Default token storage path
DEFAULT_TOKEN_PATH = "/etc/turbine-monitor/auth_token.json"


class DeviceRegistration:
    """
    Handles device registration with the backend server.
    
    Sends registration requests with device information and stores
    the received authentication token for future API calls.
    """
    
    def __init__(
        self,
        backend_url: str = "http://localhost:3000",
        registration_endpoint: str = "/api/devices/register",
        token_path: str = DEFAULT_TOKEN_PATH,
        max_retries: int = 5,
        retry_delay: int = 5
    ):
        """
        Initialize device registration.
        
        Args:
            backend_url: Backend server URL
            registration_endpoint: Registration API endpoint
            token_path: Path to store authentication token
            max_retries: Maximum number of registration retries
            retry_delay: Delay between retries in seconds
            
        Requirements: 3.3, 3.5
        """
        self.backend_url = backend_url.rstrip('/')
        self.registration_endpoint = registration_endpoint
        self.token_path = Path(token_path)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        self._token: Optional[str] = None
        
        logger.info(f"Device Registration initialized: backend={backend_url}, "
                   f"token_path={token_path}")
    
    def register(
        self,
        device_uuid: str,
        hostname: Optional[str] = None,
        ip_address: Optional[str] = None,
        hardware_info: Optional[Dict] = None
    ) -> bool:
        """
        Register device with backend server.
        
        Args:
            device_uuid: Unique device identifier
            hostname: Device hostname (auto-detected if None)
            ip_address: Device IP address (auto-detected if None)
            hardware_info: Optional hardware information
            
        Returns:
            True if registration successful
            
        Requirements: 3.3, 3.4, 3.5
        """
        # Auto-detect hostname and IP if not provided
        if hostname is None:
            hostname = self._get_hostname()
        
        if ip_address is None:
            ip_address = self._get_ip_address()
        
        # Prepare registration payload
        payload = {
            "uuid": device_uuid,
            "hostname": hostname,
            "ip_address": ip_address,
            "timestamp": time.time(),
            "hardware_info": hardware_info or self._get_hardware_info()
        }
        
        logger.info(f"Registering device: uuid={device_uuid}, hostname={hostname}")
        
        # Attempt registration with retries
        for attempt in range(1, self.max_retries + 1):
            try:
                success = self._send_registration_request(payload)
                
                if success:
                    logger.info("Device registered successfully")
                    return True
                
                if attempt < self.max_retries:
                    logger.warning(f"Registration failed (attempt {attempt}/{self.max_retries}), "
                                 f"retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                    
            except Exception as e:
                logger.error(f"Registration error (attempt {attempt}/{self.max_retries}): {e}")
                
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)
        
        logger.error("Device registration failed after all retries")
        return False
    
    def _send_registration_request(self, payload: Dict) -> bool:
        """
        Send registration request to backend.
        
        Args:
            payload: Registration payload
            
        Returns:
            True if registration successful
            
        Requirements: 3.3, 3.4
        """
        if not REQUESTS_AVAILABLE:
            logger.warning("Requests library not available, simulating registration")
            self._token = "mock_token_12345"
            self._save_token(self._token)
            return True
        
        try:
            url = f"{self.backend_url}{self.registration_endpoint}"
            
            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract and store auth token
                if "token" in data:
                    self._token = data["token"]
                    self._save_token(self._token)
                    logger.info("Authentication token received and stored")
                    return True
                else:
                    logger.warning("Registration response missing token")
                    return False
            
            elif response.status_code == 409:
                # Device already registered
                logger.info("Device already registered")
                return True
            
            else:
                logger.error(f"Registration failed: HTTP {response.status_code}")
                logger.debug(f"Response: {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            logger.error("Registration request timed out")
            return False
        except requests.exceptions.ConnectionError:
            logger.error("Registration request connection error")
            return False
        except Exception as e:
            logger.error(f"Registration request error: {e}")
            return False
    
    def _save_token(self, token: str) -> None:
        """
        Save authentication token to file.
        
        Args:
            token: Authentication token
            
        Requirements: 3.5
        """
        try:
            # Create directory if it doesn't exist
            self.token_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save token as JSON
            token_data = {
                "token": token,
                "created_at": time.time()
            }
            
            with open(self.token_path, 'w') as f:
                json.dump(token_data, f, indent=2)
            
            logger.info(f"Token saved to {self.token_path}")
            
        except Exception as e:
            logger.error(f"Failed to save token: {e}")
            raise
    
    def load_token(self) -> Optional[str]:
        """
        Load authentication token from file.
        
        Returns:
            Authentication token or None if not found
            
        Requirements: 3.5
        """
        try:
            if not self.token_path.exists():
                logger.debug(f"Token file not found: {self.token_path}")
                return None
            
            with open(self.token_path, 'r') as f:
                token_data = json.load(f)
            
            self._token = token_data.get("token")
            
            if self._token:
                logger.info("Token loaded from file")
            else:
                logger.warning("Token file exists but contains no token")
            
            return self._token
            
        except Exception as e:
            logger.error(f"Failed to load token: {e}")
            return None
    
    def _get_hostname(self) -> str:
        """Get device hostname."""
        try:
            return socket.gethostname()
        except Exception as e:
            logger.warning(f"Failed to get hostname: {e}")
            return "unknown"
    
    def _get_ip_address(self) -> str:
        """Get device IP address."""
        try:
            # Get IP by connecting to external host (doesn't actually send data)
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception as e:
            logger.warning(f"Failed to get IP address: {e}")
            return "0.0.0.0"
    
    def _get_hardware_info(self) -> Dict:
        """
        Get hardware information.
        
        Returns:
            Dictionary with hardware information
        """
        import platform
        
        try:
            info = {
                "system": platform.system(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "python_version": platform.python_version()
            }
            
            # Try to get Raspberry Pi specific info
            try:
                with open("/proc/cpuinfo", "r") as f:
                    cpuinfo = f.read()
                    if "Raspberry Pi" in cpuinfo:
                        info["model"] = "Raspberry Pi"
                        # Extract model details
                        for line in cpuinfo.split("\n"):
                            if "Model" in line:
                                info["model_details"] = line.split(":")[1].strip()
                                break
            except:
                pass
            
            return info
            
        except Exception as e:
            logger.warning(f"Failed to get hardware info: {e}")
            return {"error": str(e)}
    
    @property
    def token(self) -> Optional[str]:
        """Get authentication token."""
        if self._token is None:
            self._token = self.load_token()
        return self._token
    
    @property
    def is_registered(self) -> bool:
        """Check if device is registered (has token)."""
        return self.token is not None
    
    def get_auth_header(self) -> Dict[str, str]:
        """
        Get authorization header for API requests.
        
        Returns:
            Dictionary with Authorization header
        """
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}
    
    def clear_token(self) -> None:
        """Clear stored token (for testing)."""
        self._token = None
        if self.token_path.exists():
            self.token_path.unlink()
            logger.info("Token cleared")
