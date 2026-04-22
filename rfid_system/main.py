"""RFID System - Main entry point."""

import sys
import threading

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from backend.config import config
from backend.event_broker import broker
from backend.serial_handler import SerialHandler
from backend.data_manager import data_manager
from ui.main_window import MainWindow
from web.app import run_server


def main() -> int:
    """Main application entry point."""
    
    # Initialize Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("RFID Учёт меток")
    
    # Initialize serial handler
    serial_handler = SerialHandler(
        baudrate=config.serial_baudrate,
        timeout=config.serial_timeout,
        port_keywords=config.port_keywords
    )
    
    # Create main window
    window = MainWindow(serial_handler)
    window.show()
    
    # Start serial handler thread
    serial_handler.start()
    
    # Start FastAPI server in background thread
    def start_web_server():
        run_server(host=config.web_host, port=config.web_port)
    
    web_thread = threading.Thread(target=start_web_server, daemon=True)
    web_thread.start()
    
    # Schedule cleanup on exit
    def cleanup():
        serial_handler.stop()
    
    app.aboutToQuit.connect(cleanup)
    
    # Run Qt event loop
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
