from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QDialogButtonBox, QCheckBox, QDoubleSpinBox
)
from ..services.config_service import ConfigService

class ConfigDialog(QDialog):
    """A dialog for viewing and editing the application configuration."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Configuration")
        self.config_service = ConfigService()
        self.config_data = self.config_service.load_config()

        # --- Layouts ---
        self.layout = QVBoxLayout(self)
        self.form_layout = QFormLayout()

        # --- Widgets for editing config values ---
        # I'll add a few examples as a proof of concept.

        # Presidio settings
        self.presidio_enabled_checkbox = QCheckBox()
        self.presidio_enabled_checkbox.setChecked(self.config_data.get('presidio', {}).get('enabled', False))
        self.form_layout.addRow("Enable Presidio:", self.presidio_enabled_checkbox)

        self.presidio_confidence_spinbox = QDoubleSpinBox()
        self.presidio_confidence_spinbox.setRange(0.0, 1.0)
        self.presidio_confidence_spinbox.setSingleStep(0.1)
        self.presidio_confidence_spinbox.setValue(self.config_data.get('presidio', {}).get('analyzer', {}).get('analysis', {}).get('confidence_threshold', 0.7))
        self.form_layout.addRow("Presidio Confidence Threshold:", self.presidio_confidence_spinbox)

        # Drain3 settings
        self.drain3_sim_threshold_spinbox = QDoubleSpinBox()
        self.drain3_sim_threshold_spinbox.setRange(0.0, 1.0)
        self.drain3_sim_threshold_spinbox.setSingleStep(0.1)
        self.drain3_sim_threshold_spinbox.setValue(self.config_data.get('drain3', {}).get('original', {}).get('similarity_threshold', 0.4))
        self.form_layout.addRow("Drain3 Similarity Threshold:", self.drain3_sim_threshold_spinbox)

        self.layout.addLayout(self.form_layout)

        # --- Dialog Buttons (Save/Cancel) ---
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def accept(self):
        """Saves the configuration when the Save button is clicked."""
        # Update the dictionary with values from the widgets
        self.config_data['presidio']['enabled'] = self.presidio_enabled_checkbox.isChecked()
        self.config_data['presidio']['analyzer']['analysis']['confidence_threshold'] = self.presidio_confidence_spinbox.value()
        self.config_data['drain3']['original']['similarity_threshold'] = self.drain3_sim_threshold_spinbox.value()

        # Save the updated dictionary back to the file
        if self.config_service.save_config(self.config_data):
            print("Configuration saved successfully.")
            super().accept()
        else:
            # Optionally, show an error message to the user
            print("Error: Could not save configuration.")
            # We might not want to close the dialog on failure
            # For now, we let it close.
            super().accept()
