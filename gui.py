# -*- coding: utf-8 -*-
import os
import sys
import threading
import logging
import time
import socket
from pathlib import Path
os.environ["QT_LOGGING_RULES"] = "*.debug=false;*.warning=false"

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import QFont
from server_core import ServerCore, logger
from settings import Settings

class LogHandler(logging.Handler):
    def __init__(self, signal):
        super().__init__()
        self.signal = signal
    def emit(self, record):
        self.signal.emit(self.format(record))

class MainWindow(QMainWindow):
    log_signal = Signal(str)

    def __init__(self):
        super().__init__()
        self.settings = Settings()
        self.server = ServerCore(self.settings)
        self.setWindowTitle("SwiftExchange Server")
        self.setMinimumSize(700, 500)

        self.log_signal.connect(self._append_log)
        handler = LogHandler(self.log_signal)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        self._init_ui()
        self._load_settings_to_ui()
        if self.settings.auto_start:
            QTimer.singleShot(500, self.start_server)

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        tabs = QTabWidget()
        layout.addWidget(tabs)

        # Вкладка "Сервер"
        server_tab = QWidget()
        tabs.addTab(server_tab, "Сервер")
        s_layout = QVBoxLayout(server_tab)

        status_group = QGroupBox("Статус")
        status_box = QHBoxLayout(status_group)
        self.status_label = QLabel("Остановлен")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        status_box.addWidget(self.status_label)
        status_box.addStretch()
        self.port_label = QLabel(f"Порт: {self.settings.port}")
        status_box.addWidget(self.port_label)
        s_layout.addWidget(status_group)

        btn_box = QHBoxLayout()
        self.start_btn = QPushButton("Запустить сервер")
        self.start_btn.clicked.connect(self.start_server)
        self.stop_btn = QPushButton("Остановить сервер")
        self.stop_btn.clicked.connect(self.stop_server)
        self.stop_btn.setEnabled(False)
        btn_box.addWidget(self.start_btn)
        btn_box.addWidget(self.stop_btn)
        btn_box.addStretch()
        s_layout.addLayout(btn_box)

        log_group = QGroupBox("Логи")
        log_box = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        log_box.addWidget(self.log_text)
        s_layout.addWidget(log_group)

        # Вкладка "Настройки"
        settings_tab = QWidget()
        tabs.addTab(settings_tab, "Настройки")
        settings_layout = QFormLayout(settings_tab)

        self.port_spin = QSpinBox()
        self.port_spin.setRange(1024, 65535)
        self.port_spin.setValue(self.settings.port)
        settings_layout.addRow("Порт:", self.port_spin)

        self.dir_edit = QLineEdit(str(self.settings.upload_dir))
        self.dir_btn = QPushButton("Обзор...")
        self.dir_btn.clicked.connect(self._browse_folder)
        dir_row = QHBoxLayout()
        dir_row.addWidget(self.dir_edit)
        dir_row.addWidget(self.dir_btn)
        settings_layout.addRow("Папка для файлов:", dir_row)

        self.size_spin = QSpinBox()
        self.size_spin.setRange(1, 10240)
        self.size_spin.setValue(self.settings.max_file_size_mb)
        settings_layout.addRow("Макс. размер файла (МБ):", self.size_spin)

        self.auto_check = QCheckBox()
        self.auto_check.setChecked(self.settings.auto_start)
        settings_layout.addRow("Автозапуск при старте:", self.auto_check)

        self.save_btn = QPushButton("Сохранить настройки")
        self.save_btn.clicked.connect(self._save_settings)
        settings_layout.addRow(self.save_btn)

        self.statusBar().showMessage("Готов")

    def _browse_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Выберите папку")
        if path:
            self.dir_edit.setText(path)

    def _load_settings_to_ui(self):
        self.port_spin.setValue(self.settings.port)
        self.dir_edit.setText(str(self.settings.upload_dir))
        self.size_spin.setValue(self.settings.max_file_size_mb)
        self.auto_check.setChecked(self.settings.auto_start)

    def _save_settings(self):
        self.settings.set("port", self.port_spin.value())
        new_dir = Path(self.dir_edit.text())
        if not new_dir.exists():
            new_dir.mkdir(parents=True, exist_ok=True)
        self.settings.set("upload_dir", str(new_dir))
        self.settings.set("max_file_size_mb", self.size_spin.value())
        self.settings.set("auto_start", self.auto_check.isChecked())

        if self.server.is_running():
            self.stop_server()
            for _ in range(10):
                if not self.server.is_running():
                    break
                time.sleep(0.5)
            self.server.update_settings(self.settings)
            self.start_server()
        else:
            self.server.update_settings(self.settings)

        self.port_label.setText(f"Порт: {self.settings.port}")
        self.statusBar().showMessage("Настройки сохранены", 3000)

    def start_server(self):
        if self.server.is_running():
            return
        self.settings.upload_dir.mkdir(parents=True, exist_ok=True)
        def _run():
            ok = self.server.start()
            self._update_ui_after_start(ok)
        threading.Thread(target=_run, daemon=True).start()

    def _update_ui_after_start(self, ok):
        if ok:
            self.status_label.setText("Запущен")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.statusBar().showMessage("Сервер запущен")
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            self._append_log(f"Сервер доступен по адресу: http://{ip}:{self.settings.port}")
        else:
            self.statusBar().showMessage("Ошибка запуска (порт занят?)", 3000)

    def stop_server(self):
        if not self.server.is_running():
            return
        self.server.stop()
        self._update_ui_after_stop()

    def _update_ui_after_stop(self):
        self.status_label.setText("Остановлен")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.statusBar().showMessage("Сервер остановлен")

    @Slot(str)
    def _append_log(self, msg):
        self.log_text.append(msg)
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

    def closeEvent(self, event):
        if self.server.is_running():
            self.stop_server()
        for timer in self.findChildren(QTimer):
            timer.stop()
        event.accept()