"""Main window UI with PyQt6."""

import platform
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QFileDialog, QTableWidget, QTableWidgetItem,
    QMessageBox, QGroupBox, QFormLayout, QHeaderView, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QFont

from backend.config import config
from backend.data_manager import data_manager


class MainWindow(QMainWindow):
    """Main application window with dark theme."""
    
    def __init__(self, serial_handler):
        super().__init__()
        self.serial_handler = serial_handler
        self.current_uid: Optional[str] = None
        self.selected_photo_path: Optional[str] = None
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self) -> None:
        """Initialize the UI components."""
        self.setWindowTitle("RFID Учёт меток")
        self.setMinimumSize(900, 700)
        
        # Apply dark theme stylesheet
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QGroupBox {
                border: 2px solid #3c3c3c;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 10px;
                font-weight: bold;
                color: #e0e0e0;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
                color: #4CAF50;
            }
            QLabel {
                color: #e0e0e0;
            }
            QLineEdit {
                background-color: #2d2d2d;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                padding: 6px;
                color: #ffffff;
            }
            QLineEdit:read-only {
                background-color: #3a3a3a;
                color: #aaaaaa;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QTableWidget {
                background-color: #2d2d2d;
                alternate-background-color: #323232;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                gridline-color: #3c3c3c;
                color: #e0e0e0;
            }
            QTableWidget::item:selected {
                background-color: #4CAF50;
            }
            QHeaderView::section {
                background-color: #3c3c3c;
                color: #ffffff;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
            QStatusBar {
                background-color: #2d2d2d;
                color: #aaaaaa;
            }
        """)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(16, 16, 16, 16)
        
        # Top panel: Status and Photo
        top_panel = QHBoxLayout()
        top_panel.setSpacing(16)
        
        # Status label
        status_group = QGroupBox("Статус подключения")
        status_layout = QVBoxLayout(status_group)
        self.status_label = QLabel("🔍 Инициализация...")
        self.status_label.setFont(QFont("Segoe UI", 12))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_layout.addWidget(self.status_label)
        top_panel.addWidget(status_group, stretch=1)
        
        # Photo display
        photo_group = QGroupBox("Фото сотрудника")
        photo_layout = QVBoxLayout(photo_group)
        self.photo_label = QLabel()
        self.photo_label.setFixedSize(140, 140)
        self.photo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.photo_label.setStyleSheet("background-color: #2d2d2d; border-radius: 8px;")
        self.photo_label.setText("Нет фото")
        photo_layout.addWidget(self.photo_label)
        top_panel.addWidget(photo_group)
        
        main_layout.addLayout(top_panel)
        
        # Form for adding/updating entries
        form_group = QGroupBox("Добавление / Редактирование")
        form_layout = QFormLayout(form_group)
        form_layout.setSpacing(10)
        
        # UID field (readonly)
        self.uid_input = QLineEdit()
        self.uid_input.setReadOnly(True)
        self.uid_input.setPlaceholderText("Автоматически при сканировании")
        form_layout.addRow("UID:", self.uid_input)
        
        # FIO field
        self.fio_input = QLineEdit()
        self.fio_input.setPlaceholderText("Фамилия Имя Отчество")
        form_layout.addRow("ФИО:", self.fio_input)
        
        # Photo selection button
        photo_btn_layout = QHBoxLayout()
        self.photo_path_label = QLabel("Не выбрано")
        self.photo_path_label.setStyleSheet("color: #aaaaaa;")
        select_photo_btn = QPushButton("Выбрать фото")
        select_photo_btn.clicked.connect(self._select_photo)
        photo_btn_layout.addWidget(self.photo_path_label)
        photo_btn_layout.addWidget(select_photo_btn)
        form_layout.addRow("Фото:", photo_btn_layout)
        
        # Save button
        save_btn = QPushButton("Сохранить в реестр")
        save_btn.clicked.connect(self._save_entry)
        form_layout.addRow("", save_btn)
        
        main_layout.addWidget(form_group)
        
        # Scan history table
        table_group = QGroupBox("История сканирований")
        table_layout = QVBoxLayout(table_group)
        
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Время", "UID", "ФИО", "Статус"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table_layout.addWidget(self.table)
        
        main_layout.addWidget(table_group, stretch=1)
        
        # Status bar
        self.statusBar().showMessage("Готов к работе")
    
    def _connect_signals(self) -> None:
        """Connect signals from serial handler."""
        self.serial_handler.uid_received.connect(self.process_scan)
        self.serial_handler.status_changed.connect(self.update_status)
    
    def update_status(self, status: str) -> None:
        """Update connection status label."""
        self.status_label.setText(status)
        self.statusBar().showMessage(status)
    
    def process_scan(self, uid: str) -> None:
        """
        Process a scanned UID.
        
        Args:
            uid: RFID card UID in hex format
        """
        self.current_uid = uid
        self.uid_input.setText(uid)
        
        # Search in registry
        result = data_manager.find_uid(uid)
        
        if result:
            fio = result.get("fio", "Неизвестно")
            photo_name = result.get("photo")
            
            self.fio_input.setText(fio)
            status = f"✅ Известный: {fio}"
            
            # Load photo
            self._load_photo(photo_name)
            
            # Play success sound
            self._play_sound(True)
        else:
            self.fio_input.setText("")
            self._clear_photo()
            status = "❌ Неизвестная карта"
            
            # Play error sound
            self._play_sound(False)
        
        # Log scan
        fio_for_log = result.get("fio") if result else None
        data_manager.log_scan(uid, fio_for_log, status)
        
        # Update table
        self._add_table_row(uid, fio_for_log or "Неизвестно", status)
        
        self.statusBar().showMessage(status)
    
    def _load_photo(self, photo_name: Optional[str]) -> None:
        """Load and display photo from file."""
        if not photo_name:
            self._clear_photo()
            return
        
        photo_path = data_manager.get_photo_path(photo_name)
        if not photo_path:
            self._clear_photo()
            return
        
        try:
            pixmap = QPixmap(str(photo_path))
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    140, 140,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.photo_label.setPixmap(scaled)
                self.photo_label.setText("")
        except Exception as e:
            print(f"Error loading photo: {e}")
            self._clear_photo()
    
    def _clear_photo(self) -> None:
        """Clear photo display."""
        self.photo_label.clear()
        self.photo_label.setText("Нет фото")
    
    def _add_table_row(self, uid: str, fio: str, status: str) -> None:
        """Add a new row to the scan history table."""
        from datetime import datetime
        now = datetime.now()
        time_str = now.strftime("%H:%M:%S")
        
        row_position = self.table.rowCount()
        self.table.insertRow(row_position)
        
        self.table.setItem(row_position, 0, QTableWidgetItem(time_str))
        self.table.setItem(row_position, 1, QTableWidgetItem(uid.upper()))
        self.table.setItem(row_position, 2, QTableWidgetItem(fio))
        
        status_item = QTableWidgetItem(status)
        if status.startswith("✅"):
            status_item.setForeground(Qt.GlobalColor.darkGreen)
        else:
            status_item.setForeground(Qt.GlobalColor.red)
        self.table.setItem(row_position, 3, status_item)
        
        # Auto-scroll to bottom
        self.table.scrollToBottom()
        
        # Limit rows
        max_rows = config.max_log_rows
        while self.table.rowCount() > max_rows:
            self.table.removeRow(0)
    
    def _select_photo(self) -> None:
        """Open file dialog to select a photo."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите фото",
            "",
            "Images (*.jpg *.jpeg *.png *.gif *.bmp)"
        )
        
        if file_path:
            self.selected_photo_path = file_path
            self.photo_path_label.setText(Path(file_path).name)
    
    def _save_entry(self) -> None:
        """Save or update entry in registry."""
        if not self.current_uid:
            QMessageBox.warning(self, "Ошибка", "Сначала отсканируйте карту")
            return
        
        fio = self.fio_input.text().strip()
        if not fio:
            QMessageBox.warning(self, "Ошибка", "Введите ФИО")
            return
        
        success = data_manager.add_or_update(
            self.current_uid,
            fio,
            self.selected_photo_path
        )
        
        if success:
            QMessageBox.information(
                self,
                "Успех",
                f"Запись для {fio} сохранена в реестр"
            )
            # Clear form
            self.selected_photo_path = None
            self.photo_path_label.setText("Не выбрано")
            self.fio_input.clear()
        else:
            QMessageBox.critical(
                self,
                "Ошибка",
                "Не удалось сохранить запись. Возможно, файл открыт в Excel."
            )
    
    def _play_sound(self, success: bool) -> None:
        """Play sound based on scan result."""
        if not config.sounds_enable:
            return
        
        try:
            if platform.system() == "Windows":
                import winsound
                sound_file = config.sound_ok if success else config.sound_err
                sound_path = Path(sound_file)
                if sound_path.exists():
                    winsound.PlaySound(str(sound_path), winsound.SND_FILENAME)
                else:
                    # Fallback beep
                    winsound.Beep(1000 if success else 500, 200)
            # On Linux/macOS, just pass (no built-in simple sound API)
        except Exception as e:
            print(f"Sound error: {e}")
    
    def closeEvent(self, event) -> None:
        """Handle window close event."""
        self.serial_handler.stop()
        event.accept()
