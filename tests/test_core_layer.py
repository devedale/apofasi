"""
Test per il Core Layer

Questo script testa tutti i componenti del Core Layer per verificare
che funzionino correttamente e siano integrati tra loro.

Author: Edoardo D'Alesio
Version: 1.0.0
"""

import sys
import tempfile
from pathlib import Path

# Aggiungi il path del progetto per gli import
sys.path.insert(0, str(Path(__file__).parent))

from src.core import (
    # Eccezioni
    CoreException, ValidationError, ConfigurationError, ProcessingError, ParserError,
    
    # Costanti
    DEFAULT_CONFIG_PATH, SUPPORTED_FORMATS, MAX_FILE_SIZE, DEFAULT_ENCODING,
    ANONYMIZATION_METHODS, SENSITIVE_FIELDS,
    
    # Enumerazioni
    LogFormat, ParserType, AnonymizationMethod, ProcessingStatus, ErrorSeverity,
    
    # Validatori
    ConfigValidator, DataValidator, FileValidator, SchemaValidator,
    
    # Servizi
    LoggerService
)


def test_exceptions():
    """Test delle eccezioni core."""
    print("🧪 Testando eccezioni core...")
    
    # Test CoreException
    try:
        raise CoreException("Test error", {"field": "value"}, "error")
    except CoreException as e:
        assert e.message == "Test error"
        assert e.context == {"field": "value"}
        assert e.severity == "error"
        assert "Context: field=value" in str(e)
    
    # Test ValidationError
    try:
        raise ValidationError("Validation failed", "test_field", "test_value", "required")
    except ValidationError as e:
        assert e.message == "Validation failed"
        assert e.context["field"] == "test_field"
        assert e.context["value"] == "test_value"
        assert e.context["rule"] == "required"
    
    # Test ConfigurationError
    try:
        raise ConfigurationError("Config error", "config.yaml", "parsing", "timeout")
    except ConfigurationError as e:
        assert e.message == "Config error"
        assert e.context["config_path"] == "config.yaml"
        assert e.context["section"] == "parsing"
        assert e.context["key"] == "timeout"
    
    print("✅ Eccezioni core test completato con successo")


def test_constants():
    """Test delle costanti core."""
    print("🧪 Testando costanti core...")
    
    # Test costanti di configurazione
    assert isinstance(DEFAULT_CONFIG_PATH, Path)
    assert isinstance(SUPPORTED_FORMATS, list)
    assert len(SUPPORTED_FORMATS) > 0
    assert 'cef' in SUPPORTED_FORMATS
    assert 'syslog' in SUPPORTED_FORMATS
    
    # Test costanti di sistema
    assert isinstance(MAX_FILE_SIZE, int)
    assert MAX_FILE_SIZE > 0
    assert isinstance(DEFAULT_ENCODING, str)
    assert DEFAULT_ENCODING == 'utf-8'
    
    # Test costanti di anonimizzazione
    assert isinstance(ANONYMIZATION_METHODS, list)
    assert len(ANONYMIZATION_METHODS) > 0
    assert 'hash' in ANONYMIZATION_METHODS
    assert 'mask' in ANONYMIZATION_METHODS
    
    # Test campi sensibili
    assert isinstance(SENSITIVE_FIELDS, list)
    assert len(SENSITIVE_FIELDS) > 0
    assert 'password' in SENSITIVE_FIELDS
    assert 'email' in SENSITIVE_FIELDS
    
    print("✅ Costanti core test completato con successo")


def test_enums():
    """Test delle enumerazioni core."""
    print("🧪 Testando enumerazioni core...")
    
    # Test LogFormat
    assert LogFormat.CEF.value == "cef"
    assert LogFormat.SYSLOG.value == "syslog"
    assert LogFormat.from_string("CEF") == LogFormat.CEF
    assert LogFormat.from_string("invalid") == LogFormat.UNKNOWN
    assert LogFormat.JSON.is_structured() == True
    assert LogFormat.TXT.is_structured() == False
    
    # Test ParserType
    assert ParserType.CEF.value == "cef"
    assert ParserType.from_log_format(LogFormat.CEF) == ParserType.CEF
    assert ParserType.from_log_format(LogFormat.UNKNOWN) == ParserType.UNIVERSAL
    
    # Test AnonymizationMethod
    assert AnonymizationMethod.HASH.value == "hash"
    assert AnonymizationMethod.ENCRYPT.is_reversible() == True
    assert AnonymizationMethod.HASH.is_reversible() == False
    assert AnonymizationMethod.MASK.preserves_format() == True
    assert AnonymizationMethod.DELETE.preserves_format() == False
    
    # Test ProcessingStatus
    assert ProcessingStatus.COMPLETED.is_final() == True
    assert ProcessingStatus.PROCESSING.is_final() == False
    assert ProcessingStatus.COMPLETED.is_success() == True
    assert ProcessingStatus.FAILED.is_success() == False
    
    # Test ErrorSeverity
    assert ErrorSeverity.ERROR.requires_alert() == True
    assert ErrorSeverity.WARNING.requires_alert() == False
    assert ErrorSeverity.WARNING.allows_retry() == True
    assert ErrorSeverity.CRITICAL.allows_retry() == False
    
    print("✅ Enumerazioni core test completato con successo")


def test_validators():
    """Test dei validatori core."""
    print("🧪 Testando validatori core...")
    
    # Test ConfigValidator
    config_validator = ConfigValidator(strict_mode=False)
    
    # Configurazione valida
    valid_config = {
        'parsing': {
            'supported_formats': ['cef', 'syslog'],
            'timeout': 30
        },
        'output': {
            'format': 'json',
            'compression': 'none'
        },
        'anonymization': {
            'methods': ['hash', 'mask']
        }
    }
    
    assert config_validator.validate_config(valid_config) == True
    
    # Configurazione non valida
    invalid_config = {
        'parsing': {
            'timeout': -1  # Timeout negativo
        }
    }
    
    assert config_validator.validate_config(invalid_config) == False
    assert len(config_validator.errors) > 0
    
    # Test DataValidator
    data_validator = DataValidator()
    
    # Record valido
    valid_record = {
        'parser_type': 'CEF',
        'parsed_at': '2023-01-01T00:00:00',
        'cef_version': '0',
        'device_vendor': 'Test'
    }
    
    assert data_validator.validate_record(valid_record) == True
    
    # Record non valido
    invalid_record = {
        'parser_type': 'INVALID'  # Parser type non valido
    }
    
    assert data_validator.validate_record(invalid_record) == False
    
    # Test FileValidator
    file_validator = FileValidator(max_file_size=1024)
    
    # Crea file temporaneo per test
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"test content")
        temp_file = Path(f.name)
    
    try:
        assert file_validator.validate_file(temp_file) == True
    finally:
        temp_file.unlink()  # Pulisci file temporaneo
    
    # Test SchemaValidator
    schema_validator = SchemaValidator()
    
    # Dati validi per schema CEF
    valid_cef_data = {
        'cef_version': '0',
        'device_vendor': 'Test',
        'device_product': 'TestProduct',
        'name': 'TestEvent',
        'severity': '5'
    }
    
    assert schema_validator.validate_against_schema(valid_cef_data, 'cef') == True
    
    # Dati non validi per schema CEF
    invalid_cef_data = {
        'cef_version': '0'
        # Mancano campi obbligatori
    }
    
    assert schema_validator.validate_against_schema(invalid_cef_data, 'cef') == False
    
    print("✅ Validatori core test completato con successo")


def test_logger_service():
    """Test del LoggerService."""
    print("🧪 Testando LoggerService...")
    
    # Crea file temporaneo per log
    with tempfile.NamedTemporaryFile(delete=False, suffix='.log') as f:
        log_file = Path(f.name)
    
    try:
        # Test LoggerService
        logger = LoggerService(
            log_level="INFO",
            log_file=log_file,
            console_output=False,
            structured_logging=False
        )
        
        # Test logging
        logger.info("Test message")
        logger.warning("Test warning")
        logger.error("Test error")
        
        # Verifica che il file di log sia stato creato
        assert log_file.exists()
        assert log_file.stat().st_size > 0
        
        # Test statistiche
        stats = logger.get_statistics()
        assert stats['log_level'] == "INFO"
        assert stats['log_file'] == str(log_file)
        assert stats['console_output'] == False
        assert stats['structured_logging'] == False
        
        # Test cambio livello
        logger.set_level("DEBUG")
        assert logger.log_level == "DEBUG"
        
    finally:
        # Pulisci file temporaneo
        if log_file.exists():
            log_file.unlink()
    
    print("✅ LoggerService test completato con successo")


def main():
    """Esegue tutti i test per il Core Layer."""
    print("🚀 Iniziando test per il Core Layer...")
    print("=" * 60)
    
    try:
        test_exceptions()
        test_constants()
        test_enums()
        test_validators()
        test_logger_service()
        
        print("=" * 60)
        print("🎉 Tutti i test del Core Layer completati con successo!")
        print("✅ Il Core Layer è implementato correttamente")
        
    except Exception as e:
        print(f"❌ Errore durante i test: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main()) 