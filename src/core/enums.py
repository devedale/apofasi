"""
Core Enums - Enumerazioni centralizzate per l'applicazione

Questo modulo definisce tutte le enumerazioni utilizzate nell'applicazione,
fornendo tipi di dati strutturati e validati per diversi aspetti
del sistema come formati di log, tipi di parser, metodi di anonimizzazione.

DESIGN:
- Enumerazioni ben documentate e tipizzate
- Valori semantici per facilitare la comprensione
- Supporto per serializzazione e deserializzazione
- Integrazione con il sistema di validazione

Author: Edoardo D'Alesio
Version: 1.0.0
"""

from enum import Enum, auto
from typing import List, Optional


class LogFormat(Enum):
    """
    Enumerazione dei formati di log supportati.
    
    WHY: Enumerazione per garantire tipi di dati validi
    e facilitare la gestione dei diversi formati di log.
    """
    
    CEF = "cef"                    # Common Event Format
    SYSLOG = "syslog"              # Syslog (RFC3164, RFC5424)
    JSON = "json"                  # JSON strutturato
    CSV = "csv"                    # CSV/TSV
    APACHE = "apache"              # Apache access logs
    FORTINET = "fortinet"          # Fortinet logs
    TXT = "txt"                    # Testo strutturato
    UNKNOWN = "unknown"            # Formato non riconosciuto
    
    @classmethod
    def from_string(cls, value: str) -> 'LogFormat':
        """
        Converte una stringa in LogFormat.
        
        WHY: Metodo di utilità per gestire input stringa
        e fornire fallback per valori non validi.
        
        Args:
            value: Stringa da convertire
            
        Returns:
            LogFormat corrispondente o UNKNOWN se non valido
        """
        try:
            return cls(value.lower())
        except ValueError:
            return cls.UNKNOWN
    
    def is_structured(self) -> bool:
        """
        Determina se il formato è strutturato.
        
        WHY: Distinzione importante per ottimizzazioni
        e strategie di parsing diverse.
        
        Returns:
            True se il formato è strutturato
        """
        return self in [LogFormat.JSON, LogFormat.CSV, LogFormat.CEF]
    
    def requires_schema(self) -> bool:
        """
        Determina se il formato richiede schema.
        
        WHY: Alcuni formati necessitano di schema
        per parsing accurato.
        
        Returns:
            True se il formato richiede schema
        """
        return self in [LogFormat.JSON, LogFormat.CSV]


class ParserType(Enum):
    """
    Enumerazione dei tipi di parser disponibili.
    
    WHY: Enumerazione per identificare e gestire
    i diversi tipi di parser nel sistema.
    """
    
    UNIVERSAL = "universal"         # Parser universale
    CEF = "cef"                    # Parser CEF specifico
    SYSLOG = "syslog"              # Parser Syslog specifico
    JSON = "json"                  # Parser JSON specifico
    CSV = "csv"                    # Parser CSV specifico
    APACHE = "apache"              # Parser Apache specifico
    FORTINET = "fortinet"          # Parser Fortinet specifico
    ADAPTIVE = "adaptive"          # Parser adattivo
    MULTI_STRATEGY = "multi_strategy"  # Parser multi-strategia
    
    @classmethod
    def from_log_format(cls, log_format: LogFormat) -> 'ParserType':
        """
        Mappa LogFormat a ParserType.
        
        WHY: Metodo di utilità per determinare automaticamente
        il parser appropriato basato sul formato di log.
        
        Args:
            log_format: Formato di log
            
        Returns:
            ParserType corrispondente
        """
        mapping = {
            LogFormat.CEF: cls.CEF,
            LogFormat.SYSLOG: cls.SYSLOG,
            LogFormat.JSON: cls.JSON,
            LogFormat.CSV: cls.CSV,
            LogFormat.APACHE: cls.APACHE,
            LogFormat.FORTINET: cls.FORTINET
        }
        return mapping.get(log_format, cls.UNIVERSAL)


class AnonymizationMethod(Enum):
    """
    Enumerazione dei metodi di anonimizzazione.
    
    WHY: Enumerazione per garantire metodi di anonimizzazione
    validi e tracciabili per compliance privacy.
    """
    
    HASH = "hash"                  # Hash crittografico
    MASK = "mask"                  # Mascheramento con asterischi
    REPLACE = "replace"            # Sostituzione con placeholder
    ENCRYPT = "encrypt"            # Crittografia
    DELETE = "delete"              # Rimozione completa
    PSEUDONYMIZE = "pseudonymize"  # Pseudonimizzazione
    
    def is_reversible(self) -> bool:
        """
        Determina se il metodo è reversibile.
        
        WHY: Informazione critica per compliance GDPR
        e gestione dei dati personali.
        
        Returns:
            True se il metodo è reversibile
        """
        return self in [self.ENCRYPT, self.PSEUDONYMIZE]
    
    def preserves_format(self) -> bool:
        """
        Determina se il metodo preserva il formato originale.
        
        WHY: Importante per mantenere la struttura
        dei dati per analisi successive.
        
        Returns:
            True se il formato è preservato
        """
        return self in [self.MASK, self.PSEUDONYMIZE]


class ProcessingStatus(Enum):
    """
    Enumerazione degli stati di processing.
    
    WHY: Enumerazione per tracciare lo stato delle operazioni
    e fornire feedback accurato agli utenti.
    """
    
    PENDING = "pending"             # In attesa di processing
    PROCESSING = "processing"       # In corso di processing
    COMPLETED = "completed"         # Processing completato con successo
    FAILED = "failed"               # Processing fallito
    CANCELLED = "cancelled"         # Processing cancellato
    PARTIAL = "partial"             # Processing parzialmente completato
    
    def is_final(self) -> bool:
        """
        Determina se lo stato è finale.
        
        WHY: Importante per gestire retry e cleanup
        delle risorse di processing.
        
        Returns:
            True se lo stato è finale
        """
        return self in [self.COMPLETED, self.FAILED, self.CANCELLED]
    
    def is_success(self) -> bool:
        """
        Determina se lo stato indica successo.
        
        WHY: Utile per decisioni di business logic
        e reporting dei risultati.
        
        Returns:
            True se lo stato indica successo
        """
        return self in [self.COMPLETED, self.PARTIAL]


class ErrorSeverity(Enum):
    """
    Enumerazione della severità degli errori.
    
    WHY: Enumerazione per categorizzare errori e
    determinare azioni appropriate (retry, alert, etc.).
    """
    
    DEBUG = "debug"                 # Informazioni di debug
    INFO = "info"                   # Informazioni generali
    WARNING = "warning"             # Warning non critico
    ERROR = "error"                 # Errore che impedisce l'operazione
    CRITICAL = "critical"           # Errore critico del sistema
    
    def requires_alert(self) -> bool:
        """
        Determina se la severità richiede alert.
        
        WHY: Importante per sistema di monitoring
        e notifiche automatiche.
        
        Returns:
            True se richiede alert
        """
        return self in [self.ERROR, self.CRITICAL]
    
    def allows_retry(self) -> bool:
        """
        Determina se la severità permette retry.
        
        WHY: Utile per implementare retry logic
        e gestire errori temporanei.
        
        Returns:
            True se permette retry
        """
        return self in [self.WARNING, self.ERROR]


class ValidationLevel(Enum):
    """
    Enumerazione dei livelli di validazione.
    
    WHY: Enumerazione per configurare la stringenza
    della validazione in base al contesto.
    """
    
    NONE = "none"                   # Nessuna validazione
    BASIC = "basic"                 # Validazione base
    STRICT = "strict"               # Validazione rigorosa
    COMPLIANCE = "compliance"       # Validazione per compliance
    
    def requires_schema(self) -> bool:
        """
        Determina se il livello richiede schema.
        
        WHY: Importante per determinare se caricare
        e utilizzare schemi di validazione.
        
        Returns:
            True se richiede schema
        """
        return self in [self.STRICT, self.COMPLIANCE]


class CacheStrategy(Enum):
    """
    Enumerazione delle strategie di cache.
    
    WHY: Enumerazione per configurare il comportamento
    della cache in base alle esigenze di performance.
    """
    
    NONE = "none"                   # Nessuna cache
    MEMORY = "memory"               # Cache in memoria
    DISK = "disk"                   # Cache su disco
    HYBRID = "hybrid"               # Cache ibrida (memoria + disco)
    
    def uses_memory(self) -> bool:
        """
        Determina se la strategia usa memoria.
        
        WHY: Importante per gestire l'utilizzo
        delle risorse di sistema.
        
        Returns:
            True se usa memoria
        """
        return self in [self.MEMORY, self.HYBRID]
    
    def uses_disk(self) -> bool:
        """
        Determina se la strategia usa disco.
        
        WHY: Importante per gestire I/O
        e spazio su disco.
        
        Returns:
            True se usa disco
        """
        return self in [self.DISK, self.HYBRID] 