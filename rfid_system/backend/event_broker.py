"""Thread-safe event broker for publishing and subscribing to RFID events."""

import threading
from collections import deque
from datetime import datetime
from typing import Dict, List, Any, Optional


class EventBroker:
    """Thread-safe event bus using deque and Lock."""
    
    def __init__(self, maxlen: int = 500):
        self._events: deque = deque(maxlen=maxlen)
        self._lock = threading.Lock()
        self._total_scans = 0
        self._known_scans = 0
        self._unknown_scans = 0
    
    def publish(self, uid: str, fio: Optional[str], status: str) -> None:
        """
        Publish an RFID scan event.
        
        Args:
            uid: RFID card UID in hex format
            fio: Full name if known, None otherwise
            status: Scan status ('✅ Known', '❌ Unknown', etc.)
        """
        now = datetime.now()
        event = {
            "time": now.strftime("%H:%M:%S"),
            "date": now.strftime("%Y-%m-%d"),
            "uid": uid.upper(),
            "fio": fio or "Неизвестно",
            "status": status
        }
        
        with self._lock:
            self._events.append(event)
            self._total_scans += 1
            if status.startswith("✅"):
                self._known_scans += 1
            else:
                self._unknown_scans += 1
    
    def get_recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get the most recent events."""
        with self._lock:
            events_list = list(self._events)
            return events_list[-limit:] if limit < len(events_list) else events_list
    
    def get_stats(self) -> Dict[str, int]:
        """Get scan statistics."""
        with self._lock:
            return {
                "total": self._total_scans,
                "known": self._known_scans,
                "unknown": self._unknown_scans
            }
    
    def get_all_events(self) -> List[Dict[str, Any]]:
        """Get all events (for initial load)."""
        with self._lock:
            return list(self._events)


# Global broker instance
broker = EventBroker()
