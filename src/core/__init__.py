"""
Core Layer - Layer condiviso per tutta l'applicazione

Questo modulo fornisce le funzionalità core condivise da tutti i layer
dell'applicazione, inclusi eccezioni, costanti, enumerazioni, validatori
e servizi di utilità.

DESIGN:
- Layer condiviso per massimizzare la riusabilità
- Dipendenze minime per evitare coupling
- Interfacce chiare per facilitare testing
- Gestione centralizzata di errori e validazioni

Author: Edoardo D'Alesio
Version: 1.0.0
"""

# Import delle eccezioni core
from .exceptions import (
    CoreException,
    ValidationError,
    ConfigurationError,
    ProcessingError,
    ParserError
)

# Import delle costanti
from .constants import (
    # Configurazione
    DEFAULT_CONFIG_PATH,
    SUPPORTED_FORMATS,
    MAX_FILE_SIZE,
    
    # Parsing
    DEFAULT_ENCODING,
    BUFFER_SIZE,
    MAX_LINE_LENGTH,
    
    # Anonimizzazione
    ANONYMIZATION_METHODS,
    SENSITIVE_FIELDS,
    
    # Performance
    DEFAULT_TIMEOUT,
    MAX_WORKERS,
    CHUNK_SIZE
)

# Import delle enumerazioni
from .enums import (
    LogFormat,
    ParserType,
    AnonymizationMethod,
    ProcessingStatus,
    ErrorSeverity,
    ValidationLevel,
    CacheStrategy
)

# Import dei validatori
from .validators import (
    ConfigValidator,
    DataValidator,
    FileValidator,
    SchemaValidator
)

# Import dei servizi core
from .services import (
    LoggerService,
    MetricsService,
    CacheService,
    ValidatorService
)

__all__ = [
    # Eccezioni
    'CoreException',
    'ValidationError', 
    'ConfigurationError',
    'ProcessingError',
    'ParserError',
    
    # Costanti
    'DEFAULT_CONFIG_PATH',
    'SUPPORTED_FORMATS',
    'MAX_FILE_SIZE',
    'DEFAULT_ENCODING',
    'BUFFER_SIZE',
    'MAX_LINE_LENGTH',
    'ANONYMIZATION_METHODS',
    'SENSITIVE_FIELDS',
    'DEFAULT_TIMEOUT',
    'MAX_WORKERS',
    'CHUNK_SIZE',
    
    # Enumerazioni
    'LogFormat',
    'ParserType',
    'AnonymizationMethod',
    'ProcessingStatus',
    'ErrorSeverity',
    'ValidationLevel',
    'CacheStrategy',
    
    # Validatori
    'ConfigValidator',
    'DataValidator',
    'FileValidator',
    'SchemaValidator',
    
    # Servizi
    'LoggerService',
    'MetricsService',
    'CacheService',
    'ValidatorService'
] 