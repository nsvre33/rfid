"""Configuration loader with defaults and validation."""

import json
from pathlib import Path
from typing import Dict, Any, List


DEFAULT_CONFIG: Dict[str, Any] = {
    "serial": {
        "baudrate": 9600,
        "timeout": 1.0,
        "port_keywords": ["arduino", "ch340", "cp2102", "usb serial", "ftdi"]
    },
    "paths": {
        "registry": "data/registry.xlsx",
        "logs_dir": "data/logs",
        "photos_dir": "data/photos"
    },
    "ui": {
        "max_log_rows": 150
    },
    "web": {
        "host": "0.0.0.0",
        "port": 8000
    },
    "sounds": {
        "enable": True,
        "ok": "assets/ok.wav",
        "err": "assets/err.wav"
    }
}


class Config:
    """Configuration manager with lazy loading and validation."""
    
    def __init__(self, config_path: str = "config.json"):
        self._config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        self._loaded = False
    
    def _load(self) -> None:
        """Load configuration from file or use defaults."""
        if self._loaded:
            return
        
        if self._config_path.exists():
            try:
                with open(self._config_path, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                # Merge with defaults
                self._config = DEFAULT_CONFIG.copy()
                self._deep_update(self._config, file_config)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Config load error: {e}, using defaults")
                self._config = DEFAULT_CONFIG.copy()
        else:
            self._config = DEFAULT_CONFIG.copy()
        
        self._loaded = True
    
    def _deep_update(self, base: Dict[str, Any], update: Dict[str, Any]) -> None:
        """Recursively update nested dictionaries."""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_update(base[key], value)
            else:
                base[key] = value
    
    def get(self, *keys: str, default: Any = None) -> Any:
        """Get nested configuration value using dot notation keys."""
        self._load()
        
        current = self._config
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current
    
    @property
    def serial_baudrate(self) -> int:
        return int(self.get("serial", "baudrate", default=9600))
    
    @property
    def serial_timeout(self) -> float:
        return float(self.get("serial", "timeout", default=1.0))
    
    @property
    def port_keywords(self) -> List[str]:
        return self.get("serial", "port_keywords", default=DEFAULT_CONFIG["serial"]["port_keywords"])
    
    @property
    def registry_path(self) -> Path:
        return Path(self.get("paths", "registry", default="data/registry.xlsx"))
    
    @property
    def logs_dir(self) -> Path:
        return Path(self.get("paths", "logs_dir", default="data/logs"))
    
    @property
    def photos_dir(self) -> Path:
        return Path(self.get("paths", "photos_dir", default="data/photos"))
    
    @property
    def max_log_rows(self) -> int:
        return int(self.get("ui", "max_log_rows", default=150))
    
    @property
    def web_host(self) -> str:
        return str(self.get("web", "host", default="0.0.0.0"))
    
    @property
    def web_port(self) -> int:
        return int(self.get("web", "port", default=8000))
    
    @property
    def sounds_enable(self) -> bool:
        return bool(self.get("sounds", "enable", default=True))
    
    @property
    def sound_ok(self) -> str:
        return str(self.get("sounds", "ok", default="assets/ok.wav"))
    
    @property
    def sound_err(self) -> str:
        return str(self.get("sounds", "err", default="assets/err.wav"))


# Global config instance
config = Config()
