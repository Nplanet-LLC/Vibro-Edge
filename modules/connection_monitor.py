"""
Connection Monitor Module

This module monitors internet connectivity and manages offline/online state
transitions, triggering appropriate actions for data buffering and synchronization.

Requirements: 4.1, 4.3, 4.4, 4.7
"""

import logging
import time
import threading
from typing import Optional, Callable
from enum import Enum
from datetime import datetime

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """Connection state machine states."""
    ONLINE = "online"
    OFFLINE = "offline"
    SYNCING = "syncing"
    UNKNOWN = "unknown"


class ConnectionMonitor:
    """
    Monitors internet connectivity and manages state transitions.
    
    Implements a state machine: ONLINE → OFFLINE → SYNCING → ONLINE
    Pings backend health endpoint periodically to check connectivity.
    """
    
    def __init__(
        self,
        backend_url: str = "http://localhost:3000",
        health_endpoint: str = "/api/health",
        check_interval: int = 30,
        timeout: int = 5
    ):
        """
        Initialize connection monitor.
        
        Args:
            backend_url: Backend server URL
            health_endpoint: Health check endpoint path
            check_interval: Seconds between connectivity checks
            timeout: Request timeout in seconds
            
        Requirements: 4.3
        """
        self.backend_url = backend_url.rstrip('/')
        self.health_endpoint = health_endpoint
        self.check_interval = check_interval
        self.timeout = timeout
        
        # State
        self._state = ConnectionState.UNKNOWN
        self._previous_state = ConnectionState.UNKNOWN
        self._last_check_time: Optional[datetime] = None
        self._last_online_time: Optional[datetime] = None
        self._last_offline_time: Optional[datetime] = None
        
        # Monitoring thread
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False
        
        # Callbacks
        self._on_state_change_callback: Optional[Callable] = None
        self._on_online_callback: Optional[Callable] = None
        self._on_offline_callback: Optional[Callable] = None
        self._on_sync_start_callback: Optional[Callable] = None
        self._on_sync_complete_callback: Optional[Callable] = None
        
        logger.info(f"Connection Monitor initialized: backend={backend_url}, "
                   f"check_interval={check_interval}s")
    
    def start(self) -> None:
        """
        Start monitoring connectivity.
        
        Requirements: 4.3
        """
        if self._running:
            logger.warning("Connection monitor already running")
            return
        
        self._running = True
        self._stop_event.clear()
        
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="ConnectionMonitor"
        )
        self._monitor_thread.start()
        
        logger.info("Connection monitor started")
    
    def stop(self) -> None:
        """Stop monitoring connectivity."""
        if not self._running:
            return
        
        self._running = False
        self._stop_event.set()
        
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        
        logger.info("Connection monitor stopped")
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        logger.info("Connection monitoring loop started")
        
        while not self._stop_event.is_set():
            try:
                # Check connectivity
                is_online = self._check_connectivity()
                self._last_check_time = datetime.now()
                
                # Update state based on connectivity
                self._update_state(is_online)
                
                # Wait for next check
                self._stop_event.wait(self.check_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.check_interval)
        
        logger.info("Connection monitoring loop stopped")
    
    def _check_connectivity(self) -> bool:
        """
        Check internet connectivity by pinging backend health endpoint.
        
        Returns:
            True if backend is reachable
            
        Requirements: 4.3
        """
        if not REQUESTS_AVAILABLE:
            logger.debug("Requests library not available, assuming online")
            return True
        
        try:
            url = f"{self.backend_url}{self.health_endpoint}"
            response = requests.get(url, timeout=self.timeout)
            
            is_online = response.status_code == 200
            
            if is_online:
                logger.debug(f"Backend health check successful: {url}")
            else:
                logger.warning(f"Backend health check failed: {url} (status={response.status_code})")
            
            return is_online
            
        except requests.exceptions.Timeout:
            logger.warning("Backend health check timed out")
            return False
        except requests.exceptions.ConnectionError:
            logger.warning("Backend health check connection error")
            return False
        except Exception as e:
            logger.error(f"Backend health check error: {e}")
            return False
    
    def _update_state(self, is_online: bool) -> None:
        """
        Update connection state based on connectivity check.
        
        Implements state machine:
        - ONLINE → OFFLINE: Connection lost, start buffering
        - OFFLINE → SYNCING: Connection restored, start sync
        - SYNCING → ONLINE: Sync complete
        
        Requirements: 4.1, 4.3, 4.4
        """
        self._previous_state = self._state
        
        if is_online:
            if self._state == ConnectionState.OFFLINE:
                # Transition: OFFLINE → SYNCING
                logger.info("Connection restored, starting synchronization")
                self._state = ConnectionState.SYNCING
                self._last_online_time = datetime.now()
                
                # Trigger sync callback
                if self._on_sync_start_callback:
                    self._on_sync_start_callback()
                
            elif self._state == ConnectionState.SYNCING:
                # Stay in SYNCING until explicitly moved to ONLINE
                pass
                
            elif self._state in [ConnectionState.UNKNOWN, ConnectionState.ONLINE]:
                # Transition: UNKNOWN/ONLINE → ONLINE
                if self._state != ConnectionState.ONLINE:
                    logger.info("Connection is online")
                    self._state = ConnectionState.ONLINE
                    self._last_online_time = datetime.now()
                    
                    if self._on_online_callback:
                        self._on_online_callback()
        else:
            if self._state in [ConnectionState.ONLINE, ConnectionState.SYNCING, ConnectionState.UNKNOWN]:
                # Transition: ONLINE/SYNCING/UNKNOWN → OFFLINE
                logger.warning("Connection lost, switching to offline mode")
                self._state = ConnectionState.OFFLINE
                self._last_offline_time = datetime.now()
                
                # Trigger offline callback
                if self._on_offline_callback:
                    self._on_offline_callback()
        
        # Notify state change
        if self._state != self._previous_state:
            logger.info(f"State transition: {self._previous_state.value} → {self._state.value}")
            
            if self._on_state_change_callback:
                self._on_state_change_callback(self._previous_state, self._state)
    
    def mark_sync_complete(self) -> None:
        """
        Mark synchronization as complete.
        
        Transitions from SYNCING → ONLINE
        
        Requirements: 4.4, 4.7
        """
        if self._state == ConnectionState.SYNCING:
            logger.info("Synchronization complete, returning to online mode")
            self._previous_state = self._state
            self._state = ConnectionState.ONLINE
            
            if self._on_sync_complete_callback:
                self._on_sync_complete_callback()
            
            if self._on_state_change_callback:
                self._on_state_change_callback(self._previous_state, self._state)
        else:
            logger.warning(f"Cannot mark sync complete: not in SYNCING state (current={self._state.value})")
    
    def force_check(self) -> bool:
        """
        Force an immediate connectivity check.
        
        Returns:
            True if backend is reachable
        """
        is_online = self._check_connectivity()
        self._last_check_time = datetime.now()
        self._update_state(is_online)
        return is_online
    
    def set_on_state_change_callback(self, callback: Callable) -> None:
        """
        Set callback for state changes.
        
        Callback signature: callback(old_state: ConnectionState, new_state: ConnectionState)
        """
        self._on_state_change_callback = callback
    
    def set_on_online_callback(self, callback: Callable) -> None:
        """Set callback for online events."""
        self._on_online_callback = callback
    
    def set_on_offline_callback(self, callback: Callable) -> None:
        """
        Set callback for offline events.
        
        Requirements: 4.1
        """
        self._on_offline_callback = callback
    
    def set_on_sync_start_callback(self, callback: Callable) -> None:
        """
        Set callback for sync start events.
        
        Requirements: 4.4
        """
        self._on_sync_start_callback = callback
    
    def set_on_sync_complete_callback(self, callback: Callable) -> None:
        """
        Set callback for sync complete events.
        
        Requirements: 4.7
        """
        self._on_sync_complete_callback = callback
    
    @property
    def state(self) -> ConnectionState:
        """Get current connection state."""
        return self._state
    
    @property
    def is_online(self) -> bool:
        """Check if currently online."""
        return self._state in [ConnectionState.ONLINE, ConnectionState.SYNCING]
    
    @property
    def is_offline(self) -> bool:
        """Check if currently offline."""
        return self._state == ConnectionState.OFFLINE
    
    @property
    def is_syncing(self) -> bool:
        """Check if currently syncing."""
        return self._state == ConnectionState.SYNCING
    
    def get_status(self) -> dict:
        """Get detailed status information."""
        return {
            "state": self._state.value,
            "previous_state": self._previous_state.value,
            "is_online": self.is_online,
            "is_offline": self.is_offline,
            "is_syncing": self.is_syncing,
            "last_check_time": self._last_check_time.isoformat() if self._last_check_time else None,
            "last_online_time": self._last_online_time.isoformat() if self._last_online_time else None,
            "last_offline_time": self._last_offline_time.isoformat() if self._last_offline_time else None,
            "backend_url": self.backend_url,
            "check_interval": self.check_interval,
            "running": self._running
        }
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
