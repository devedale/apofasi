"""Configuration loader implementation."""

import yaml
import configparser
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigLoader:
    """Configuration loader for the application."""
    
    def __init__(self) -> None:
        """Initialize the config loader."""
        self._default_config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
    
    def load_config(self, config_path: Optional[Path] = None) -> Dict[str, Any]:
        """
        Load configuration from file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Configuration dictionary
        """
        if config_path is None:
            config_path = self._default_config_path
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        # Determina il formato del file dall'estensione
        if config_path.suffix.lower() in ['.ini', '.cfg']:
            return self._load_ini_config(config_path)
        elif config_path.suffix.lower() in ['.yaml', '.yml']:
            return self._load_yaml_config(config_path)
        else:
            # Prova prima INI, poi YAML
            try:
                return self._load_ini_config(config_path)
            except:
                try:
                    return self._load_yaml_config(config_path)
                except Exception as e:
                    raise ValueError(f"Impossibile caricare il file di configurazione {config_path}: formato non supportato. Errore: {e}")
    
    def _load_ini_config(self, config_path: Path) -> Dict[str, Any]:
        """
        Carica configurazione da file INI.
        
        Args:
            config_path: Percorso del file INI
            
        Returns:
            Dizionario di configurazione
        """
        config = configparser.ConfigParser()
        config.read(config_path, encoding='utf-8')
        
        # Converti ConfigParser in dizionario
        config_dict = {}
        for section in config.sections():
            config_dict[section] = {}
            for key, value in config.items(section):
                # Prova a convertire i valori in tipi Python appropriati
                config_dict[section][key] = self._convert_ini_value(value)
        
        # Gestisci strutture nidificate per sezioni specifiche
        config_dict = self._process_nested_sections(config_dict)
        
        return config_dict
    
    def _process_nested_sections(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa sezioni nidificate nella configurazione INI.
        
        Args:
            config_dict: Dizionario di configurazione
            
        Returns:
            Dizionario con strutture nidificate processate
        """
        # Sezioni che devono essere processate come dizionari
        nested_sections = ['supported_formats', 'parser_priorities', 'parser_mapping']
        
        for section_name, section_data in config_dict.items():
            if isinstance(section_data, dict):
                for key, value in section_data.items():
                    if key in nested_sections and isinstance(value, str):
                        # Prova a parsare come dizionario
                        try:
                            # Rimuovi spazi extra e dividi per righe
                            lines = [line.strip() for line in value.split('\n') if line.strip()]
                            parsed_dict = {}
                            
                            for line in lines:
                                if ':' in line:
                                    k, v = line.split(':', 1)
                                    k = k.strip()
                                    v = v.strip().strip('"\'')  # Rimuovi quote
                                    parsed_dict[k] = v
                            
                            if parsed_dict:
                                config_dict[section_name][key] = parsed_dict
                        except:
                            # Se non riesce a parsare, mantieni come stringa
                            pass
        
        return config_dict
    
    def _load_yaml_config(self, config_path: Path) -> Dict[str, Any]:
        """
        Carica configurazione da file YAML.
        
        Args:
            config_path: Percorso del file YAML
            
        Returns:
            Dizionario di configurazione
        """
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    
    def _convert_ini_value(self, value: str) -> Any:
        """
        Converte un valore stringa INI nel tipo Python appropriato.
        
        Args:
            value: Valore stringa da convertire
            
        Returns:
            Valore convertito
        """
        # Rimuovi spazi extra
        value = value.strip()
        
        # Prova a convertire in boolean
        if value.lower() in ['true', 'yes', 'on', '1']:
            return True
        elif value.lower() in ['false', 'no', 'off', '0']:
            return False
        
        # Prova a convertire in intero
        try:
            return int(value)
        except ValueError:
            pass
        
        # Prova a convertire in float
        try:
            return float(value)
        except ValueError:
            pass
        
        # Mantieni come stringa se non è possibile convertire
        return value
    
    def load_default_config(self) -> Dict[str, Any]:
        """
        Load default configuration.
        
        Returns:
            Default configuration dictionary
        """
        return self.load_config(self._default_config_path)
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate configuration structure.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            True if configuration is valid
        """
        # Sezioni richieste per la nuova configurazione
        required_sections = ["centralized_regex", "drain3"]
        
        for section in required_sections:
            if section not in config:
                return False
        
        return True
    
    def get_parser_config(self, config: Dict[str, Any], parser_name: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific parser.
        
        Args:
            config: Configuration dictionary
            parser_name: Name of the parser
            
        Returns:
            Parser configuration or None if not found
        """
        parsers_config = config.get("parsers", {})
        return parsers_config.get(parser_name)
    
    def get_drain3_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get Drain3 configuration.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Drain3 configuration dictionary
        """
        return config.get("drain3", {})
    
    def get_regex_patterns(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get regex patterns configuration.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Regex patterns configuration dictionary
        """
        return config.get("regex_patterns", {}) 