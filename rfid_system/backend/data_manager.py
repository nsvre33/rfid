"""Thread-safe data manager for registry, logs, and photos."""

import shutil
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

import pandas as pd

from .config import config
from .event_broker import broker


class DataManager:
    """
    Thread-safe manager for RFID data operations.
    
    Handles:
    - Registry Excel file (read/write)
    - Daily log files
    - Photo storage and linking
    - Event publishing to broker
    """
    
    def __init__(self):
        self._registry_lock = threading.Lock()
        self._log_lock = threading.Lock()
        self._ensure_directories()
        self._init_registry()
    
    def _ensure_directories(self) -> None:
        """Create required directories if they don't exist."""
        config.registry_path.parent.mkdir(parents=True, exist_ok=True)
        config.logs_dir.mkdir(parents=True, exist_ok=True)
        config.photos_dir.mkdir(parents=True, exist_ok=True)
    
    def _init_registry(self) -> None:
        """Initialize registry Excel file with headers if it doesn't exist."""
        registry_path = config.registry_path
        if not registry_path.exists():
            try:
                df = pd.DataFrame(columns=["UID", "FIO", "Photo"])
                df.to_excel(registry_path, index=False, engine='openpyxl')
                print(f"Created new registry: {registry_path}")
            except Exception as e:
                print(f"Error creating registry: {e}")
    
    def _read_registry(self) -> pd.DataFrame:
        """Read registry Excel file."""
        try:
            return pd.read_excel(config.registry_path, dtype={"UID": str}, engine='openpyxl')
        except FileNotFoundError:
            self._init_registry()
            return pd.DataFrame(columns=["UID", "FIO", "Photo"])
        except Exception as e:
            print(f"Error reading registry: {e}")
            return pd.DataFrame(columns=["UID", "FIO", "Photo"])
    
    def _write_registry(self, df: pd.DataFrame) -> bool:
        """Write DataFrame to registry Excel file."""
        try:
            df.to_excel(config.registry_path, index=False, engine='openpyxl')
            return True
        except PermissionError:
            print("Registry is locked by another process (Excel open), skipping write")
            return False
        except Exception as e:
            print(f"Error writing registry: {e}")
            return False
    
    def find_uid(self, uid: str) -> Optional[Dict[str, Any]]:
        """
        Find a UID in the registry.
        
        Args:
            uid: RFID card UID
            
        Returns:
            Dict with 'fio' and 'photo' keys if found, None otherwise
        """
        with self._registry_lock:
            df = self._read_registry()
            uid_upper = uid.upper()
            match = df[df["UID"] == uid_upper]
            
            if not match.empty:
                row = match.iloc[0]
                return {
                    "fio": str(row["FIO"]),
                    "photo": str(row["Photo"]) if pd.notna(row["Photo"]) else None
                }
            return None
    
    def add_or_update(self, uid: str, fio: str, photo_path: Optional[str] = None) -> bool:
        """
        Add or update a UID entry in the registry.
        
        Args:
            uid: RFID card UID
            fio: Full name
            photo_path: Path to photo file (optional)
            
        Returns:
            True if successful, False otherwise
        """
        with self._registry_lock:
            df = self._read_registry()
            uid_upper = uid.upper()
            
            # Copy photo if provided
            saved_photo_name = None
            if photo_path and Path(photo_path).exists():
                src_path = Path(photo_path)
                ext = src_path.suffix.lower()
                if ext not in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
                    ext = '.jpg'
                
                # Create filename from FIO
                safe_fio = "".join(c for c in fio if c.isalnum() or c in ' -_').strip()
                photo_name = f"{safe_fio}{ext}"
                dest_path = config.photos_dir / photo_name
                
                try:
                    shutil.copy2(src_path, dest_path)
                    saved_photo_name = photo_name
                    print(f"Copied photo to {dest_path}")
                except Exception as e:
                    print(f"Error copying photo: {e}")
            
            # Check if UID exists
            existing_idx = df.index[df["UID"] == uid_upper].tolist()
            
            if existing_idx:
                # Update existing entry
                df.loc[existing_idx[0], "FIO"] = fio
                if saved_photo_name:
                    df.loc[existing_idx[0], "Photo"] = saved_photo_name
                print(f"Updated UID {uid_upper} in registry")
            else:
                # Add new entry
                new_row = pd.DataFrame({
                    "UID": [uid_upper],
                    "FIO": [fio],
                    "Photo": [saved_photo_name]
                })
                df = pd.concat([df, new_row], ignore_index=True)
                print(f"Added UID {uid_upper} to registry")
            
            return self._write_registry(df)
    
    def log_scan(self, uid: str, fio: Optional[str], status: str) -> None:
        """
        Log a scan to daily Excel file.
        
        Args:
            uid: RFID card UID
            fio: Full name if known
            status: Scan status
        """
        with self._log_lock:
            today = datetime.now().strftime("%Y-%m-%d")
            log_path = config.logs_dir / f"{today}.xlsx"
            now = datetime.now()
            
            record = {
                "Time": now.strftime("%H:%M:%S"),
                "Date": now.strftime("%Y-%m-%d"),
                "UID": uid.upper(),
                "FIO": fio or "Неизвестно",
                "Status": status
            }
            
            try:
                if log_path.exists():
                    df = pd.read_excel(log_path, dtype={"UID": str}, engine='openpyxl')
                else:
                    df = pd.DataFrame(columns=["Time", "Date", "UID", "FIO", "Status"])
                
                new_row = pd.DataFrame([record])
                df = pd.concat([df, new_row], ignore_index=True)
                df.to_excel(log_path, index=False, engine='openpyxl')
                
            except PermissionError:
                print(f"Log file {log_path} is locked, skipping write")
            except Exception as e:
                print(f"Error writing log: {e}")
            
            # Publish to event broker
            broker.publish(uid, fio, status)
    
    def get_registry_entries(self) -> List[Dict[str, Any]]:
        """Get all registry entries as list of dicts."""
        with self._registry_lock:
            df = self._read_registry()
            # Replace NaN with None for JSON serialization
            df = df.where(pd.notna(df), None)
            records = df.to_dict(orient='records')
            # Ensure all values are JSON-serializable
            for record in records:
                for key, value in record.items():
                    if isinstance(value, float) and str(value) == 'nan':
                        record[key] = None
            return records
    
    def get_photo_path(self, photo_name: Optional[str]) -> Optional[Path]:
        """Get full path to a photo file."""
        if not photo_name:
            return None
        
        photo_path = config.photos_dir / photo_name
        if photo_path.exists():
            return photo_path
        return None


# Global data manager instance
data_manager = DataManager()
