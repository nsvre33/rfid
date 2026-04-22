"""Serial port handler with auto-detection and reconnection."""

import re
import time
from pathlib import Path
from typing import Optional, List

import serial
from serial.tools.list_ports import comports
from PyQt6.QtCore import QThread, pyqtSignal


class SerialHandler(QThread):
    """
    QThread for handling RFID serial communication.
    
    Features:
    - Auto-detection of COM ports by keywords
    - Automatic reconnection on disconnect
    - Debounce protection
    - Strict regex parsing for RFID:HEX format
    """
    
    uid_received = pyqtSignal(str)
    status_changed = pyqtSignal(str)
    
    def __init__(self, baudrate: int = 9600, timeout: float = 1.0,
                 port_keywords: Optional[List[str]] = None):
        super().__init__()
        self.baudrate = baudrate
        self.timeout = timeout
        self.port_keywords = port_keywords or ["arduino", "ch340", "cp2102", "usb serial", "ftdi"]
        self._running = True
        self._connected = False
        self._port: Optional[serial.Serial] = None
        self._last_uid: Optional[str] = None
        self._last_read_time: float = 0
    
    def _find_port(self) -> Optional[str]:
        """Find available COM port by keywords or fallback to first available."""
        ports = comports()
        
        # First pass: search by keywords
        for port in ports:
            port_lower = (port.device + " " + (port.description or "")).lower()
            for keyword in self.port_keywords:
                if keyword.lower() in port_lower:
                    print(f"Found port by keyword '{keyword}': {port.device}")
                    return port.device
        
        # Fallback: use first available port
        if ports:
            print(f"No keyword match, using first available port: {ports[0].device}")
            return ports[0].device
        
        return None
    
    def _connect(self) -> bool:
        """Attempt to connect to serial port."""
        port_name = self._find_port()
        if not port_name:
            return False
        
        try:
            self._port = serial.Serial(
                port=port_name,
                baudrate=self.baudrate,
                timeout=self.timeout,
                write_timeout=self.timeout
            )
            self._connected = True
            self.status_changed.emit(f"✅ Подключено: {port_name}")
            print(f"Connected to {port_name}")
            return True
        except serial.SerialException as e:
            print(f"Connection failed: {e}")
            self._connected = False
            return False
    
    def _disconnect(self) -> None:
        """Disconnect from serial port."""
        if self._port and self._port.is_open:
            try:
                self._port.close()
            except Exception as e:
                print(f"Error closing port: {e}")
        self._connected = False
        self._port = None
    
    def _parse_line(self, line: str) -> Optional[str]:
        """
        Parse incoming line for RFID UID.
        
        Expected format: RFID:[0-9A-Fa-f]+
        Returns uppercase hex UID or None.
        """
        pattern = r"RFID:([0-9A-Fa-f]+)"
        match = re.search(pattern, line)
        if match:
            uid = match.group(1).upper()
            return uid
        return None
    
    def run(self) -> None:
        """Main thread loop with auto-reconnection."""
        while self._running:
            if not self._connected:
                self.status_changed.emit("🔍 Поиск порта...")
                if not self._connect():
                    time.sleep(3)  # Wait before retry
                    continue
            
            try:
                if self._port and self._port.is_open:
                    line = self._port.readline().decode('utf-8', errors='ignore').strip()
                    
                    if line:
                        print(f"Received: {line}")
                        uid = self._parse_line(line)
                        
                        if uid:
                            # Debounce protection: ignore same UID within 0.5s
                            current_time = time.time()
                            if uid == self._last_uid and (current_time - self._last_read_time) < 0.5:
                                continue
                            
                            self._last_uid = uid
                            self._last_read_time = current_time
                            
                            self.uid_received.emit(uid)
                            time.sleep(0.5)  # Debounce delay
                else:
                    self._connected = False
            except serial.SerialException as e:
                print(f"Serial error: {e}")
                self._disconnect()
                self.status_changed.emit("⚠️ Ошибка соединения")
            except UnicodeDecodeError as e:
                print(f"Decode error: {e}")
            except Exception as e:
                print(f"Unexpected error: {e}")
                self._disconnect()
            
            time.sleep(0.1)  # Small delay to prevent CPU spinning
    
    def stop(self) -> None:
        """Stop the thread gracefully."""
        self._running = False
        self._disconnect()
        self.wait()  # Wait for thread to finish
