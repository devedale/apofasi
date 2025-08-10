"""
Logger Service - Servizio di logging centralizzato

Questo modulo fornisce un servizio di logging centralizzato per tutta
l'applicazione, con supporto per logging strutturato, rotazione automatica
e configurazione dinamica dei livelli di log.

DESIGN:
- Logging strutturato con contesto aggiuntivo
- Rotazione automatica dei file di log
- Configurazione dinamica dei livelli
- Supporto per multiple destinazioni

Author: Edoardo D'Alesio
Version: 1.0.0
"""

import logging
import logging.handlers
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..constants import LOG_LEVELS, LOG_TIMESTAMP_FORMAT, MAX_LOG_FILE_SIZE, LOG_BACKUP_COUNT
from ..enums import ErrorSeverity


class LoggerService:
    """
    Servizio di logging centralizzato per l'applicazione.
    
    WHY: Servizio centralizzato per garantire consistenza nel logging
    e facilitare il debugging e monitoring dell'applicazione.
    
    Contract:
        - Configurazione centralizzata dei logger
        - Logging strutturato con metadati
        - Rotazione automatica dei file
        - Supporto per multiple destinazioni
    """
    
    def __init__(self, 
                 log_level: str = "INFO",
                 log_file: Optional[Path] = None,
                 console_output: bool = True,
                 structured_logging: bool = True):
        """
        Inizializza il servizio di logging.
        
        Args:
            log_level: Livello di logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file: Percorso del file di log (opzionale)
            console_output: Se True, logga anche su console
            structured_logging: Se True, usa logging strutturato JSON
        """
        self.log_level = self._validate_log_level(log_level)
        self.log_file = log_file
        self.console_output = console_output
        self.structured_logging = structured_logging
        
        # Configura il logging
        self._setup_logging()
        
        # Logger principale
        self.logger = logging.getLogger('clean_parser')
        self.logger.setLevel(self.log_level)
    
    def _validate_log_level(self, level: str) -> str:
        """
        Valida il livello di logging.
        
        WHY: Validazione per garantire che il livello sia valido
        e fornire fallback appropriati.
        
        Args:
            level: Livello di logging da validare
            
        Returns:
            Livello di logging validato
        """
        if level.upper() in LOG_LEVELS:
            return level.upper()
        else:
            print(f"Warning: Livello di log '{level}' non valido, usando INFO")
            return "INFO"
    
    def _setup_logging(self):
        """Configura il sistema di logging."""
        # Rimuovi handler esistenti
        logging.getLogger().handlers.clear()
        
        # Formatter per logging strutturato
        if self.structured_logging:
            formatter = logging.Formatter(
                '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
                '"module": "%(name)s", "message": "%(message)s"}'
            )
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt=LOG_TIMESTAMP_FORMAT
            )
        
        # Handler per console
        if self.console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            logging.getLogger().addHandler(console_handler)
        
        # Handler per file
        if self.log_file:
            self._setup_file_handler(formatter)
    
    def _setup_file_handler(self, formatter):
        """Configura l'handler per file con rotazione."""
        # Crea directory se non esiste
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Handler con rotazione automatica
        file_handler = logging.handlers.RotatingFileHandler(
            self.log_file,
            maxBytes=MAX_LOG_FILE_SIZE,
            backupCount=LOG_BACKUP_COUNT
        )
        file_handler.setFormatter(formatter)
        logging.getLogger().addHandler(file_handler)
    
    def log(self, level: str, message: str, context: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Logga un messaggio con contesto opzionale.
        
        WHY: Metodo principale per logging con supporto per
        contesto strutturato e parametri aggiuntivi.
        
        Args:
            level: Livello di logging
            message: Messaggio da loggare
            context: Contesto aggiuntivo (opzionale)
            **kwargs: Parametri aggiuntivi per il contesto
        """
        # Combina context e kwargs
        full_context = context or {}
        full_context.update(kwargs)
        
        # Prepara il messaggio con contesto
        if full_context:
            context_str = json.dumps(full_context)
            log_message = f"{message} | Context: {context_str}"
        else:
            log_message = message
        
        # Logga con il livello appropriato
        if level.upper() == "DEBUG":
            self.logger.debug(log_message, extra={'context': full_context})
        elif level.upper() == "INFO":
            self.logger.info(log_message, extra={'context': full_context})
        elif level.upper() == "WARNING":
            self.logger.warning(log_message, extra={'context': full_context})
        elif level.upper() == "ERROR":
            self.logger.error(log_message, extra={'context': full_context})
        elif level.upper() == "CRITICAL":
            self.logger.critical(log_message, extra={'context': full_context})
        else:
            self.logger.info(log_message, extra={'context': full_context})
    
    def debug(self, message: str, context: Optional[Dict[str, Any]] = None, **kwargs):
        """Logga un messaggio di debug."""
        self.log("DEBUG", message, context, **kwargs)
    
    def info(self, message: str, context: Optional[Dict[str, Any]] = None, **kwargs):
        """Logga un messaggio informativo."""
        self.log("INFO", message, context, **kwargs)
    
    def warning(self, message: str, context: Optional[Dict[str, Any]] = None, **kwargs):
        """Logga un warning."""
        self.log("WARNING", message, context, **kwargs)
    
    def error(self, message: str, context: Optional[Dict[str, Any]] = None, **kwargs):
        """Logga un errore."""
        self.log("ERROR", message, context, **kwargs)
    
    def critical(self, message: str, context: Optional[Dict[str, Any]] = None, **kwargs):
        """Logga un errore critico."""
        self.log("CRITICAL", message, context, **kwargs)
    
    def log_exception(self, exception: Exception, context: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Logga un'eccezione con stack trace.
        
        WHY: Metodo specializzato per logging di eccezioni
        con informazioni dettagliate per debugging.
        
        Args:
            exception: Eccezione da loggare
            context: Contesto aggiuntivo
            **kwargs: Parametri aggiuntivi
        """
        full_context = context or {}
        full_context.update(kwargs)
        full_context['exception_type'] = type(exception).__name__
        full_context['exception_message'] = str(exception)
        
        self.error(f"Exception occurred: {exception}", full_context)
        self.logger.exception("Stack trace:")
    
    def log_performance(self, operation: str, duration: float, context: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Logga metriche di performance.
        
        WHY: Metodo specializzato per logging di performance
        con formato standardizzato per monitoring.
        
        Args:
            operation: Nome dell'operazione
            duration: Durata in secondi
            context: Contesto aggiuntivo
            **kwargs: Parametri aggiuntivi
        """
        full_context = context or {}
        full_context.update(kwargs)
        full_context['operation'] = operation
        full_context['duration_seconds'] = duration
        full_context['duration_ms'] = duration * 1000
        
        self.info(f"Performance: {operation} completed in {duration:.3f}s", full_context)
    
    def log_security(self, event: str, severity: ErrorSeverity, context: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Logga eventi di sicurezza.
        
        WHY: Metodo specializzato per logging di eventi di sicurezza
        con livelli di severità appropriati.
        
        Args:
            event: Evento di sicurezza
            severity: Severità dell'evento
            context: Contesto aggiuntivo
            **kwargs: Parametri aggiuntivi
        """
        full_context = context or {}
        full_context.update(kwargs)
        full_context['security_event'] = True
        full_context['severity'] = severity.value
        
        if severity.requires_alert():
            self.critical(f"Security Alert: {event}", full_context)
        else:
            self.warning(f"Security Event: {event}", full_context)
    
    def set_level(self, level: str):
        """
        Imposta il livello di logging dinamicamente.
        
        WHY: Permette di cambiare il livello di logging
        senza riavviare l'applicazione.
        
        Args:
            level: Nuovo livello di logging
        """
        self.log_level = self._validate_log_level(level)
        self.logger.setLevel(self.log_level)
        self.info(f"Log level changed to {self.log_level}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Restituisce statistiche del logging.
        
        WHY: Metodo di utilità per monitoring
        e debugging del sistema di logging.
        
        Returns:
            Dizionario con statistiche del logging
        """
        return {
            'log_level': self.log_level,
            'log_file': str(self.log_file) if self.log_file else None,
            'console_output': self.console_output,
            'structured_logging': self.structured_logging,
            'timestamp': datetime.now().isoformat()
        } 