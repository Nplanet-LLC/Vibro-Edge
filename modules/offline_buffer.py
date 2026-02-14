"""
Offline Buffer Module

This module provides local SQLite-based storage for sensor data when
the edge device is offline. Data is synchronized when connection is restored.

Requirements: 4.1, 4.2, 4.5, 4.6
"""

import sqlite3
import logging
import json
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Default database path
DEFAULT_DB_PATH = "/var/lib/turbine-monitor/buffer.db"


@dataclass
class BufferedReading:
    """
    Container for a buffered sensor reading.
    
    Attributes:
        id: Database record ID
        timestamp: Reading timestamp
        raw_data: Raw sensor data (JSON)
        fft_data: FFT analysis results (JSON)
        synced: Whether reading has been synchronized
        created_at: When record was created
    """
    id: int
    timestamp: float
    raw_data: str
    fft_data: str
    synced: bool
    created_at: str
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "raw_data": json.loads(self.raw_data) if self.raw_data else None,
            "fft_data": json.loads(self.fft_data) if self.fft_data else None,
            "synced": self.synced,
            "created_at": self.created_at
        }


class OfflineBuffer:
    """
    SQLite-based offline buffer for sensor data.
    
    Stores sensor readings locally when the device is offline and
    provides synchronization capabilities when connection is restored.
    """
    
    def __init__(
        self,
        db_path: str = DEFAULT_DB_PATH,
        max_size_mb: int = 100,
        warn_threshold: float = 0.9
    ):
        """
        Initialize the offline buffer.
        
        Args:
            db_path: Path to SQLite database file
            max_size_mb: Maximum database size in MB
            warn_threshold: Threshold for capacity warning (0.0-1.0)
            
        Requirements: 4.1, 4.6
        """
        self.db_path = Path(db_path)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.warn_threshold = warn_threshold
        
        # Create directory if it doesn't exist
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Offline Buffer initialized: db_path={self.db_path}, "
                   f"max_size={max_size_mb}MB")
        
        # Initialize database
        self._init_database()
    
    def _init_database(self) -> None:
        """
        Initialize SQLite database schema.
        
        Requirements: 4.1
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                
                # Create sensor_data table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sensor_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp REAL NOT NULL,
                        raw_data TEXT NOT NULL,
                        fft_data TEXT NOT NULL,
                        synced INTEGER DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create indexes
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_synced 
                    ON sensor_data(synced)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_timestamp 
                    ON sensor_data(timestamp)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_created_at 
                    ON sensor_data(created_at)
                """)
                
                conn.commit()
                logger.info("Database schema initialized")
                
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def insert_reading(
        self,
        timestamp: float,
        raw_data: Dict,
        fft_data: Dict
    ) -> int:
        """
        Insert a sensor reading into the buffer.
        
        Args:
            timestamp: Reading timestamp
            raw_data: Raw sensor data dictionary
            fft_data: FFT analysis results dictionary
            
        Returns:
            Record ID
            
        Requirements: 4.1, 4.2
        """
        try:
            # Check buffer capacity
            self._check_capacity()
            
            # Convert data to JSON
            raw_json = json.dumps(raw_data)
            fft_json = json.dumps(fft_data)
            
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO sensor_data (timestamp, raw_data, fft_data, synced)
                    VALUES (?, ?, ?, 0)
                """, (timestamp, raw_json, fft_json))
                
                record_id = cursor.lastrowid
                conn.commit()
                
                logger.debug(f"Inserted reading: id={record_id}, timestamp={timestamp}")
                return record_id
                
        except sqlite3.Error as e:
            logger.error(f"Failed to insert reading: {e}")
            raise
    
    def get_unsynced_readings(
        self,
        limit: Optional[int] = None,
        order_by_timestamp: bool = True
    ) -> List[BufferedReading]:
        """
        Get all unsynced readings from the buffer.
        
        Args:
            limit: Maximum number of readings to return
            order_by_timestamp: Whether to order by timestamp (chronological)
            
        Returns:
            List of buffered readings
            
        Requirements: 4.4
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                
                query = """
                    SELECT id, timestamp, raw_data, fft_data, synced, created_at
                    FROM sensor_data
                    WHERE synced = 0
                """
                
                if order_by_timestamp:
                    query += " ORDER BY timestamp ASC"
                
                if limit:
                    query += f" LIMIT {limit}"
                
                cursor.execute(query)
                rows = cursor.fetchall()
                
                readings = [
                    BufferedReading(
                        id=row[0],
                        timestamp=row[1],
                        raw_data=row[2],
                        fft_data=row[3],
                        synced=bool(row[4]),
                        created_at=row[5]
                    )
                    for row in rows
                ]
                
                logger.debug(f"Retrieved {len(readings)} unsynced readings")
                return readings
                
        except sqlite3.Error as e:
            logger.error(f"Failed to get unsynced readings: {e}")
            raise
    
    def mark_as_synced(self, record_ids: List[int]) -> int:
        """
        Mark readings as synchronized.
        
        Args:
            record_ids: List of record IDs to mark as synced
            
        Returns:
            Number of records updated
            
        Requirements: 4.5
        """
        if not record_ids:
            return 0
        
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                
                placeholders = ','.join('?' * len(record_ids))
                cursor.execute(f"""
                    UPDATE sensor_data
                    SET synced = 1
                    WHERE id IN ({placeholders})
                """, record_ids)
                
                updated = cursor.rowcount
                conn.commit()
                
                logger.info(f"Marked {updated} readings as synced")
                return updated
                
        except sqlite3.Error as e:
            logger.error(f"Failed to mark readings as synced: {e}")
            raise
    
    def cleanup_old_records(self, days: int = 7) -> int:
        """
        Delete old synced records.
        
        Args:
            days: Delete records older than this many days
            
        Returns:
            Number of records deleted
            
        Requirements: 4.6
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    DELETE FROM sensor_data
                    WHERE synced = 1
                    AND created_at < ?
                """, (cutoff_date.isoformat(),))
                
                deleted = cursor.rowcount
                conn.commit()
                
                logger.info(f"Deleted {deleted} old synced records (older than {days} days)")
                return deleted
                
        except sqlite3.Error as e:
            logger.error(f"Failed to cleanup old records: {e}")
            raise
    
    def _check_capacity(self) -> None:
        """
        Check buffer capacity and warn if approaching limit.
        
        Requirements: 4.6
        """
        try:
            if not self.db_path.exists():
                return
            
            current_size = self.db_path.stat().st_size
            usage_ratio = current_size / self.max_size_bytes
            
            if usage_ratio >= self.warn_threshold:
                logger.warning(f"Buffer capacity at {usage_ratio*100:.1f}% "
                             f"({current_size/1024/1024:.1f}MB / "
                             f"{self.max_size_bytes/1024/1024:.1f}MB)")
                
                # If at 100%, delete oldest synced records
                if usage_ratio >= 1.0:
                    logger.warning("Buffer full, deleting oldest synced records")
                    self._delete_oldest_synced(limit=100)
                    
        except Exception as e:
            logger.error(f"Error checking capacity: {e}")
    
    def _delete_oldest_synced(self, limit: int = 100) -> int:
        """
        Delete oldest synced records.
        
        Args:
            limit: Number of records to delete
            
        Returns:
            Number of records deleted
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    DELETE FROM sensor_data
                    WHERE id IN (
                        SELECT id FROM sensor_data
                        WHERE synced = 1
                        ORDER BY created_at ASC
                        LIMIT ?
                    )
                """, (limit,))
                
                deleted = cursor.rowcount
                conn.commit()
                
                logger.info(f"Deleted {deleted} oldest synced records")
                return deleted
                
        except sqlite3.Error as e:
            logger.error(f"Failed to delete oldest records: {e}")
            raise
    
    def get_buffer_stats(self) -> Dict:
        """
        Get buffer statistics.
        
        Returns:
            Dictionary with buffer statistics
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                
                # Total records
                cursor.execute("SELECT COUNT(*) FROM sensor_data")
                total_records = cursor.fetchone()[0]
                
                # Unsynced records
                cursor.execute("SELECT COUNT(*) FROM sensor_data WHERE synced = 0")
                unsynced_records = cursor.fetchone()[0]
                
                # Synced records
                synced_records = total_records - unsynced_records
                
                # Database size
                db_size = self.db_path.stat().st_size if self.db_path.exists() else 0
                usage_ratio = db_size / self.max_size_bytes
                
                # Oldest and newest timestamps
                cursor.execute("""
                    SELECT MIN(timestamp), MAX(timestamp)
                    FROM sensor_data
                    WHERE synced = 0
                """)
                min_ts, max_ts = cursor.fetchone()
                
                return {
                    "total_records": total_records,
                    "unsynced_records": unsynced_records,
                    "synced_records": synced_records,
                    "db_size_bytes": db_size,
                    "db_size_mb": db_size / 1024 / 1024,
                    "max_size_mb": self.max_size_bytes / 1024 / 1024,
                    "usage_percent": usage_ratio * 100,
                    "oldest_unsynced_timestamp": min_ts,
                    "newest_unsynced_timestamp": max_ts
                }
                
        except sqlite3.Error as e:
            logger.error(f"Failed to get buffer stats: {e}")
            return {}
    
    def clear_all(self) -> int:
        """
        Clear all records from the buffer (for testing).
        
        Returns:
            Number of records deleted
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM sensor_data")
                deleted = cursor.rowcount
                conn.commit()
                
                logger.warning(f"Cleared all {deleted} records from buffer")
                return deleted
                
        except sqlite3.Error as e:
            logger.error(f"Failed to clear buffer: {e}")
            raise
    
    def close(self) -> None:
        """Close database connection and cleanup."""
        logger.info("Offline buffer closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
