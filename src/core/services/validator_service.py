"""
Validator Service - Servizio di validazione centralizzato

Questo modulo fornisce un servizio di validazione centralizzato che
combina tutti i validatori del Core Layer per fornire un'interfaccia
unificata per la validazione di dati, configurazioni e file.

DESIGN:
- Interfaccia unificata per tutti i validatori
- Validazione batch e progressiva
- Reporting dettagliato degli errori
- Integrazione con logging e metriche

Author: Edoardo D'Alesio
Version: 1.0.0
"""

import time
from typing import Dict, List, Any, Optional, Union, Callable
from pathlib import Path
from datetime import datetime

from ..validators import ConfigValidator, DataValidator, FileValidator, SchemaValidator
from ..enums import ValidationLevel
from ..exceptions import ValidationError, ConfigurationError


class ValidatorService:
    """
    Servizio di validazione centralizzato per l'applicazione.
    
    WHY: Servizio centralizzato che combina tutti i validatori
    per fornire un'interfaccia unificata e semplificata.
    
    Contract:
        - Validazione di configurazioni, dati, file e schemi
        - Reporting dettagliato degli errori
        - Integrazione con logging e metriche
        - Supporto per validazione batch
    """
    
    def __init__(self, 
                 validation_level: ValidationLevel = ValidationLevel.BASIC,
                 enable_logging: bool = True,
                 enable_metrics: bool = True):
        """
        Inizializza il servizio di validazione.
        
        Args:
            validation_level: Livello di validazione da applicare
            enable_logging: Se True, logga errori di validazione
            enable_metrics: Se True, traccia metriche di validazione
        """
        self.validation_level = validation_level
        self.enable_logging = enable_logging
        self.enable_metrics = enable_metrics
        
        # Inizializza validatori
        self.config_validator = ConfigValidator(strict_mode=False)
        self.data_validator = DataValidator(validation_level=validation_level)
        self.file_validator = FileValidator()
        self.schema_validator = SchemaValidator()
        
        # Statistiche di validazione
        self.validation_stats = {
            'total_validations': 0,
            'successful_validations': 0,
            'failed_validations': 0,
            'total_errors': 0,
            'total_warnings': 0,
            'validation_time_total': 0.0
        }
    
    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida una configurazione completa.
        
        WHY: Metodo per validare configurazioni con reporting
        dettagliato e integrazione con logging.
        
        Args:
            config: Configurazione da validare
            
        Returns:
            Dizionario con risultati della validazione
        """
        start_time = time.time()
        
        try:
            # Validazione configurazione
            is_valid = self.config_validator.validate_config(config)
            
            # Prepara risultati
            result = {
                'valid': is_valid,
                'errors': self.config_validator.errors.copy(),
                'warnings': self.config_validator.warnings.copy(),
                'validation_time': time.time() - start_time,
                'validation_level': self.validation_level.value
            }
            
            # Aggiorna statistiche
            self._update_stats(is_valid, result['validation_time'], 
                             len(result['errors']), len(result['warnings']))
            
            return result
            
        except Exception as e:
            # Gestione errori inaspettati
            result = {
                'valid': False,
                'errors': [f"Errore inaspettato durante validazione: {str(e)}"],
                'warnings': [],
                'validation_time': time.time() - start_time,
                'validation_level': self.validation_level.value
            }
            
            self._update_stats(False, result['validation_time'], 1, 0)
            return result
    
    def validate_data(self, data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        Valida dati singoli o batch.
        
        WHY: Metodo per validare dati con supporto per
        validazione singola e batch per performance.
        
        Args:
            data: Dati da validare (singolo record o lista)
            
        Returns:
            Dizionario con risultati della validazione
        """
        start_time = time.time()
        
        if isinstance(data, dict):
            # Validazione singolo record
            is_valid = self.data_validator.validate_record(data)
            
            result = {
                'valid': is_valid,
                'errors': self.data_validator.errors.copy(),
                'warnings': self.data_validator.warnings.copy(),
                'validation_time': time.time() - start_time,
                'records_processed': 1,
                'valid_records': 1 if is_valid else 0,
                'invalid_records': 0 if is_valid else 1
            }
            
        else:
            # Validazione batch
            batch_result = self.data_validator.validate_batch(data)
            
            result = {
                'valid': batch_result['error_rate'] == 0,
                'errors': batch_result['errors'],
                'warnings': batch_result['warnings'],
                'validation_time': time.time() - start_time,
                'records_processed': batch_result['total_records'],
                'valid_records': batch_result['valid_records'],
                'invalid_records': batch_result['invalid_records'],
                'error_rate': batch_result['error_rate']
            }
        
        # Aggiorna statistiche
        self._update_stats(result['valid'], result['validation_time'],
                         len(result['errors']), len(result['warnings']))
        
        return result
    
    def validate_file(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Valida un singolo file.
        
        WHY: Metodo per validare file con controlli
        di accessibilità e conformità ai requisiti.
        
        Args:
            file_path: Percorso del file da validare
            
        Returns:
            Dizionario con risultati della validazione
        """
        start_time = time.time()
        
        try:
            is_valid = self.file_validator.validate_file(file_path)
            
            result = {
                'valid': is_valid,
                'errors': [],
                'warnings': [],
                'validation_time': time.time() - start_time,
                'file_path': str(file_path),
                'file_size': Path(file_path).stat().st_size if is_valid else 0
            }
            
        except ValidationError as e:
            result = {
                'valid': False,
                'errors': [str(e)],
                'warnings': [],
                'validation_time': time.time() - start_time,
                'file_path': str(file_path),
                'file_size': 0
            }
        
        # Aggiorna statistiche
        self._update_stats(result['valid'], result['validation_time'],
                         len(result['errors']), len(result['warnings']))
        
        return result
    
    def validate_directory(self, dir_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Valida una directory e restituisce i file validi.
        
        WHY: Metodo per processare directory intere
        e filtrare automaticamente file non validi.
        
        Args:
            dir_path: Percorso della directory da validare
            
        Returns:
            Dizionario con risultati della validazione
        """
        start_time = time.time()
        
        try:
            valid_files = self.file_validator.validate_directory(dir_path)
            
            result = {
                'valid': True,
                'errors': [],
                'warnings': [],
                'validation_time': time.time() - start_time,
                'directory_path': str(dir_path),
                'valid_files': [str(f) for f in valid_files],
                'total_files_found': len(valid_files)
            }
            
        except ValidationError as e:
            result = {
                'valid': False,
                'errors': [str(e)],
                'warnings': [],
                'validation_time': time.time() - start_time,
                'directory_path': str(dir_path),
                'valid_files': [],
                'total_files_found': 0
            }
        
        # Aggiorna statistiche
        self._update_stats(result['valid'], result['validation_time'],
                         len(result['errors']), len(result['warnings']))
        
        return result
    
    def validate_schema(self, data: Dict[str, Any], schema_name: str) -> Dict[str, Any]:
        """
        Valida dati contro uno schema specifico.
        
        WHY: Metodo per validare dati contro schemi
        predefiniti per diversi formati di log.
        
        Args:
            data: Dati da validare
            schema_name: Nome dello schema da utilizzare
            
        Returns:
            Dizionario con risultati della validazione
        """
        start_time = time.time()
        
        try:
            is_valid = self.schema_validator.validate_against_schema(data, schema_name)
            
            result = {
                'valid': is_valid,
                'errors': [],
                'warnings': [],
                'validation_time': time.time() - start_time,
                'schema_name': schema_name,
                'data_keys': list(data.keys()) if isinstance(data, dict) else []
            }
            
        except ValidationError as e:
            result = {
                'valid': False,
                'errors': [str(e)],
                'warnings': [],
                'validation_time': time.time() - start_time,
                'schema_name': schema_name,
                'data_keys': list(data.keys()) if isinstance(data, dict) else []
            }
        
        # Aggiorna statistiche
        self._update_stats(result['valid'], result['validation_time'],
                         len(result['errors']), len(result['warnings']))
        
        return result
    
    def validate_all(self, 
                    config: Optional[Dict[str, Any]] = None,
                    data: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None,
                    files: Optional[List[Union[str, Path]]] = None,
                    schemas: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Esegue validazione completa di tutti i tipi di dati.
        
        WHY: Metodo per validazione completa di un'intera
        configurazione o dataset con reporting aggregato.
        
        Args:
            config: Configurazione da validare (opzionale)
            data: Dati da validare (opzionale)
            files: File da validare (opzionale)
            schemas: Schemi da validare (opzionale)
            
        Returns:
            Dizionario con risultati completi della validazione
        """
        start_time = time.time()
        all_results = {}
        
        # Validazione configurazione
        if config is not None:
            all_results['config'] = self.validate_config(config)
        
        # Validazione dati
        if data is not None:
            all_results['data'] = self.validate_data(data)
        
        # Validazione file
        if files is not None:
            file_results = []
            for file_path in files:
                file_results.append(self.validate_file(file_path))
            all_results['files'] = file_results
        
        # Validazione schemi
        if schemas is not None:
            schema_results = []
            for schema_data in schemas:
                schema_name = schema_data.get('schema_name', 'unknown')
                data_to_validate = schema_data.get('data', {})
                schema_results.append(self.validate_schema(data_to_validate, schema_name))
            all_results['schemas'] = schema_results
        
        # Calcola risultati aggregati
        total_validation_time = time.time() - start_time
        all_valid = all(all_results.get(key, {}).get('valid', True) 
                       for key in all_results)
        
        # Aggrega errori e warning
        all_errors = []
        all_warnings = []
        
        for result_type, result in all_results.items():
            if isinstance(result, list):
                for item in result:
                    all_errors.extend(item.get('errors', []))
                    all_warnings.extend(item.get('warnings', []))
            else:
                all_errors.extend(result.get('errors', []))
                all_warnings.extend(result.get('warnings', []))
        
        return {
            'valid': all_valid,
            'validation_time_total': total_validation_time,
            'total_errors': len(all_errors),
            'total_warnings': len(all_warnings),
            'errors': all_errors,
            'warnings': all_warnings,
            'results': all_results
        }
    
    def _update_stats(self, is_valid: bool, validation_time: float, 
                     error_count: int, warning_count: int):
        """Aggiorna le statistiche di validazione."""
        self.validation_stats['total_validations'] += 1
        self.validation_stats['validation_time_total'] += validation_time
        
        if is_valid:
            self.validation_stats['successful_validations'] += 1
        else:
            self.validation_stats['failed_validations'] += 1
        
        self.validation_stats['total_errors'] += error_count
        self.validation_stats['total_warnings'] += warning_count
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Restituisce statistiche di validazione.
        
        WHY: Metodo per monitoring e debugging
        delle performance di validazione.
        
        Returns:
            Dizionario con statistiche di validazione
        """
        total_validations = self.validation_stats['total_validations']
        success_rate = 0.0
        avg_validation_time = 0.0
        
        if total_validations > 0:
            success_rate = (self.validation_stats['successful_validations'] / total_validations) * 100
            avg_validation_time = self.validation_stats['validation_time_total'] / total_validations
        
        return {
            'validation_level': self.validation_level.value,
            'total_validations': total_validations,
            'successful_validations': self.validation_stats['successful_validations'],
            'failed_validations': self.validation_stats['failed_validations'],
            'success_rate_percent': success_rate,
            'total_errors': self.validation_stats['total_errors'],
            'total_warnings': self.validation_stats['total_warnings'],
            'total_validation_time': self.validation_stats['validation_time_total'],
            'average_validation_time': avg_validation_time
        }
    
    def reset_stats(self):
        """Resetta le statistiche di validazione."""
        self.validation_stats = {
            'total_validations': 0,
            'successful_validations': 0,
            'failed_validations': 0,
            'total_errors': 0,
            'total_warnings': 0,
            'validation_time_total': 0.0
        }
    
    def set_validation_level(self, level: ValidationLevel):
        """
        Imposta il livello di validazione.
        
        Args:
            level: Nuovo livello di validazione
        """
        self.validation_level = level
        self.data_validator.validation_level = level 