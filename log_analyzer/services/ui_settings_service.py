import json
from typing import Dict, Any

class UISettingsService:
    """
    A service to manage saving and loading UI-specific settings,
    such as last used paths.
    """
    def __init__(self, settings_file: str = '.ui_settings.json'):
        self.settings_file = settings_file

    def load_settings(self) -> Dict[str, Any]:
        """
        Loads settings from the JSON file.

        Returns:
            A dictionary with the UI settings, or an empty dictionary if
            the file doesn't exist or is invalid.
        """
        try:
            with open(self.settings_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save_settings(self, settings_data: Dict[str, Any]):
        """
        Saves the provided settings dictionary to the JSON file.

        Args:
            settings_data: The dictionary of settings to save.
        """
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(settings_data, f, indent=2)
        except Exception as e:
            print(f"Error saving UI settings: {e}")
