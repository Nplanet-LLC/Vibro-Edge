"""
MQTT Client Module

This module handles MQTT communication with the backend server,
including connection management, message publishing, and retry logic.

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
"""

import logging
import time
import json
import ssl
from typing import Dict, Optional, Callable
from enum import Enum

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("paho-mqtt not available, MQTT client will use mock mode")

logger = logging.getLogger(__name__)


class ConnectionStatus(Enum):
    """MQTT connection status."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class MQTTClient:
    """
    MQTT client for publishing sensor data to the backend.
    
    Handles connection management, automatic reconnection with exponential
    backoff, and message publishing with QoS 1.
    """
    
    def __init__(
        self,
        device_uuid: str,
        broker_host: str = "localhost",
        broker_port: int = 1883,
        use_tls: bool = False,
        username: Optional[str] = None,
        password: Optional[str] = None,
        ca_cert_path: Optional[str] = None,
        max_retry_delay: int = 60,
        qos: int = 1
    ):
        """
        Initialize MQTT client.
        
        Args:
            device_uuid: Unique device identifier
            broker_host: MQTT broker hostname
            broker_port: MQTT broker port
            use_tls: Whether to use TLS encryption
            username: MQTT username (optional)
            password: MQTT password (optional)
            ca_cert_path: Path to CA certificate for TLS (optional)
            max_retry_delay: Maximum retry delay in seconds
            qos: Quality of Service level (0, 1, or 2)
            
        Requirements: 5.1, 5.2
        """
        if not MQTT_AVAILABLE:
            logger.warning("MQTT not available, using mock mode")
        
        self.device_uuid = device_uuid
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.use_tls = use_tls
        self.username = username
        self.password = password
        self.ca_cert_path = ca_cert_path
        self.max_retry_delay = max_retry_delay
        self.qos = qos
        
        # Connection state
        self._status = ConnectionStatus.DISCONNECTED
        self._retry_count = 0
        self._retry_delay = 1
        
        # Callbacks
        self._on_connect_callback: Optional[Callable] = None
        self._on_disconnect_callback: Optional[Callable] = None
        self._on_publish_callback: Optional[Callable] = None
        
        # MQTT topic
        self.topic = f"turbines/{device_uuid}/vibration"
        
        # Initialize client
        if MQTT_AVAILABLE:
            self._client = mqtt.Client(client_id=device_uuid)
            self._setup_callbacks()
            self._setup_authentication()
            self._setup_tls()
        else:
            self._client = None
        
        logger.info(f"MQTT Client initialized: broker={broker_host}:{broker_port}, "
                   f"topic={self.topic}, tls={use_tls}")
    
    def _setup_callbacks(self) -> None:
        """Setup MQTT client callbacks."""
        if not self._client:
            return
        
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_publish = self._on_publish
    
    def _setup_authentication(self) -> None:
        """Setup MQTT authentication."""
        if not self._client:
            return
        
        if self.username and self.password:
            self._client.username_pw_set(self.username, self.password)
            logger.info("MQTT authentication configured")
    
    def _setup_tls(self) -> None:
        """
        Setup TLS encryption.
        
        Requirements: 5.1
        """
        if not self._client or not self.use_tls:
            return
        
        try:
            if self.ca_cert_path:
                self._client.tls_set(
                    ca_certs=self.ca_cert_path,
                    cert_reqs=ssl.CERT_REQUIRED,
                    tls_version=ssl.PROTOCOL_TLSv1_2
                )
            else:
                self._client.tls_set(cert_reqs=ssl.CERT_NONE)
            
            logger.info("TLS encryption configured")
            
        except Exception as e:
            logger.error(f"Failed to setup TLS: {e}")
            raise
    
    def connect(self) -> bool:
        """
        Connect to MQTT broker.
        
        Returns:
            True if connection initiated successfully
            
        Requirements: 5.1, 5.3
        """
        if not MQTT_AVAILABLE:
            logger.warning("MQTT not available, simulating connection")
            self._status = ConnectionStatus.CONNECTED
            return True
        
        try:
            self._status = ConnectionStatus.CONNECTING
            logger.info(f"Connecting to MQTT broker {self.broker_host}:{self.broker_port}...")
            
            self._client.connect(self.broker_host, self.broker_port, keepalive=60)
            self._client.loop_start()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            self._status = ConnectionStatus.ERROR
            return False
    
    def disconnect(self) -> None:
        """
        Disconnect from MQTT broker.
        
        Requirements: 5.3
        """
        if not MQTT_AVAILABLE:
            self._status = ConnectionStatus.DISCONNECTED
            return
        
        try:
            if self._client:
                self._client.loop_stop()
                self._client.disconnect()
            
            self._status = ConnectionStatus.DISCONNECTED
            logger.info("Disconnected from MQTT broker")
            
        except Exception as e:
            logger.error(f"Error disconnecting from MQTT broker: {e}")
    
    def publish(self, payload: Dict) -> bool:
        """
        Publish sensor data to MQTT topic.
        
        Args:
            payload: Data payload to publish
            
        Returns:
            True if publish initiated successfully
            
        Requirements: 5.2, 5.5
        """
        if self._status != ConnectionStatus.CONNECTED:
            logger.warning(f"Cannot publish: not connected (status={self._status.value})")
            return False
        
        try:
            # Convert payload to JSON
            message = json.dumps(payload)
            
            if not MQTT_AVAILABLE:
                logger.debug(f"Mock publish to {self.topic}: {len(message)} bytes")
                return True
            
            # Publish with QoS 1 (at-least-once delivery)
            result = self._client.publish(
                self.topic,
                message,
                qos=self.qos,
                retain=False
            )
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.debug(f"Published to {self.topic}: {len(message)} bytes")
                return True
            else:
                logger.error(f"Publish failed with code {result.rc}")
                return False
                
        except Exception as e:
            logger.error(f"Error publishing message: {e}")
            return False
    
    def reconnect_with_backoff(self) -> bool:
        """
        Attempt to reconnect with exponential backoff.
        
        Returns:
            True if reconnection initiated successfully
            
        Requirements: 5.4
        """
        if self._status == ConnectionStatus.CONNECTED:
            return True
        
        # Calculate retry delay with exponential backoff
        delay = min(self._retry_delay, self.max_retry_delay)
        
        logger.info(f"Reconnecting in {delay} seconds (attempt {self._retry_count + 1})...")
        time.sleep(delay)
        
        success = self.connect()
        
        if success:
            # Reset retry state on successful connection
            self._retry_count = 0
            self._retry_delay = 1
        else:
            # Increase retry delay exponentially
            self._retry_count += 1
            self._retry_delay = min(self._retry_delay * 2, self.max_retry_delay)
        
        return success
    
    def _on_connect(self, client, userdata, flags, rc):
        """
        Callback when connection is established.
        
        Requirements: 5.3
        """
        if rc == 0:
            self._status = ConnectionStatus.CONNECTED
            self._retry_count = 0
            self._retry_delay = 1
            logger.info("Connected to MQTT broker successfully")
            
            if self._on_connect_callback:
                self._on_connect_callback()
        else:
            self._status = ConnectionStatus.ERROR
            logger.error(f"Connection failed with code {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """
        Callback when connection is lost.
        
        Requirements: 5.3, 5.4
        """
        self._status = ConnectionStatus.DISCONNECTED
        
        if rc == 0:
            logger.info("Disconnected from MQTT broker (clean)")
        else:
            logger.warning(f"Disconnected from MQTT broker (unexpected, code={rc})")
        
        if self._on_disconnect_callback:
            self._on_disconnect_callback()
    
    def _on_publish(self, client, userdata, mid):
        """Callback when message is published."""
        logger.debug(f"Message {mid} published successfully")
        
        if self._on_publish_callback:
            self._on_publish_callback(mid)
    
    def set_on_connect_callback(self, callback: Callable) -> None:
        """Set callback for connection events."""
        self._on_connect_callback = callback
    
    def set_on_disconnect_callback(self, callback: Callable) -> None:
        """Set callback for disconnection events."""
        self._on_disconnect_callback = callback
    
    def set_on_publish_callback(self, callback: Callable) -> None:
        """Set callback for publish events."""
        self._on_publish_callback = callback
    
    @property
    def status(self) -> ConnectionStatus:
        """
        Get current connection status.
        
        Requirements: 5.3
        """
        return self._status
    
    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._status == ConnectionStatus.CONNECTED
    
    def get_connection_info(self) -> Dict:
        """Get connection information."""
        return {
            "device_uuid": self.device_uuid,
            "broker_host": self.broker_host,
            "broker_port": self.broker_port,
            "topic": self.topic,
            "status": self._status.value,
            "use_tls": self.use_tls,
            "qos": self.qos,
            "retry_count": self._retry_count,
            "retry_delay": self._retry_delay
        }
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
