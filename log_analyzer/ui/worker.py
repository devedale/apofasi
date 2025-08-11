from PyQt6.QtCore import QObject, pyqtSignal, QThread
from ..services.reporting_service import ReportingService

class Worker(QObject):
    """
    A worker object that runs a long-running task in a separate thread.
    This is essential to prevent the GUI from freezing during processing.
    """
    # Signals that can be emitted from this worker
    finished = pyqtSignal()
    progress = pyqtSignal(str)
    results_ready = pyqtSignal(list)

    def __init__(self, processing_service, input_path, output_path):
        super().__init__()
        self.processing_service = processing_service
        # The input path can be a single file or a list of files
        self.input_paths = [input_path] if isinstance(input_path, str) else input_path
        self.output_path = output_path

    def run(self):
        """
        The main work method. This is what will be executed in the new thread.
        """
        try:
            # For now, we don't have a way to get progress updates from the
            # backend service, so we'll just emit a starting message.
            self.progress.emit("Starting backend processing... this may take a while.")

            # Call the main processing method from the backend service
            processed_records = self.processing_service.process_files(self.input_paths)
            self.progress.emit(f"Processing complete. Found {len(processed_records)} records.")

            # Generate and save reports
            if processed_records:
                self.progress.emit("Generating reports...")
                reporting_service = ReportingService(self.output_path)
                reporting_service.generate_json_report(processed_records)
                reporting_service.generate_logppt_report(processed_records)
                self.progress.emit(f"Reports saved to {self.output_path}")

            # Emit the results back to the main thread for display
            self.results_ready.emit(processed_records)

        except Exception as e:
            self.progress.emit(f"An error occurred: {e}")

        finally:
            # Emit the finished signal regardless of success or failure
            self.finished.emit()
