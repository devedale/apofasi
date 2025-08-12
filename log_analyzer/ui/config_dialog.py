from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton,
    QDialogButtonBox, QCheckBox, QDoubleSpinBox, QTabWidget, QWidget,
    QTableWidget, QTableWidgetItem, QHBoxLayout, QComboBox, QGroupBox
)
from ..services.config_service import ConfigService

class ConfigDialog(QDialog):
    """A dialog for viewing and editing the application configuration."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Configuration")
        self.setMinimumSize(700, 500)
        self.config_service = ConfigService()
        self.config_data = self.config_service.load_config()

        # --- Main Layout and Tab Widget ---
        self.layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)

        # --- Create Tabs ---
        self.create_core_settings_tab()
        self.create_regex_editor_tab()
        self.create_entities_tab()

        # --- Dialog Buttons (Save/Cancel) ---
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def create_core_settings_tab(self):
        """Creates the tab for editing core settings."""
        tab = QWidget()
        layout = QFormLayout(tab)

        # Presidio settings
        self.presidio_enabled_checkbox = QCheckBox()
        self.presidio_enabled_checkbox.setChecked(self.config_data.get('presidio', {}).get('enabled', False))
        layout.addRow("Enable Presidio:", self.presidio_enabled_checkbox)

        self.presidio_confidence_spinbox = QDoubleSpinBox()
        self.presidio_confidence_spinbox.setRange(0.0, 1.0)
        self.presidio_confidence_spinbox.setSingleStep(0.1)
        self.presidio_confidence_spinbox.setValue(self.config_data.get('presidio', {}).get('analyzer', {}).get('analysis', {}).get('confidence_threshold', 0.7))
        layout.addRow("Presidio Confidence Threshold:", self.presidio_confidence_spinbox)

        # Drain3 settings
        self.drain3_sim_threshold_spinbox = QDoubleSpinBox()
        self.drain3_sim_threshold_spinbox.setRange(0.0, 1.0)
        self.drain3_sim_threshold_spinbox.setSingleStep(0.1)
        self.drain3_sim_threshold_spinbox.setValue(self.config_data.get('drain3', {}).get('original', {}).get('similarity_threshold', 0.4))
        layout.addRow("Drain3 Similarity Threshold:", self.drain3_sim_threshold_spinbox)

        self.tabs.addTab(tab, "Core Settings")

    def create_regex_editor_tab(self):
        """Creates the tab for managing custom Presidio regex recognizers."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Table to display recognizers
        self.regex_table = QTableWidget()
        self.regex_table.setColumnCount(3)
        self.regex_table.setHorizontalHeaderLabels(["Name", "Regex Pattern", "Score"])
        self.populate_regex_table()
        layout.addWidget(self.regex_table)

        # Buttons for managing recognizers
        button_layout = QHBoxLayout()
        add_button = QPushButton("Add")
        edit_button = QPushButton("Edit")
        delete_button = QPushButton("Delete")

        # TODO: Connect buttons to handler methods
        # add_button.clicked.connect(self.add_regex)
        # edit_button.clicked.connect(self.edit_regex)
        # delete_button.clicked.connect(self.delete_regex)

        button_layout.addWidget(add_button)
        button_layout.addWidget(edit_button)
        button_layout.addWidget(delete_button)
        layout.addLayout(button_layout)

        # --- Live Preview Section ---
        preview_group = QGroupBox("Live Preview")
        preview_layout = QFormLayout(preview_group)

        self.sample_text_input = QLineEdit()
        self.sample_text_input.setPlaceholderText("Enter sample text here...")
        preview_layout.addRow("Sample Text:", self.sample_text_input)

        self.preview_output_area = QLineEdit()
        self.preview_output_area.setReadOnly(True)
        preview_layout.addRow("Anonymized:", self.preview_output_area)

        preview_button = QPushButton("Preview Changes")
        preview_button.clicked.connect(self.update_preview)
        preview_layout.addWidget(preview_button)

        layout.addWidget(preview_group)

        self.tabs.addTab(tab, "Custom Regex Recognizers")

    def create_entities_tab(self):
        """Creates the tab for managing Presidio entities and strategies."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.entities_table = QTableWidget()
        self.entities_table.setColumnCount(3)
        self.entities_table.setHorizontalHeaderLabels(["Entity", "Enabled", "Strategy"])
        self.populate_entities_table()
        layout.addWidget(self.entities_table)

        self.tabs.addTab(tab, "Entities & Strategies")

    def populate_entities_table(self):
        """Fills the entities table with data from the config."""
        entities = self.config_data.get('presidio', {}).get('analyzer', {}).get('entities', {})
        strategies = self.config_data.get('presidio', {}).get('anonymizer', {}).get('strategies', {})

        # We assume the entities list in the config is the source of truth
        entity_names = sorted(entities.keys())
        self.entities_table.setRowCount(len(entity_names))

        for row, entity_name in enumerate(entity_names):
            # Column 0: Entity Name (read-only)
            name_item = QTableWidgetItem(entity_name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.entities_table.setItem(row, 0, name_item)

            # Column 1: Enabled Checkbox
            checkbox = QCheckBox()
            checkbox.setChecked(entities.get(entity_name, False))
            self.entities_table.setCellWidget(row, 1, checkbox)

            # Column 2: Strategy ComboBox
            combo_box = QComboBox()
            combo_box.addItems(["replace", "mask", "hash", "keep"])
            current_strategy = strategies.get(entity_name, "replace")
            combo_box.setCurrentText(current_strategy)
            self.entities_table.setCellWidget(row, 2, combo_box)

    def populate_regex_table(self):
        """Fills the regex table with data from the config."""
        # I'm assuming a structure for ad-hoc recognizers.
        # This may need to be added to the default config.yaml
        recognizers = self.config_data.get('presidio', {}).get('analyzer', {}).get('ad_hoc_recognizers', [])
        self.regex_table.setRowCount(len(recognizers))

        for row, recognizer in enumerate(recognizers):
            self.regex_table.setItem(row, 0, QTableWidgetItem(recognizer.get("name", "")))
            self.regex_table.setItem(row, 1, QTableWidgetItem(recognizer.get("regex", "")))
            self.regex_table.setItem(row, 2, QTableWidgetItem(str(recognizer.get("score", ""))))

    def accept(self):
        """Saves the configuration when the Save button is clicked."""
        # --- Gather data from all tabs before saving ---

        # Core Settings Tab
        if self.config_data.get('presidio'):
            self.config_data['presidio']['enabled'] = self.presidio_enabled_checkbox.isChecked()
            if self.config_data['presidio'].get('analyzer', {}).get('analysis'):
                self.config_data['presidio']['analyzer']['analysis']['confidence_threshold'] = self.presidio_confidence_spinbox.value()

        if self.config_data.get('drain3', {}).get('original'):
            self.config_data['drain3']['original']['similarity_threshold'] = self.drain3_sim_threshold_spinbox.value()

        # Regex Editor Tab
        recognizers = []
        for row in range(self.regex_table.rowCount()):
            name = self.regex_table.item(row, 0).text()
            regex = self.regex_table.item(row, 1).text()
            score = float(self.regex_table.item(row, 2).text() or 0.0)
            recognizers.append({"name": name, "regex": regex, "score": score})

        if not self.config_data.get('presidio'):
            self.config_data['presidio'] = {}
        if not self.config_data['presidio'].get('analyzer'):
            self.config_data['presidio']['analyzer'] = {}
        self.config_data['presidio']['analyzer']['ad_hoc_recognizers'] = recognizers

        # Entities & Strategies Tab
        entities = {}
        strategies = {}
        for row in range(self.entities_table.rowCount()):
            entity_name = self.entities_table.item(row, 0).text()
            is_enabled = self.entities_table.cellWidget(row, 1).isChecked()
            strategy = self.entities_table.cellWidget(row, 2).currentText()
            entities[entity_name] = is_enabled
            strategies[entity_name] = strategy

        self.config_data['presidio']['analyzer']['entities'] = entities
        if not self.config_data['presidio'].get('anonymizer'):
            self.config_data['presidio']['anonymizer'] = {}
        self.config_data['presidio']['anonymizer']['strategies'] = strategies


        # Save the updated dictionary back to the file
        if self.config_service.save_config(self.config_data):
            print("Configuration saved successfully.")
            super().accept()
        else:
            # Optionally, show an error message to the user
            print("Error: Could not save configuration.")
            # For now, we let it close, but a real app might show a QMessageBox
            super().accept()

    def update_preview(self):
        """
        Updates the live preview area based on the current UI settings.
        This creates a temporary, in-memory Presidio engine to show the
        effects of the unsaved changes.
        """
        from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
        from presidio_analyzer.ad_hoc_recognizer import AdHocRecognizer
        from presidio_anonymizer import AnonymizerEngine

        sample_text = self.sample_text_input.text()
        if not sample_text:
            self.preview_output_area.setText("")
            return

        try:
            # 1. Create a temporary registry and analyzer engine
            registry = RecognizerRegistry()
            registry.load_predefined_recognizers()
            analyzer = AnalyzerEngine(registry=registry)
            anonymizer = AnonymizerEngine()

            # 2. Get the unsaved ad-hoc recognizers from the UI table
            for row in range(self.regex_table.rowCount()):
                name = self.regex_table.item(row, 0).text()
                regex = self.regex_table.item(row, 1).text()
                if name and regex:
                    ad_hoc_recognizer = AdHocRecognizer(supported_entity=name, patterns=[regex])
                    analyzer.registry.add_recognizer(ad_hoc_recognizer)

            # 3. Analyze and anonymize the sample text
            analyzer_results = analyzer.analyze(text=sample_text, language='en')
            anonymized_result = anonymizer.anonymize(
                text=sample_text,
                analyzer_results=analyzer_results
            )

            # 4. Display the result
            self.preview_output_area.setText(anonymized_result.text)

        except Exception as e:
            self.preview_output_area.setText(f"Error: {e}")
