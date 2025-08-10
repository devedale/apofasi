"""
Core Exceptions - Eccezioni centralizzate per l'applicazione

Questo modulo definisce tutte le eccezioni personalizzate utilizzate
nell'applicazione, fornendo una gerarchia chiara e informazioni
dettagliate per debugging e gestione errori.

DESIGN:
- Gerarchia di eccezioni ben definita
- Informazioni contestuali per debugging
- Separazione tra errori di sistema e di business logic
- Supporto per errori specifici per dominio

Author: Edoardo D'Alesio
Version: 1.0.0
"""

from typing import Optional, Dict, Any, List


class CoreException(Exception):
    """
    Eccezione base per tutte le eccezioni dell'applicazione.
    
    WHY: Eccezione base che fornisce funzionalità comuni come
    contesto aggiuntivo e gestione centralizzata degli errori.
    
    Attributes:
        message: Messaggio descrittivo dell'errore
        context: Dizionario con informazioni contestuali
        severity: Gravità dell'errore (opzionale)
    """
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None, severity: str = "error"):
        self.message = message
        self.context = context or {}
        self.severity = severity
        super().__init__(self.message)
    
    def __str__(self) -> str:
        """Rappresentazione stringa dell'eccezione con contesto."""
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{self.message} (Context: {context_str})"
        return self.message


class ValidationError(CoreException):
    """
    Eccezione per errori di validazione dei dati.
    
    WHY: Separazione specifica per errori di validazione che
    possono essere gestiti diversamente dagli altri errori.
    
    Attributes:
        field: Campo che ha causato l'errore di validazione
        value: Valore che ha causato l'errore
        rule: Regola di validazione violata
    """
    
    def __init__(self, message: str, field: Optional[str] = None, value: Any = None, rule: Optional[str] = None):
        context = {
            'field': field,
            'value': value,
            'rule': rule
        }
        super().__init__(message, context, "validation_error")


class ConfigurationError(CoreException):
    """
    Eccezione per errori di configurazione.
    
    WHY: Errori di configurazione sono critici e richiedono
    attenzione immediata per garantire il funzionamento del sistema.
    
    Attributes:
        config_path: Percorso del file di configurazione
        section: Sezione della configurazione problematica
        key: Chiave di configurazione problematica
    """
    
    def __init__(self, message: str, config_path: Optional[str] = None, section: Optional[str] = None, key: Optional[str] = None):
        context = {
            'config_path': config_path,
            'section': section,
            'key': key
        }
        super().__init__(message, context, "critical")


class ProcessingError(CoreException):
    """
    Eccezione per errori durante il processing dei dati.
    
    WHY: Errori di processing possono essere temporanei e
    potrebbero permettere retry o fallback strategies.
    
    Attributes:
        stage: Stadio del processing dove è avvenuto l'errore
        input_data: Dati di input che hanno causato l'errore
        retry_count: Numero di tentativi effettuati
    """
    
    def __init__(self, message: str, stage: Optional[str] = None, input_data: Optional[Any] = None, retry_count: int = 0):
        context = {
            'stage': stage,
            'input_data': str(input_data) if input_data else None,
            'retry_count': retry_count
        }
        super().__init__(message, context, "processing_error")


class ParserError(CoreException):
    """
    Eccezione specifica per errori di parsing.
    
    WHY: Errori di parsing sono comuni e richiedono informazioni
    specifiche come numero di riga e contenuto problematico.
    
    Attributes:
        line_number: Numero della riga che ha causato l'errore
        line_content: Contenuto della riga problematica
        parser_type: Tipo di parser che ha generato l'errore
        format_type: Tipo di formato che stava tentando di parsare
    """
    
    def __init__(self, message: str, line_number: Optional[int] = None, line_content: Optional[str] = None, 
                 parser_type: Optional[str] = None, format_type: Optional[str] = None):
        context = {
            'line_number': line_number,
            'line_content': line_content,
            'parser_type': parser_type,
            'format_type': format_type
        }
        super().__init__(message, context, "parsing_error")


class AnonymizationError(CoreException):
    """
    Eccezione per errori durante l'anonimizzazione.
    
    WHY: Errori di anonimizzazione sono critici per la privacy
    e richiedono logging dettagliato per audit trail.
    
    Attributes:
        field_name: Nome del campo che ha causato l'errore
        method: Metodo di anonimizzazione utilizzato
        original_value: Valore originale (se disponibile)
    """
    
    def __init__(self, message: str, field_name: Optional[str] = None, method: Optional[str] = None, 
                 original_value: Optional[str] = None):
        context = {
            'field_name': field_name,
            'method': method,
            'original_value': original_value
        }
        super().__init__(message, context, "privacy_error")


class SchemaError(CoreException):
    """
    Eccezione per errori di schema e validazione strutturale.
    
    WHY: Errori di schema indicano problemi nella struttura
    dei dati e richiedono correzioni specifiche.
    
    Attributes:
        schema_name: Nome dello schema violato
        field_path: Percorso del campo che ha violato lo schema
        expected_type: Tipo atteso per il campo
        actual_type: Tipo effettivo del campo
    """
    
    def __init__(self, message: str, schema_name: Optional[str] = None, field_path: Optional[str] = None,
                 expected_type: Optional[str] = None, actual_type: Optional[str] = None):
        context = {
            'schema_name': schema_name,
            'field_path': field_path,
            'expected_type': expected_type,
            'actual_type': actual_type
        }
        super().__init__(message, context, "schema_error")


class PerformanceError(CoreException):
    """
    Eccezione per errori di performance e timeout.
    
    WHY: Errori di performance richiedono monitoring specifico
    e potrebbero indicare problemi di scalabilità.
    
    Attributes:
        operation: Operazione che ha causato il timeout
        duration: Durata dell'operazione (in secondi)
        timeout_limit: Limite di timeout configurato
        resource_usage: Utilizzo delle risorse durante l'operazione
    """
    
    def __init__(self, message: str, operation: Optional[str] = None, duration: Optional[float] = None,
                 timeout_limit: Optional[float] = None, resource_usage: Optional[Dict[str, Any]] = None):
        context = {
            'operation': operation,
            'duration': duration,
            'timeout_limit': timeout_limit,
            'resource_usage': resource_usage
        }
        super().__init__(message, context, "performance_error") 