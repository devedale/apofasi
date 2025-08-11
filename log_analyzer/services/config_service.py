import yaml
from typing import Dict, Any, Optional

class ConfigService:
    """
    A service for loading from and saving to the YAML configuration file.
    """
    def __init__(self, config_path: str = '/app/config/config.yaml'):
        """
        Initializes the service with the path to the config file.

        Args:
            config_path: The path to the YAML configuration file.
        """
        self.config_path = config_path

    def load_config(self) -> Dict[str, Any]:
        """
        Loads the configuration from the YAML file.

        Returns:
            A dictionary representing the configuration. Returns an empty
            dictionary if the file is not found or an error occurs.
        """
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
                if not config:
                    print(f"CRITICAL ERROR: Config file at {self.config_path} is empty or invalid.")
                    return {}
                return config
        except FileNotFoundError:
            print(f"CRITICAL ERROR: Config file not found at {self.config_path}. The application cannot run without it.")
            # In a real app, this might raise an exception.
            return {}
        except yaml.YAMLError as e:
            print(f"CRITICAL ERROR: Could not parse YAML file at {self.config_path}. Error: {e}")
            return {}

    def save_config(self, config_data: Dict[str, Any]) -> bool:
        """
        Saves the provided configuration data to the YAML file.

        Args:
            config_data: The configuration dictionary to save.

        Returns:
            True if saving was successful, False otherwise.
        """
        try:
            with open(self.config_path, 'w') as f:
                yaml.dump(config_data, f, sort_keys=False, default_flow_style=False)
            return True
        except Exception as e:
            print(f"Error saving config file: {e}")
            return False

    def get_value(self, key_path: str, default: Any = None) -> Any:
        """
        Gets a value from the loaded config using a dot-separated path.

        Example: get_value('presidio.analyzer.confidence_threshold')
        """
        config = self.load_config()
        keys = key_path.split('.')
        value = config
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
