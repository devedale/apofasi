"""Regex-based anonymizer implementation."""

import hashlib
import re
from typing import Any, Dict, Optional

from ..domain.interfaces.anonymizer import Anonymizer
from ..domain.entities.parsed_record import ParsedRecord
from ..core.services.regex_service import RegexService
from ..domain.interfaces.centralized_regex_service import CentralizedRegexService


class RegexAnonymizer(Anonymizer):
    """Regex-based implementation of anonymizer."""
    
    def __init__(self, config: Dict[str, Any], centralized_regex_service: Optional[CentralizedRegexService] = None) -> None:
        """
        Inizializza l'anonymizer.
        
        Args:
            config: Configurazione del sistema
            centralized_regex_service: Servizio regex centralizzato per coerenza
        """
        self._config = config
        self._centralized_regex_service = centralized_regex_service
        
        # Carica configurazione anonimizzazione
        self._anonymization_config = self._load_anonymization_config()
        
        # Carica pattern regex per anonimizzazione
        self._regex_patterns = self._load_regex_patterns()
    
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
                # WHY: Applica anonimizzazione specifica per i campi configurati
                if key.lower() in [field.lower() for field in self._anonymization_config.always_anonymize_fields]:
                    anonymized_parsed_data[key] = self.anonymize_field(key, value)
                elif isinstance(value, str):
                    # WHY: Per gli altri campi stringa, applica solo pattern regex
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
        
        # WHY: Controlla se il campo deve essere anonimizzato sempre
        if field_name.lower() in [field.lower() for field in self._anonymization_config.always_anonymize_fields]:
            # Get anonymization method for this field
            method = self._anonymization_config.get_method_for_field(field_name)
            
            if method == "hash":
                return self._hash_value(field_value)
            elif method == "mask":
                return self._mask_value(field_value)
            elif method == "replace":
                replacement = self._anonymization_config.methods.get("replace", {}).get(field_name)
                return replacement if replacement else f"<{field_name.upper()}>"
            else:
                # Apply regex patterns
                return self.anonymize_text(field_value)
        
        # Se non è un campo da anonimizzare sempre, applica solo i pattern regex
        return self.anonymize_text(field_value)
    
    def anonymize_text(self, text: str) -> str:
        """
        Anonymize text content using regex patterns.
        
        Args:
            text: Text to anonymize
            
        Returns:
            Anonymized text
        """
        if not text:
            return text
        
        anonymized_text = text
        
        # 🚨 CORREZIONE: Applica PRIMA always_anonymize ai campi testuali
        # WHY: I campi in always_anonymize devono essere anonimizzati SEMPRE,
        # anche quando sono nel testo completo, non solo nei campi strutturati
        if self._anonymization_config and self._anonymization_config.always_anonymize_fields:
            for field_name in self._anonymization_config.always_anonymize_fields:
                # Crea pattern per trovare il campo nel testo (es: vd="root", tz="+0200")
                field_pattern = rf'{field_name}\s*=\s*"([^"]*)"'
                
                try:
                    # Cerca se il pattern matcha
                    matches = re.findall(field_pattern, anonymized_text, flags=re.IGNORECASE)
                    if matches:
                        # Sostituisci con il placeholder appropriato dal config
                        # WHY: Usa i placeholder definiti nel config per coerenza
                        if hasattr(self, '_centralized_regex_service') and self._centralized_regex_service:
                            # Usa il servizio centralizzato per ottenere il placeholder corretto
                            placeholder = self._centralized_regex_service.get_placeholder_for_field(field_name)
                        else:
                            # Fallback: usa il nome del campo in maiuscolo
                            placeholder = f"<{field_name.upper()}>"
                        
                        replacement = f'{field_name}="{placeholder}"'
                        anonymized_text = re.sub(field_pattern, replacement, anonymized_text, flags=re.IGNORECASE)
                        
                except re.error as e:
                    print(f"⚠️ Errore regex always_anonymize per '{field_name}': {e}")
        
        # WHY: Usa i pattern regex centralizzati se disponibili (DOPO always_anonymize)
        if self._centralized_regex_service:
            anonymization_patterns = self._centralized_regex_service.get_anonymization_patterns()
            for pattern_name, pattern_info in anonymization_patterns.items():
                if isinstance(pattern_info, dict) and "regex" in pattern_info:
                    pattern = pattern_info["regex"]
                    replacement = pattern_info.get("replacement", f"<{pattern_name.upper()}>")
                    try:
                        anonymized_text = re.sub(pattern, replacement, anonymized_text, flags=re.IGNORECASE)
                    except re.error as e:
                        print(f"⚠️ Errore regex pattern '{pattern_name}': {e}")
        else:
            # Fallback ai pattern locali
            for pattern_name, pattern_info in self._regex_patterns.items():
                if isinstance(pattern_info, dict) and "pattern" in pattern_info:
                    pattern = pattern_info["pattern"]
                    replacement = pattern_info.get("replacement", f"<{pattern_name.upper()}>")
                    try:
                        anonymized_text = re.sub(pattern, replacement, anonymized_text, flags=re.IGNORECASE)
                    except re.error as e:
                        print(f"⚠️ Errore regex pattern '{pattern_name}': {e}")
        
        return anonymized_text
    
    @property
    def anonymization_methods(self) -> Dict[str, str]:
        """Get available anonymization methods."""
        return self._anonymization_config.methods
    
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
        """Load anonymization configuration using centralized service."""
        from ..domain.entities.anonymization_config import AnonymizationConfig
        
        try:
            # WHY: Usa il servizio centralizzato se disponibile
            if self._centralized_regex_service:
                drain3_config = self._centralized_regex_service.get_drain3_config()
                anonymization_config = drain3_config.get("anonymization", {})
                anonymization_patterns = self._centralized_regex_service.get_anonymization_patterns()
                
                return AnonymizationConfig(
                    enabled=anonymization_config.get("enabled", True),
                    preserve_structure=anonymization_config.get("preserve_structure", True),
                    always_anonymize_fields=anonymization_config.get("always_anonymize", []),
                    methods=anonymization_config.get("methods", {}),
                    regex_patterns=anonymization_patterns,
                )
            else:
                # Fallback alla configurazione locale
                return self._load_default_anonymization_config()
                
        except Exception as e:
            print(f"❌ Errore nel caricamento della configurazione: {e}")
            print("📝 Usando configurazione di default...")
            return self._load_default_anonymization_config()
    
    def _load_default_anonymization_config(self) -> "AnonymizationConfig":
        """Load default anonymization configuration."""
        from ..domain.entities.anonymization_config import AnonymizationConfig
        
        return AnonymizationConfig(
            enabled=True,
            preserve_structure=True,
            always_anonymize_fields=[
                "ip_address", "user_id", "session_id", "device_id", 
                "mac_address", "email", "phone", "credit_card", "ssn"
            ],
            methods={},
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