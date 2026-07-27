# -*- coding: utf-8 -*-
import json
from pathlib import Path

CONFIG_FILE = Path("config.json")
DEFAULTS = {
    "host": "0.0.0.0",
    "port": 8000,
    "upload_dir": "uploads",
    "max_file_size_mb": 1024,
    "auto_start": False
}

class Settings:
    def __init__(self):
        self._data = self._load()

    def _load(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                self._save(DEFAULTS)
                return DEFAULTS.copy()
        else:
            self._save(DEFAULTS)
            return DEFAULTS.copy()

    def _save(self, data):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value
        self._save(self._data)

    @property
    def host(self):
        return self._data.get("host", "0.0.0.0")

    @property
    def port(self):
        return self._data.get("port", 8000)

    @property
    def upload_dir(self):
        return Path(self._data.get("upload_dir", "uploads"))

    @property
    def max_file_size_mb(self):
        return self._data.get("max_file_size_mb", 1024)

    @property
    def auto_start(self):
        return self._data.get("auto_start", False)