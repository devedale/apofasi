"""
Core Constants - Costanti centralizzate per l'applicazione

Questo modulo definisce tutte le costanti utilizzate nell'applicazione,
fornendo valori standardizzati e configurabili per diversi aspetti
del sistema come parsing, anonimizzazione, performance e configurazione.

DESIGN:
- Costanti ben documentate e organizzate per categoria
- Valori sensati per diversi scenari d'uso
- Facilmente configurabili per deployment diversi
- Supporto per limiti di sicurezza e performance

Author: Edoardo D'Alesio
Version: 1.0.0
"""

import os
from pathlib import Path

# =============================================================================
# CONFIGURAZIONE
# =============================================================================

# Percorso di default per i file di configurazione
DEFAULT_CONFIG_PATH = Path("config/config.yaml")

# Formati di log supportati dal sistema
SUPPORTED_FORMATS = [
    'cef',      # Common Event Format
    'syslog',   # Syslog (RFC3164, RFC5424)
    'json',     # JSON strutturato
    'csv',      # CSV/TSV
    'apache',   # Apache access logs
    'fortinet', # Fortinet logs
    'txt'       # Testo strutturato
]

# =============================================================================
# LIMITI DI SISTEMA
# =============================================================================

# Dimensione massima file (100MB)
MAX_FILE_SIZE = 100 * 1024 * 1024

# Dimensione massima riga singola (1MB)
MAX_LINE_LENGTH = 1024 * 1024

# Timeout di default per operazioni (30 secondi)
DEFAULT_TIMEOUT = 30.0

# Numero massimo di worker per processing parallelo
MAX_WORKERS = min(32, (os.cpu_count() or 1) + 4)

# Dimensione chunk per processing di file grandi (1MB)
CHUNK_SIZE = 1024 * 1024

# =============================================================================
# PARSING
# =============================================================================

# Encoding di default per i file
DEFAULT_ENCODING = 'utf-8'

# Encoding alternativi supportati
SUPPORTED_ENCODINGS = [
    'utf-8',
    'utf-16',
    'latin-1',
    'ascii',
    'iso-8859-1'
]

# Dimensione buffer per lettura file (64KB)
BUFFER_SIZE = 64 * 1024

# Numero di righe da campionare per rilevamento formato
SAMPLE_LINES = 100

# Soglia di confidenza per rilevamento formato (70%)
FORMAT_DETECTION_THRESHOLD = 0.7

# =============================================================================
# ANONIMIZZAZIONE
# =============================================================================

# Metodi di anonimizzazione supportati
ANONYMIZATION_METHODS = [
    'hash',      # Hash SHA-256
    'mask',      # Mascheramento con asterischi
    'replace',   # Sostituzione con placeholder
    'encrypt',   # Crittografia (se supportata)
    'delete'     # Rimozione completa
]

# Campi sensibili per anonimizzazione automatica
SENSITIVE_FIELDS = [
    'password',
    'passwd',
    'pwd',
    'secret',
    'key',
    'token',
    'auth',
    'credential',
    'ssn',
    'social_security',
    'credit_card',
    'cc_number',
    'phone',
    'email',
    'address',
    'ip_address',
    'mac_address'
]

# Pattern regex per rilevamento automatico dati sensibili
SENSITIVE_PATTERNS = {
    'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    'ip_address': r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
    'credit_card': r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',
    'phone': r'\b\+?[\d\s\-\(\)]{10,}\b',
    'ssn': r'\b\d{3}-\d{2}-\d{4}\b'
}

# =============================================================================
# PERFORMANCE
# =============================================================================

# Limiti di memoria per processing (512MB)
MAX_MEMORY_USAGE = 512 * 1024 * 1024

# Intervallo di aggiornamento progress bar (1000 righe)
PROGRESS_UPDATE_INTERVAL = 1000

# Timeout per operazioni di rete (10 secondi)
NETWORK_TIMEOUT = 10.0

# Numero massimo di file da processare in parallelo
MAX_CONCURRENT_FILES = 4

# =============================================================================
# LOGGING
# =============================================================================

# Livelli di log supportati
LOG_LEVELS = [
    'DEBUG',
    'INFO', 
    'WARNING',
    'ERROR',
    'CRITICAL'
]

# Formato di default per i timestamp nei log
LOG_TIMESTAMP_FORMAT = '%Y-%m-%d %H:%M:%S'

# Dimensione massima file di log (10MB)
MAX_LOG_FILE_SIZE = 10 * 1024 * 1024

# Numero di backup file di log da mantenere
LOG_BACKUP_COUNT = 5

# =============================================================================
# VALIDAZIONE
# =============================================================================

# Lunghezza massima per stringhe (1MB)
MAX_STRING_LENGTH = 1024 * 1024

# Numero massimo di campi per record (1000)
MAX_FIELDS_PER_RECORD = 1000

# Numero massimo di record per file (1M)
MAX_RECORDS_PER_FILE = 1_000_000

# Soglia di warning per performance (80%)
PERFORMANCE_WARNING_THRESHOLD = 0.8

# =============================================================================
# CACHE
# =============================================================================

# Dimensione massima cache in memoria (100MB)
MAX_CACHE_SIZE = 100 * 1024 * 1024

# TTL di default per cache entries (1 ora)
DEFAULT_CACHE_TTL = 3600

# Numero massimo di entries in cache (10000)
MAX_CACHE_ENTRIES = 10_000

# =============================================================================
# METRICHE
# =============================================================================

# Intervallo di aggiornamento metriche (5 secondi)
METRICS_UPDATE_INTERVAL = 5.0

# Metriche di performance da tracciare
PERFORMANCE_METRICS = [
    'processing_time',
    'memory_usage',
    'cpu_usage',
    'file_size',
    'records_processed',
    'errors_count',
    'warnings_count'
]

# =============================================================================
# SICUREZZA
# =============================================================================

# Lunghezza minima per hash di sicurezza (32 caratteri)
MIN_HASH_LENGTH = 32

# Algoritmi di hash supportati
SUPPORTED_HASH_ALGORITHMS = [
    'sha256',
    'sha512',
    'blake2b'
]

# Salt di default per hash (32 bytes)
DEFAULT_SALT_LENGTH = 32

# =============================================================================
# OUTPUT
# =============================================================================

# Formati di output supportati
SUPPORTED_OUTPUT_FORMATS = [
    'json',
    'csv',
    'xml',
    'yaml'
]

# Compressione supportata
SUPPORTED_COMPRESSION = [
    'gzip',
    'bzip2',
    'lzma'
]

# =============================================================================
# ERRORI E WARNING
# =============================================================================

# Codici di errore standard
ERROR_CODES = {
    'VALIDATION_ERROR': 1001,
    'CONFIGURATION_ERROR': 1002,
    'PARSING_ERROR': 1003,
    'PROCESSING_ERROR': 1004,
    'ANONYMIZATION_ERROR': 1005,
    'PERFORMANCE_ERROR': 1006,
    'SCHEMA_ERROR': 1007
}

# Messaggi di errore standard
ERROR_MESSAGES = {
    'FILE_TOO_LARGE': 'File size exceeds maximum allowed size',
    'INVALID_FORMAT': 'File format not supported or invalid',
    'ENCODING_ERROR': 'Unable to decode file with specified encoding',
    'PERMISSION_DENIED': 'Permission denied accessing file',
    'TIMEOUT_ERROR': 'Operation timed out',
    'MEMORY_ERROR': 'Insufficient memory for operation'
} 