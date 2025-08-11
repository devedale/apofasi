import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QTextEdit, QPushButton, QFileDialog, QStatusBar, QLabel
)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import QThread
from .config_dialog import ConfigDialog
from .worker import Worker
from ..services.config_service import ConfigService
from ..services.log_processing_service import LogProcessingService

class MainWindow(QMainWindow):
    """The main window for the Log Analyzer application."""

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Log Analyzer & Anonymizer")
        self.setGeometry(100, 100, 900, 700)  # x, y, width, height

        # --- Central Widget and Layout ---
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        # --- UI Widgets ---
        self.results_text_area = QTextEdit()
        self.results_text_area.setReadOnly(True)
        self.results_text_area.setPlaceholderText("Results will be shown here...")

        self.run_button = QPushButton("Run Pipeline")
        self.run_button.setEnabled(False) # Disabled until input is selected
        self.run_button.clicked.connect(self.run_pipeline)

        self.layout.addWidget(self.results_text_area)
        self.layout.addWidget(self.run_button)

        # --- Status Bar ---
        self.setStatusBar(QStatusBar(self))
        self.statusBar().showMessage("Ready. Please select a file or folder to analyze.")

        # --- Menu Bar and Actions ---
        self._create_actions()
        self._create_menu_bar()

        # --- Internal state ---
        self.input_path = None
        self.output_path = None

    def _create_actions(self):
        """Create the actions for the menu bar."""
        self.open_file_action = QAction("&Open File...", self)
        self.open_file_action.triggered.connect(self.select_file)

        self.open_folder_action = QAction("Open &Folder...", self)
        self.open_folder_action.triggered.connect(self.select_folder)

        self.set_output_folder_action = QAction("Set &Output Folder...", self)
        self.set_output_folder_action.triggered.connect(self.select_output_folder)

        self.exit_action = QAction("&Exit", self)
        self.exit_action.triggered.connect(self.close)

        self.configure_action = QAction("&Configure...", self)
        self.configure_action.triggered.connect(self.open_configuration)

    def _create_menu_bar(self):
        """Create the main menu bar."""
        menu_bar = self.menuBar()

        # File Menu
        file_menu = menu_bar.addMenu("&File")
        file_menu.addAction(self.open_file_action)
        file_menu.addAction(self.open_folder_action)
        file_menu.addAction(self.set_output_folder_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        # Edit Menu
        edit_menu = menu_bar.addMenu("&Edit")
        edit_menu.addAction(self.configure_action)

    def select_file(self):
        """Placeholder for file selection logic."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Log File")
        if file_path:
            self.input_path = file_path
            self.statusBar().showMessage(f"Input file set: {self.input_path}")
            self._check_paths_and_enable_run()

    def select_folder(self):
        """Placeholder for folder selection logic."""
        folder_path = QFileDialog.getExistingDirectory(self, "Open Log Folder")
        if folder_path:
            self.input_path = folder_path
            self.statusBar().showMessage(f"Input folder set: {self.input_path}")
            self._check_paths_and_enable_run()

    def select_output_folder(self):
        """Placeholder for output folder selection logic."""
        folder_path = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder_path:
            self.output_path = folder_path
            self.statusBar().showMessage(f"Output folder set: {self.output_path}")
            self._check_paths_and_enable_run()

    def _check_paths_and_enable_run(self):
        """Enables the run button if both input and output paths are set."""
        if self.input_path and self.output_path:
            self.run_button.setEnabled(True)
            self.statusBar().showMessage(f"Ready to run. Input: {self.input_path}, Output: {self.output_path}")

    def open_configuration(self):
        """Opens the configuration dialog."""
        dialog = ConfigDialog(self)
        if dialog.exec():
            self.statusBar().showMessage("Configuration saved.")
        else:
            self.statusBar().showMessage("Configuration changes canceled.")

    def run_pipeline(self):
        """
        Sets up the worker thread and starts the backend processing.
        """
        if not self.input_path or not self.output_path:
            self.statusBar().showMessage("Error: Input and Output paths must be set.")
            return

        self.run_button.setEnabled(False)
        self.results_text_area.clear()
        self.statusBar().showMessage("Starting processing...")

        # 1. Load config and create services
        config = ConfigService().load_config()
        processing_service = LogProcessingService(config)

        # 2. Create a QThread and a worker.
        self.thread = QThread()
        self.worker = Worker(processing_service, self.input_path, self.output_path)
        self.worker.moveToThread(self.thread)

        # 3. Connect signals and slots
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.progress.connect(self.update_status_bar)
        self.worker.results_ready.connect(self.display_results)

        # 4. Start the thread
        self.thread.start()
        self.thread.finished.connect(lambda: self.run_button.setEnabled(True))

    def update_status_bar(self, message: str):
        """Updates the status bar with a message from the worker."""
        self.statusBar().showMessage(message)

    def display_results(self, records: list):
        """Displays a summary of the results in the text area."""
        self.results_text_area.append(f"--- Processing Finished ---")
        self.results_text_area.append(f"Total records processed: {len(records)}\n")
        if records:
            import json
            # Display first 5 records as an example
            for i, record in enumerate(records[:5]):
                self.results_text_area.append(f"--- Record {i+1} ---")
                self.results_text_area.append(json.dumps(record.model_dump(), indent=2))
                self.results_text_area.append("\n")

# Example of how to run this window for testing
if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec())
