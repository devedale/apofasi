"""
Servizio centralizzato per la gestione di tutte le regex e pattern di anonimizzazione.

DESIGN: Centralizza tutte le regex per garantire coerenza tra anonimizzazione,
pattern detection e template generation. Evita duplicazioni e inconsistenze.
"""

from typing import Dict, List, Tuple, Optional, Pattern, Any
import re
import yaml
from pathlib import Path
from abc import ABC, abstractmethod


class CentralizedRegexService(ABC):
    """Interfaccia astratta per il servizio regex centralizzato."""
    
    @abstractmethod
    def get_anonymization_patterns(self) -> Dict[str, Dict[str, str]]:
        """Restituisce tutti i pattern di anonimizzazione."""
        pass
    
    @abstractmethod
    def get_pattern_detection_patterns(self) -> Dict[str, Dict[str, str]]:
        """Restituisce tutti i pattern per la detection."""
        pass
    
    @abstractmethod
    def anonymize_content(self, content: str) -> str:
        """Anonimizza il contenuto usando i pattern centralizzati."""
        pass
    
    @abstractmethod
    def detect_patterns(self, content: str) -> Dict[str, List[str]]:
        """Rileva pattern nel contenuto usando le regex centralizzate."""
        pass
    
    @abstractmethod
    def get_template_from_content(self, content: str, anonymized: bool = False) -> str:
        """Genera un template dal contenuto, opzionalmente anonimizzato."""
        pass


class CentralizedRegexServiceImpl(CentralizedRegexService):
    """Implementazione del servizio regex centralizzato."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Inizializza il servizio con la configurazione.
        
        Args:
            config: Configurazione contenente le regex centralizzate
        """
        self._config = config
        self._anonymization_patterns = {}
        self._detection_patterns = {}
        self._compiled_anonymization = {}
        self._compiled_detection = {}
        
        # Carica configurazione da file YAML se disponibile
        self._load_configuration()
        
        # Compila i pattern
        self._compiled_anonymization = self._compile_anonymization_patterns()
        self._compiled_detection = self._compile_detection_patterns()
    
    def _load_configuration(self):
        """Carica la configurazione da file YAML o usa i default."""
        config_file = self._config.get("centralized_regex", {}).get("config_file", "config/centralized_regex.yaml")
        
        try:
            if Path(config_file).exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    yaml_config = yaml.safe_load(f)
                    self._anonymization_patterns = yaml_config.get("anonymization", {}).get("patterns", {})
                    self._detection_patterns = yaml_config.get("pattern_detection", {}).get("patterns", {})
                print(f"✅ Configurazione regex caricata da {config_file}")
            else:
                print(f"⚠️ File configurazione {config_file} non trovato, uso pattern di default")
                self._load_default_patterns()
        except Exception as e:
            print(f"⚠️ Errore caricamento configurazione: {e}, uso pattern di default")
            self._load_default_patterns()
    
    def _load_default_patterns(self):
        """Carica i pattern di default se la configurazione non è disponibile."""
        self._anonymization_patterns = {
            "ip_address": {
                "regex": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
                "replacement": "<IP>",
                "description": "Indirizzi IPv4"
            },
            "mac_address": {
                "regex": r"([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})",
                "replacement": "<MAC>",
                "description": "Indirizzi MAC"
            },
            "fortinet_device_id": {
                "regex": r"FGT[0-9A-Z]{8,}",
                "replacement": "<FORTINET_DEVICE>",
                "description": "ID dispositivi Fortinet"
            },
            "device_name": {
                "regex": r'devname="([^"]+)"',
                "replacement": 'devname="<DEVICE_NAME>"',
                "description": "Nomi dispositivi"
            },
            "hostname": {
                "regex": r'hostname="([^"]+)"',
                "replacement": 'hostname="<HOSTNAME>"',
                "description": "Hostname"
            }
        }
        
        self._detection_patterns = {
            "ip_address": {
                "regex": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
                "description": "Indirizzi IPv4"
            },
            "mac_address": {
                "regex": r"([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})",
                "description": "Indirizzi MAC"
            },
            "unix_timestamp": {
                "regex": r"\b\d{10,19}\b",
                "description": "Timestamp Unix"
            }
        }
    
    def _compile_anonymization_patterns(self) -> Dict[str, Pattern]:
        """Compila i pattern di anonimizzazione."""
        compiled = {}
        for name, pattern_info in self._anonymization_patterns.items():
            try:
                compiled[name] = re.compile(pattern_info["regex"])
            except re.error as e:
                print(f"Warning: Invalid regex for {name}: {e}")
        return compiled
    
    def _compile_detection_patterns(self) -> Dict[str, Pattern]:
        """Compila i pattern per la detection."""
        compiled = {}
        for name, pattern_info in self._detection_patterns.items():
            try:
                compiled[name] = re.compile(pattern_info["regex"])
            except re.error as e:
                print(f"Warning: Invalid regex for {name}: {e}")
        return compiled
    
    def get_anonymization_patterns(self) -> Dict[str, Dict[str, str]]:
        """Restituisce tutti i pattern di anonimizzazione."""
        return self._anonymization_patterns.copy()
    
    def get_pattern_detection_patterns(self) -> Dict[str, Dict[str, str]]:
        """Restituisce tutti i pattern per la detection."""
        return self._detection_patterns.copy()
    
    def anonymize_content(self, content: str) -> str:
        """
        Anonimizza il contenuto usando i pattern centralizzati.
        
        Args:
            content: Contenuto da anonimizzare
            
        Returns:
            Contenuto anonimizzato
        """
        anonymized_content = content
        
        # Applica i pattern in ordine di specificità (più specifici prima)
        for name, pattern in self._compiled_anonymization.items():
            pattern_info = self._anonymization_patterns[name]
            replacement = pattern_info["replacement"]
            
            if name in ["device_name", "hostname", "username", "session_id", "log_id", "port_number", "version"]:
                # Pattern con gruppi di cattura
                anonymized_content = pattern.sub(replacement, anonymized_content)
            else:
                # Pattern semplici
                anonymized_content = pattern.sub(replacement, anonymized_content)
        
        return anonymized_content
    
    def detect_patterns(self, content: str) -> Dict[str, List[str]]:
        """
        Rileva pattern nel contenuto usando le regex centralizzate.
        
        Args:
            content: Contenuto da analizzare
            
        Returns:
            Dizionario con pattern rilevati
        """
        detected_patterns = {}
        
        for name, pattern in self._compiled_detection.items():
            matches = pattern.findall(content)
            if matches:
                # Rimuovi duplicati mantenendo l'ordine
                unique_matches = list(dict.fromkeys(matches))
                detected_patterns[name] = unique_matches
        
        return detected_patterns
    
    def get_template_from_content(self, content: str, anonymized: bool = False) -> str:
        """
        Genera un template dal contenuto, opzionalmente anonimizzato.
        
        DESIGN: Se anonimizzato=True, preserva i placeholder di anonimizzazione
        prima di applicare i pattern generici per evitare perdita di coerenza.
        """
        if anonymized:
            # Usa il contenuto anonimizzato per il template
            template_content = self.anonymize_content(content)
        else:
            # Usa il contenuto originale
            template_content = content
        
        # Sostituisci valori specifici con placeholder generici
        template = template_content
        
        # IMPORTANTE: Se il contenuto è anonimizzato, preserva i placeholder specifici
        if anonymized:
            # Sostituisci solo i valori che NON sono già placeholder di anonimizzazione
            # Numeri che non sono parte di placeholder esistenti
            template = re.sub(r'\b(?<!<)(?<!>)\d+(?!>)\b', '<NUM>', template)
            
            # Stringhe tra virgolette che non sono già placeholder
            template = re.sub(r'"([^"]*)"', lambda m: f'"{m.group(1)}"' if any(ph in m.group(1) for ph in ['<IP>', '<MAC>', '<FORTINET_DEVICE>', '<DEVICE_NAME>', '<HOSTNAME>', '<USERNAME>', '<SESSION_ID>', '<LOG_ID>', '<UNIX_TIMESTAMP>', '<SEQ_NUM>', '<PORT>', '<VERSION>']) else '"<STR>"', template)
            
            # Timestamp che non sono già placeholder
            template = re.sub(r'\b(?<!<)(?<!>)\d{4}-\d{2}-\d{2}(?!>)\b', '<DATE>', template)
            template = re.sub(r'\b(?<!<)(?<!>)\d{2}:\d{2}:\d{2}(?!>)\b', '<TIME>', template)
        else:
            # Per contenuto non anonimizzato, applica tutti i pattern generici
            template = re.sub(r'\b\d+\b', '<NUM>', template)
            template = re.sub(r'"([^"]*)"', '"<STR>"', template)
            template = re.sub(r'\d{4}-\d{2}-\d{2}', '<DATE>', template)
            template = re.sub(r'\d{2}:\d{2}:\d{2}', '<TIME>', template)
        
        return template
