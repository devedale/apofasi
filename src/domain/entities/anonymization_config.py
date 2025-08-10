"""Anonymization configuration domain entity."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class AnonymizationConfig:
    """Domain entity for anonymization configuration."""
    
    enabled: bool = True
    preserve_structure: bool = True
    always_anonymize_fields: List[str] = None
    methods: Dict[str, Any] = None
    regex_patterns: Dict[str, Dict[str, str]] = None
    
    def __post_init__(self) -> None:
        """Initialize default values."""
        if self.always_anonymize_fields is None:
            self.always_anonymize_fields = [
                "ip_address",
                "user_id", 
                "session_id",
                "device_id",
                "mac_address",
                "email",
                "phone",
                "credit_card",
                "ssn",
            ]
        
        if self.methods is None:
            self.methods = {
                "hash": {
                    "algorithm": "sha256",
                    "salt": "clean_parser_salt_2024",
                    "fields": ["user_id", "session_id", "device_id"]
                },
                "mask": {
                    "pattern": "***",
                    "fields": ["credit_card", "ssn", "phone"]
                },
                "replace": {
                    "ip_address": "<IP>",
                    "mac_address": "<MAC>",
                    "email": "<EMAIL>",
                    "timestamp": "<TIMESTAMP>",
                    "date": "<DATE>",
                    "time": "<TIME>",
                    "version": "<VERSION>",
                    "sequence": "<SEQ_NUM>",
                    "number": "<NUM>",
                    "path": "<PATH>",
                    "url": "<URL>",
                }
            }
        
        if self.regex_patterns is None:
            self.regex_patterns = {
                "ip_address": {
                    "pattern": r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b',
                    "replacement": "<IP>"
                },
                "mac_address": {
                    "pattern": r'\b([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})\b',
                    "replacement": "<MAC>"
                },
                "email": {
                    "pattern": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                    "replacement": "<EMAIL>"
                },
                "credit_card": {
                    "pattern": r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',
                    "replacement": "****-****-****-****"
                },
                "ssn": {
                    "pattern": r'\b\d{3}-\d{2}-\d{4}\b',
                    "replacement": "***-**-****"
                },
                "phone": {
                    "pattern": r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
                    "replacement": "***-***-****"
                },
                "timestamp": {
                    "pattern": r'\b\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?\b',
                    "replacement": "<TIMESTAMP>"
                },
                "date": {
                    "pattern": r'\b\d{4}-\d{2}-\d{2}\b',
                    "replacement": "<DATE>"
                },
                "time": {
                    "pattern": r'\b\d{2}:\d{2}:\d{2}\b',
                    "replacement": "<TIME>"
                },
                "version": {
                    "pattern": r'\b(?:v?)?\d+\.\d+(?:\.\d+)?(?:-[a-zA-Z0-9]+)?\b',
                    "replacement": "<VERSION>"
                },
                "sequence": {
                    "pattern": r'\b\d{10,}\b',
                    "replacement": "<SEQ_NUM>"
                },
                "number": {
                    "pattern": r'\b\d+\b',
                    "replacement": "<NUM>"
                },
                "path": {
                    "pattern": r'[\\\/][^\\\/\s]+(?:[\\\/][^\\\/\s]+)*',
                    "replacement": "<PATH>"
                },
                "url": {
                    "pattern": r'https?://[^\s]+',
                    "replacement": "<URL>"
                },
            }
    
    def get_method_for_field(self, field_name: str) -> Optional[str]:
        """
        Get the anonymization method for a specific field.
        
        Args:
            field_name: Name of the field
            
        Returns:
            Method name or None if not configured
        """
        for method_name, method_config in self.methods.items():
            if isinstance(method_config, dict) and "fields" in method_config:
                if field_name in method_config["fields"]:
                    return method_name
        return None
    
    def get_regex_pattern(self, pattern_name: str) -> Optional[Dict[str, str]]:
        """
        Get regex pattern configuration.
        
        Args:
            pattern_name: Name of the pattern
            
        Returns:
            Pattern configuration or None if not found
        """
        return self.regex_patterns.get(pattern_name)
    
    def should_anonymize_field(self, field_name: str) -> bool:
        """
        Check if a field should be anonymized.
        
        Args:
            field_name: Name of the field
            
        Returns:
            True if field should be anonymized
        """
        return field_name in self.always_anonymize_fields
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "enabled": self.enabled,
            "preserve_structure": self.preserve_structure,
            "always_anonymize_fields": self.always_anonymize_fields,
            "methods": self.methods,
            "regex_patterns": self.regex_patterns,
        } 