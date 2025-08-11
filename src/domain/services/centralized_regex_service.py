"""
Servizio centralizzato per la gestione di tutte le regex e pattern di anonimizzazione.

DESIGN: Centralizza tutte le regex per garantire coerenza tra anonimizzazione,
pattern detection e template generation. Evita duplicazioni e inconsistenze.

WHY: Ottimizzato per usare ConfigCache e evitare caricamenti ripetuti di YAML
durante il processing di grandi dataset.
"""

from typing import Dict, List, Tuple, Optional, Pattern, Any
import re
from abc import ABC, abstractmethod
from pathlib import Path
import yaml

# WHY: Importa ConfigCache per evitare caricamenti ripetuti di YAML
from ...core.services.config_cache import ConfigCache


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
    """Implementazione del servizio regex centralizzato ottimizzata."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Inizializza il servizio con la configurazione.
        
        Args:
            config: Configurazione contenente le regex centralizzate
        """
        self._config = config
        
        # WHY: Usa ConfigCache per evitare caricamenti ripetuti di YAML
        self._config_cache = ConfigCache()
        
        # Carica configurazione da cache invece che da file
        self._load_configuration_from_cache()
        
        # Compila i pattern
        self._compiled_anonymization = self._compile_anonymization_patterns()
        self._compiled_detection = self._compile_detection_patterns()
    
    def _load_configuration_from_cache(self) -> None:
        """
        Carica la configurazione regex dalla cache invece che dal file.
        
        WHY: Evita caricamenti ripetuti di YAML durante il processing
        di grandi dataset, riducendo il tempo da minuti a secondi.
        """
        try:
            # WHY: Usa la cache invece di ricaricare YAML
            regex_config = self._config_cache.get_config('centralized_regex')
            anonymization_config = regex_config.get('anonymization', {})
            parsing_config = regex_config.get('parsing', {})
            cleaning_config = regex_config.get('cleaning', {})
            
            # Converti i pattern da config.yaml nel formato atteso
            self._anonymization_patterns = {}
            for pattern_name, regex_pattern in anonymization_config.items():
                self._anonymization_patterns[pattern_name] = {
                    "regex": regex_pattern,
                    "replacement": f"<{pattern_name.upper()}>",
                    "description": f"Pattern per {pattern_name}"
                }
            
            # Carica pattern di parsing
            self._parsing_patterns = {}
            for pattern_name, regex_pattern in parsing_config.items():
                self._parsing_patterns[pattern_name] = {
                    "regex": regex_pattern,
                    "description": f"Pattern per parsing {pattern_name}"
                }
            
            # Carica pattern di cleaning
            self._cleaning_patterns = {}
            for pattern_name, regex_pattern in cleaning_config.items():
                self._cleaning_patterns[pattern_name] = {
                    "regex": regex_pattern,
                    "description": f"Pattern per cleaning {pattern_name}"
                }
            
            # Carica pattern di detection dalla cache se disponibili
            detection_config = regex_config.get("detection", {})
            if detection_config:
                self._detection_patterns = {}
                for pattern_name, regex_pattern in detection_config.items():
                    self._detection_patterns[pattern_name] = {
                        "regex": regex_pattern,
                        "description": f"Pattern per detection {pattern_name}"
                    }
            else:
                self._detection_patterns = self._get_default_detection_patterns()
            
            total_patterns = (len(self._anonymization_patterns) + 
                            len(self._parsing_patterns) + 
                            len(self._cleaning_patterns) + 
                            len(self._detection_patterns))
            
            print(f"✅ Configurazione regex caricata da cache: {total_patterns} pattern totali")
            
        except Exception as e:
            print(f"❌ Errore nel caricamento della configurazione dalla cache: {e}")
            print("📝 Usando configurazione di default...")
    
    def _load_configuration(self) -> None:
        """
        Metodo legacy mantenuto per compatibilità.
        
        WHY: Deprecato in favore di _load_configuration_from_cache.
        """
        print("⚠️ Metodo legacy _load_configuration chiamato, usando cache...")
        self._load_configuration_from_cache()
    
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
        
        self._detection_patterns = self._get_default_detection_patterns()
    
    def _get_default_detection_patterns(self):
        """Restituisce i pattern di detection di default."""
        return {
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
        return self._anonymization_patterns
    
    def get_pattern_detection_patterns(self) -> Dict[str, Dict[str, str]]:
        """Restituisce tutti i pattern per la detection."""
        return self._detection_patterns
    
    def get_detection_patterns(self) -> Dict[str, str]:
        """
        Restituisce i pattern di detection in formato semplificato.
        
        WHY: Metodo di compatibilità per PatternDetectionService.
        Converte il formato interno in un formato semplice per la detection.
        """
        simple_patterns = {}
        for pattern_name, pattern_config in self._detection_patterns.items():
            if isinstance(pattern_config, dict) and "regex" in pattern_config:
                simple_patterns[pattern_name] = pattern_config["regex"]
            elif isinstance(pattern_config, str):
                simple_patterns[pattern_name] = pattern_config
        return simple_patterns
    
    def get_parsing_patterns(self) -> Dict[str, Dict[str, str]]:
        """Restituisce tutti i pattern per il parsing."""
        return self._parsing_patterns
    
    def get_cleaning_patterns(self) -> Dict[str, Dict[str, str]]:
        """Restituisce tutti i pattern per il cleaning."""
        return self._cleaning_patterns
    
    def get_csv_recognition_config(self) -> Dict[str, Any]:
        """Restituisce la configurazione per il riconoscimento CSV."""
        # WHY: Usa la cache invece di ricaricare YAML ogni volta
        return self._config_cache.get_csv_recognition_config()
    
    def get_field_detection_config(self) -> Dict[str, Any]:
        """Restituisce la configurazione per il rilevamento automatico dei tipi."""
        # WHY: Usa la cache invece di ricaricare YAML ogni volta
        return self._config_cache.get_field_detection_config()
    
    def get_timestamp_normalization_config(self) -> Dict[str, Any]:
        """Restituisce la configurazione per la normalizzazione timestamp."""
        # WHY: Usa la cache invece di ricaricare YAML ogni volta
        return self._config_cache.get_timestamp_normalization_config()
    
    def get_complex_csv_config(self) -> Dict[str, Any]:
        """Restituisce la configurazione per CSV complessi."""
        # WHY: Usa la cache invece di ricaricare YAML ogni volta
        return self._config_cache.get_complex_csv_config()
    
    def get_intelligent_analysis_config(self) -> Dict[str, Any]:
        """Restituisce la configurazione per l'analisi intelligente."""
        # WHY: Usa la cache invece di ricaricare YAML ogni volta
        return self._config_cache.get_intelligent_analysis_config()
    
    def get_parsers_config(self) -> Dict[str, Any]:
        """Restituisce la configurazione per i parser specifici."""
        # WHY: Usa la cache invece di ricaricare YAML ogni volta
        return self._config_cache.get_parsers_config()
    
    def get_output_config(self) -> Dict[str, Any]:
        """Restituisce la configurazione per l'output."""
        # WHY: Usa la cache invece di ricaricare YAML ogni volta
        return self._config_cache.get_output_config()
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Restituisce la configurazione per il logging."""
        # WHY: Usa la cache invece di ricaricare YAML ogni volta
        return self._config_cache.get_logging_config()
    
    def get_parser_adaptive_config(self) -> Dict[str, Any]:
        """Restituisce la configurazione per il parser universale adattivo."""
        # WHY: Usa la cache invece di ricaricare YAML ogni volta
        return self._config_cache.get_parser_adaptive_config()
    
    def get_file_formats_config(self) -> Dict[str, Any]:
        """Restituisce la configurazione per i formati di file supportati."""
        # WHY: Usa la cache invece di ricaricare YAML ogni volta
        return self._config_cache.get_file_formats_config()
    
    def get_app_config(self) -> Dict[str, Any]:
        """Restituisce la configurazione generale dell'applicazione."""
        # WHY: Usa la cache invece di ricaricare YAML ogni volta
        return self._config_cache.get_app_config()
    
    def get_drain3_config(self) -> Dict[str, Any]:
        """Restituisce la configurazione Drain3."""
        # WHY: Usa la cache invece di ricaricare YAML ogni volta
        return self._config_cache.get_drain3_config()
    
    def get_presidio_config(self) -> Dict[str, Any]:
        """Restituisce la configurazione Microsoft Presidio."""
        # WHY: Usa la cache invece di ricaricare YAML ogni volta
        return self._config_cache.get_presidio_config()
    
    def anonymize_content(self, content: str) -> str:
        """
        Anonimizza il contenuto usando i pattern centralizzati.
        
        Args:
            content: Contenuto da anonimizzare
            
        Returns:
            Contenuto anonimizzato
        """
        anonymized_content = content
        
        # 🚨 CORREZIONE: Applica PRIMA always_anonymize ai campi testuali
        # WHY: I campi in always_anonymize devono essere anonimizzati SEMPRE,
        # anche quando sono nel testo completo, non solo nei campi strutturati
        try:
            # WHY: Usa la cache per ottenere i campi always_anonymize
            regex_config = self._config_cache.get_config('centralized_regex')
            anonymization_config = regex_config.get('anonymization', {})
            
            # Cerca i campi always_anonymize nella configurazione
            if 'always_anonymize' in anonymization_config:
                always_fields = anonymization_config['always_anonymize']
                verbose = bool(self._config_cache.get_config('centralized_regex').get('verbose_logging', False))
                if verbose:
                    print(f"🔍 DEBUG always_anonymize: campi configurati = {always_fields}")
                
                for field_name in always_fields:
                    # Crea pattern per trovare il campo nel testo (es: vd="root", tz="+0200")
                    field_pattern = rf'{field_name}\s*=\s*"([^"]*)"'
                    if verbose:
                        print(f"🔍 DEBUG always_anonymize: pattern per '{field_name}' = {field_pattern}")
                    
                    try:
                        # Cerca se il pattern matcha
                        matches = re.findall(field_pattern, anonymized_content, flags=re.IGNORECASE)
                        if matches:
                            if verbose:
                                print(f"🔍 DEBUG always_anonymize: TROVATO '{field_name}' con valori = {matches}")
                            # Sostituisci con il placeholder appropriato dal config
                            placeholder_key = f"placeholder_{field_name}"
                            if placeholder_key in anonymization_config:
                                placeholder = anonymization_config[placeholder_key]
                            else:
                                placeholder = f"<{field_name.upper()}>"
                            
                            replacement = f'{field_name}="{placeholder}"'
                            anonymized_content = re.sub(field_pattern, replacement, anonymized_content, flags=re.IGNORECASE)
                            if verbose:
                                print(f"🔍 DEBUG always_anonymize: SOSTITUITO '{field_name}' con '{replacement}'")
                        else:
                            if verbose:
                                print(f"🔍 DEBUG always_anonymize: NESSUN MATCH per '{field_name}'")
                    except re.error as e:
                        print(f"⚠️ Errore regex always_anonymize per '{field_name}': {e}")
                
                if verbose:
                    print(f"🔍 DEBUG always_anonymize: testo dopo always_anonymize = {anonymized_content[:200]}...")
                
        except Exception as e:
            print(f"⚠️ Errore nell'applicazione always_anonymize: {e}")
        
        # WHY: Applica i pattern regex generici DOPO always_anonymize
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
        WHY: Tutte le regex sono ora centralizzate nel file di configurazione
        per evitare duplicazioni e inconsistenze.
        """
        if anonymized:
            template_content = self.anonymize_content(content)
        else:
            template_content = content
        
        template = template_content
        
        # ✅ IMPORTANTE: Usa le regex dal file di configurazione invece di hardcoded
        # Applica i pattern generici in ordine di specificità
        
        # 1. Prima i pattern più specifici (timestamp, date, time)
        if "generic_timestamp" in self._anonymization_patterns:
            timestamp_pattern = self._compiled_anonymization.get("generic_timestamp")
            if timestamp_pattern:
                template = timestamp_pattern.sub("<TIMESTAMP>", template)
        
        if "generic_date" in self._anonymization_patterns:
            date_pattern = self._compiled_anonymization.get("generic_date")
            if date_pattern:
                template = date_pattern.sub("<DATE>", template)
        
        if "generic_time" in self._anonymization_patterns:
            time_pattern = self._compiled_anonymization.get("generic_time")
            if time_pattern:
                template = time_pattern.sub("<TIME>", template)
        
        # 2. Poi i pattern generici (numeri, stringhe)
        if "generic_number" in self._anonymization_patterns:
            number_pattern = self._compiled_anonymization.get("generic_number")
            if number_pattern:
                template = number_pattern.sub("<NUM>", template)
        
        if "generic_string" in self._anonymization_patterns:
            string_pattern = self._compiled_anonymization.get("generic_string")
            if string_pattern:
                # Sostituisci stringhe tra virgolette con <STR> se non sono già placeholder
                template = string_pattern.sub(lambda m: f'"{m.group(1)}"' if any(ph in m.group(1) for ph in ['<IP>', '<MAC>', '<DEVICE_ID>', '<DEVICE_NAME>', '<HOSTNAME>', '<TIMEZONE>', '<VD>', '<UNIX_TIMESTAMP>', '<NUMERIC_ID>', '<PORT>', '<VERSION>', '<HASH>', '<UUID>']) else '"<STR>"', template)
        
        return template
    
    def get_placeholder_for_field(self, field_name: str) -> str:
        """
        Ottiene il placeholder corretto per un campo specifico.
        WHY: Garantisce coerenza tra always_anonymize e i placeholder del config.
        
        Args:
            field_name: Nome del campo da anonimizzare
            
        Returns:
            Placeholder appropriato per il campo
        """
        try:
            # WHY: Usa la cache per ottenere i placeholder dal config
            regex_config = self._config_cache.get_config('centralized_regex')
            anonymization_config = regex_config.get('anonymization', {})
            
            # Cerca il placeholder specifico per questo campo
            placeholder_key = f"placeholder_{field_name}"
            if placeholder_key in anonymization_config:
                return anonymization_config[placeholder_key]
            
            # Fallback: usa il nome del campo in maiuscolo
            return f"<{field_name.upper()}>"
            
        except Exception as e:
            print(f"⚠️ Errore nel recupero placeholder per '{field_name}': {e}")
            # Fallback sicuro
            return f"<{field_name.upper()}>"
