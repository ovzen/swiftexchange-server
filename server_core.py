# -*- coding: utf-8 -*-
import subprocess
import sys
import time
import logging
import socket
from pathlib import Path

logger = logging.getLogger("server_core")

def port_is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('0.0.0.0', port))
            return True
        except OSError:
            return False

class ServerCore:
    def __init__(self, settings):
        self.settings = settings
        self.process = None
        self.script_path = Path(__file__).parent / "server_app.py"

    def update_settings(self, settings):
        self.settings = settings
        logger.info("Настройки обновлены")

    def start(self):
        if self.process and self.process.poll() is None:
            return True
        if not port_is_free(self.settings.port):
            logger.error(f"Порт {self.settings.port} занят")
            return False
        if not self.script_path.exists():
            logger.error("server_app.py не найден")
            return False
        cmd = [
            sys.executable,
            str(self.script_path),
            "--host", self.settings.host,
            "--port", str(self.settings.port),
            "--upload-dir", str(self.settings.upload_dir),
            "--max-size-mb", str(self.settings.max_file_size_mb)
        ]
        try:
            flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=flags
            )
            time.sleep(1.5)
            if self.process.poll() is not None:
                err = self.process.stderr.read()
                logger.error(f"Ошибка запуска: {err}")
                self.process = None
                return False
            logger.info(f"Сервер запущен на {self.settings.host}:{self.settings.port}")
            return True
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            self.process = None
            return False

    def stop(self):
        if not self.process:
            return True
        if self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=3)
                logger.info("Сервер остановлен")
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
                logger.info("Сервер убит")
            except Exception as e:
                logger.error(f"Ошибка остановки: {e}")
                return False
        else:
            logger.info("Сервер уже завершён")
        self.process = None
        return True

    def is_running(self):
        return self.process is not None and self.process.poll() is None