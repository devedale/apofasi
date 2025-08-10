"""Regex-based anonymizer implementation."""

import hashlib
import re
from typing import Any, Dict, Optional

from ..domain.interfaces.anonymizer import Anonymizer
from ..domain.entities.parsed_record import ParsedRecord
from ..core.services.regex_service import RegexService


class RegexAnonymizer(Anonymizer):
    """Regex-based implementation of anonymizer."""
    
    def __init__(self, config: Dict[str, Any], regex_service: Optional[RegexService] = None) -> None:
        """
        Initialize the regex anonymizer.
        
        Args:
            config: Configuration dictionary
        """
        self._config = config
        self._regex_service = regex_service or RegexService(config)
        self._regex_patterns = self._load_regex_patterns()
        self._anonymization_config = self._load_anonymization_config()
    
    def anonymize_record(self, record: ParsedRecord) -> ParsedRecord:
        """
        Anonimizza il record creando anonymized_message e anonymized_parsed_data.
        
        WHY: Crea una versione anonimizzata completa del record per il processing Drain3
        e per i report che richiedono dati anonimizzati.
        """
        # 1. Crea il messaggio completo anonimizzato
        if hasattr(record, 'original_content') and record.original_content:
            record.anonymized_message = self.anonymize_text(record.original_content)
        
        # 2. Anonimizza i parsed_data se presenti
        if hasattr(record, 'parsed_data') and record.parsed_data:
            anonymized_parsed_data = {}
            for key, value in record.parsed_data.items():
                if isinstance(value, str):
                    anonymized_parsed_data[key] = self.anonymize_text(value)
                elif isinstance(value, dict):
                    # Anonimizza valori nei dizionari annidati
                    anonymized_parsed_data[key] = self._anonymize_dict(value)
                else:
                    anonymized_parsed_data[key] = value
            
            record.parsed_data_anonymized = anonymized_parsed_data
        
        return record
    
    def anonymize_field(self, field_name: str, field_value: Any) -> Any:
        """
        Anonymize a specific field value.
        
        Args:
            field_name: Name of the field
            field_value: Value to anonymize
            
        Returns:
            Anonymized value
        """
        if not isinstance(field_value, str):
            return field_value
        
        # Get anonymization method for this field
        method = self._anonymization_config.get_method_for_field(field_name)
        
        if method == "hash":
            return self._hash_value(field_value)
        elif method == "mask":
            return self._mask_value(field_value)
        elif method == "replace":
            replacement = self._anonymization_config.methods["replace"].get(field_name)
            return replacement if replacement else field_value
        else:
            # Apply regex patterns
            return self.anonymize_text(field_value)
    
    def anonymize_text(self, text: str) -> str:
        """
        Anonymize text content using regex patterns.
        
        Args:
            text: Text to anonymize
            
        Returns:
            Anonymized text
        """
        if not isinstance(text, str):
            return text
        
        # Usa RegexService centralizzato per applicare categoria anonymization
        return self._regex_service.apply_patterns_by_category(text, 'anonymization')
    
    @property
    def anonymization_methods(self) -> Dict[str, str]:
        """Get available anonymization methods."""
        return {
            "hash": "SHA256 hashing with salt",
            "mask": "Pattern masking",
            "replace": "Direct replacement",
            "regex": "Regex pattern matching",
        }
    
    @property
    def always_anonymize_fields(self) -> list[str]:
        """Get fields that should always be anonymized."""
        return self._anonymization_config.always_anonymize_fields
    
    def _load_regex_patterns(self) -> Dict[str, Dict[str, str]]:
        """Load regex patterns from configuration."""
        patterns = self._config.get("regex_patterns", {})
        
        # Convert string patterns to compiled patterns
        compiled_patterns = {}
        for pattern_name, pattern_config in patterns.items():
            if isinstance(pattern_config, dict) and "pattern" in pattern_config:
                compiled_patterns[pattern_name] = {
                    "pattern": pattern_config["pattern"],
                    "replacement": pattern_config.get("replacement", f"<{pattern_name.upper()}>")
                }
        
        return compiled_patterns
    
    def _load_anonymization_config(self) -> "AnonymizationConfig":
        """Load anonymization configuration."""
        from ..domain.entities.anonymization_config import AnonymizationConfig
        
        drain3_config = self._config.get("drain3", {})
        anonymization_config = drain3_config.get("anonymization", {})
        
        return AnonymizationConfig(
            enabled=anonymization_config.get("enabled", True),
            preserve_structure=anonymization_config.get("preserve_structure", True),
            always_anonymize_fields=anonymization_config.get("always_anonymize", []),
            methods=anonymization_config.get("methods", {}),
            regex_patterns=self._regex_patterns,
        )
    
    def _hash_value(self, value: str) -> str:
        """Hash a value using SHA256."""
        salt = self._anonymization_config.methods.get("hash", {}).get("salt", "clean_parser_salt_2024")
        return hashlib.sha256(f"{salt}{value}".encode()).hexdigest()[:16]
    
    def _mask_value(self, value: str) -> str:
        """Mask a value using configured pattern."""
        mask_pattern = self._anonymization_config.methods.get("mask", {}).get("pattern", "***")
        return mask_pattern 

    def _anonymize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Anonimizza ricorsivamente i valori in un dizionario."""
        anonymized = {}
        for key, value in data.items():
            if isinstance(value, str):
                anonymized[key] = self.anonymize_text(value)
            elif isinstance(value, dict):
                anonymized[key] = self._anonymize_dict(value)
            elif isinstance(value, list):
                anonymized[key] = [self.anonymize_text(v) if isinstance(v, str) else v for v in value]
            else:
                anonymized[key] = value
        return anonymized 