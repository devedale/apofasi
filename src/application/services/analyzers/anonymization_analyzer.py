"""
Analizzatore per statistiche di anonimizzazione.

Questo modulo fornisce analisi dettagliate sui processi di
anonimizzazione, inclusi tassi di anonimizzazione, metodi
utilizzati e campi più frequentemente anonimizzati.

Author: Edoardo D'Alesio
Version: 1.0.0
"""

from collections import Counter, defaultdict
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from src.core import LoggerService


@dataclass
class AnonymizationStats:
    """Statistiche complete sull'anonimizzazione."""
    total_anonymized: int
    anonymization_rate: float
    fields_anonymized: Dict[str, int]
    anonymization_methods: Dict[str, int]
    sensitive_fields_detected: List[str]
    anonymization_quality: Dict[str, float]
    privacy_compliance: Dict[str, bool]


class AnonymizationAnalyzer:
    """
    Analizzatore per statistiche di anonimizzazione.
    
    WHY: Fornisce visibilità sui processi di anonimizzazione
    per garantire compliance privacy e qualità dei dati.
    """
    
    def __init__(self, logger: Optional[LoggerService] = None):
        """
        Inizializza l'analizzatore di anonimizzazione.
        
        Args:
            logger: Servizio di logging opzionale
        """
        self.logger = logger or LoggerService()
    
    def analyze(self, results: List[Dict[str, Any]]) -> AnonymizationStats:
        """
        Analizza i risultati per statistiche di anonimizzazione.
        
        WHY: Monitora l'efficacia dell'anonimizzazione per
        garantire la protezione dei dati sensibili.
        
        Args:
            results: Lista dei risultati parsati
            
        Returns:
            Statistiche di anonimizzazione
        """
        if not results:
            self.logger.warning("Nessun risultato da analizzare per anonimizzazione")
            return self._create_empty_stats()
        
        self.logger.info(f"Analizzando anonimizzazione per {len(results)} record")
        
        # Contatori base
        total_records = len(results)
        anonymized_records = sum(1 for r in results if r.get('anonymized', False))
        anonymization_rate = (anonymized_records / total_records) * 100 if total_records > 0 else 0
        
        # Analisi campi anonimizzati
        fields_anonymized = self._analyze_anonymized_fields(results)
        
        # Analisi metodi di anonimizzazione
        anonymization_methods = self._analyze_anonymization_methods(results)
        
        # Campi sensibili rilevati
        sensitive_fields = self._detect_sensitive_fields(results)
        
        # Qualità dell'anonimizzazione
        anonymization_quality = self._assess_anonymization_quality(results)
        
        # Compliance privacy
        privacy_compliance = self._check_privacy_compliance(results)
        
        stats = AnonymizationStats(
            total_anonymized=anonymized_records,
            anonymization_rate=anonymization_rate,
            fields_anonymized=fields_anonymized,
            anonymization_methods=anonymization_methods,
            sensitive_fields_detected=sensitive_fields,
            anonymization_quality=anonymization_quality,
            privacy_compliance=privacy_compliance
        )
        
        self.logger.info(f"Anonimizzazione: {anonymized_records}/{total_records} record ({anonymization_rate:.1f}%)")
        
        return stats
    
    def _analyze_anonymized_fields(self, results: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Analizza i campi anonimizzati.
        
        Args:
            results: Lista dei risultati
            
        Returns:
            Conteggio campi anonimizzati per tipo
        """
        field_counter = Counter()
        
        for result in results:
            if result.get('anonymized', False):
                anonymized_fields = result.get('anonymized_fields', [])
                for field in anonymized_fields:
                    if isinstance(field, dict):
                        field_name = field.get('name', 'unknown')
                    else:
                        field_name = str(field)
                    field_counter[field_name] += 1
        
        return dict(field_counter)
    
    def _analyze_anonymization_methods(self, results: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Analizza i metodi di anonimizzazione utilizzati.
        
        Args:
            results: Lista dei risultati
            
        Returns:
            Conteggio metodi di anonimizzazione
        """
        method_counter = Counter()
        
        for result in results:
            if result.get('anonymized', False):
                anonymization_info = result.get('anonymization_info', {})
                methods = anonymization_info.get('methods', [])
                
                for method in methods:
                    if isinstance(method, dict):
                        method_name = method.get('type', 'unknown')
                    else:
                        method_name = str(method)
                    method_counter[method_name] += 1
        
        return dict(method_counter)
    
    def _detect_sensitive_fields(self, results: List[Dict[str, Any]]) -> List[str]:
        """
        Rileva campi potenzialmente sensibili.
        
        Args:
            results: Lista dei risultati
            
        Returns:
            Lista di campi sensibili rilevati
        """
        sensitive_patterns = {
            'email': ['email', 'mail', 'e-mail'],
            'phone': ['phone', 'tel', 'telephone', 'mobile'],
            'ip': ['ip', 'ip_address', 'source_ip', 'dest_ip'],
            'ssn': ['ssn', 'social_security'],
            'credit_card': ['credit_card', 'card_number', 'cc_number'],
            'password': ['password', 'pwd', 'pass'],
            'username': ['username', 'user', 'login'],
            'address': ['address', 'street', 'city', 'zip'],
            'name': ['name', 'first_name', 'last_name', 'full_name']
        }
        
        detected_fields = set()
        
        for result in results:
            parsed_data = result.get('parsed_data', {})
            
            # Gestisci sia dizionari che liste
            if isinstance(parsed_data, list):
                # Se è una lista, prendi il primo elemento come esempio
                if parsed_data and isinstance(parsed_data[0], dict):
                    sample_data = parsed_data[0]
                else:
                    continue
            elif isinstance(parsed_data, dict):
                sample_data = parsed_data
            else:
                continue
            
            for field_name in sample_data.keys():
                field_lower = field_name.lower()
                
                for sensitive_type, patterns in sensitive_patterns.items():
                    if any(pattern in field_lower for pattern in patterns):
                        detected_fields.add(field_name)
        
        return list(detected_fields)
    
    def _assess_anonymization_quality(self, results: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Valuta la qualità dell'anonimizzazione.
        
        Args:
            results: Lista dei risultati
            
        Returns:
            Metriche di qualità dell'anonimizzazione
        """
        quality_metrics = {
            'completeness': 0.0,  # Percentuale di record anonimizzati
            'consistency': 0.0,    # Consistenza dei metodi
            'effectiveness': 0.0,  # Efficacia nel proteggere dati sensibili
            'reversibility': 0.0   # Irreversibilità dell'anonimizzazione
        }
        
        if not results:
            return quality_metrics
        
        total_records = len(results)
        anonymized_records = sum(1 for r in results if r.get('anonymized', False))
        
        # Completezza
        quality_metrics['completeness'] = (anonymized_records / total_records) * 100
        
        # Consistenza (stesso metodo per stessi tipi di dati)
        consistency_score = self._calculate_consistency_score(results)
        quality_metrics['consistency'] = consistency_score
        
        # Efficacia (protezione dati sensibili)
        effectiveness_score = self._calculate_effectiveness_score(results)
        quality_metrics['effectiveness'] = effectiveness_score
        
        # Irreversibilità
        reversibility_score = self._calculate_reversibility_score(results)
        quality_metrics['reversibility'] = reversibility_score
        
        return quality_metrics
    
    def _calculate_consistency_score(self, results: List[Dict[str, Any]]) -> float:
        """
        Calcola il punteggio di consistenza.
        
        Args:
            results: Lista dei risultati
            
        Returns:
            Punteggio di consistenza (0-100)
        """
        method_by_field = defaultdict(set)
        
        for result in results:
            if result.get('anonymized', False):
                anonymization_info = result.get('anonymization_info', {})
                field_methods = anonymization_info.get('field_methods', {})
                
                for field, method in field_methods.items():
                    method_by_field[field].add(method)
        
        # Calcola consistenza: meno metodi diversi per campo = più consistente
        total_fields = len(method_by_field)
        if total_fields == 0:
            return 100.0
        
        consistency_score = 0.0
        for field, methods in method_by_field.items():
            # Se un campo ha sempre lo stesso metodo, è consistente
            if len(methods) == 1:
                consistency_score += 1.0
        
        return (consistency_score / total_fields) * 100
    
    def _calculate_effectiveness_score(self, results: List[Dict[str, Any]]) -> float:
        """
        Calcola il punteggio di efficacia.
        
        Args:
            results: Lista dei risultati
            
        Returns:
            Punteggio di efficacia (0-100)
        """
        sensitive_fields = self._detect_sensitive_fields(results)
        protected_fields = 0
        
        for result in results:
            if result.get('anonymized', False):
                anonymized_fields = result.get('anonymized_fields', [])
                for field in anonymized_fields:
                    if isinstance(field, dict):
                        field_name = field.get('name', '')
                    else:
                        field_name = str(field)
                    
                    if field_name in sensitive_fields:
                        protected_fields += 1
        
        total_sensitive = len(sensitive_fields) * len(results)
        if total_sensitive == 0:
            return 100.0
        
        return (protected_fields / total_sensitive) * 100
    
    def _calculate_reversibility_score(self, results: List[Dict[str, Any]]) -> float:
        """
        Calcola il punteggio di irreversibilità.
        
        Args:
            results: Lista dei risultati
            
        Returns:
            Punteggio di irreversibilità (0-100)
        """
        irreversible_methods = ['hash', 'encryption', 'masking']
        reversible_methods = ['replacement', 'substitution']
        
        irreversible_count = 0
        total_anonymized = 0
        
        for result in results:
            if result.get('anonymized', False):
                anonymization_info = result.get('anonymization_info', {})
                methods = anonymization_info.get('methods', [])
                
                for method in methods:
                    total_anonymized += 1
                    if isinstance(method, dict):
                        method_type = method.get('type', '')
                    else:
                        method_type = str(method)
                    
                    if method_type in irreversible_methods:
                        irreversible_count += 1
        
        if total_anonymized == 0:
            return 100.0
        
        return (irreversible_count / total_anonymized) * 100
    
    def _check_privacy_compliance(self, results: List[Dict[str, Any]]) -> Dict[str, bool]:
        """
        Verifica la compliance privacy.
        
        Args:
            results: Lista dei risultati
            
        Returns:
            Dizionario con compliance per categoria
        """
        compliance = {
            'gdpr_compliant': False,
            'data_minimization': False,
            'purpose_limitation': False,
            'storage_limitation': False
        }
        
        # GDPR compliance check
        anonymized_records = sum(1 for r in results if r.get('anonymized', False))
        total_records = len(results)
        
        if total_records > 0:
            anonymization_rate = (anonymized_records / total_records) * 100
            compliance['gdpr_compliant'] = anonymization_rate >= 90.0  # 90% anonimizzato
            compliance['data_minimization'] = anonymization_rate >= 80.0  # 80% minimizzato
        
        # Purpose limitation (non implementato completamente)
        compliance['purpose_limitation'] = True  # Placeholder
        
        # Storage limitation (non implementato completamente)
        compliance['storage_limitation'] = True  # Placeholder
        
        return compliance
    
    def _create_empty_stats(self) -> AnonymizationStats:
        """
        Crea statistiche vuote quando non ci sono risultati.
        
        Returns:
            Statistiche vuote
        """
        return AnonymizationStats(
            total_anonymized=0,
            anonymization_rate=0.0,
            fields_anonymized={},
            anonymization_methods={},
            sensitive_fields_detected=[],
            anonymization_quality={
                'completeness': 0.0,
                'consistency': 0.0,
                'effectiveness': 0.0,
                'reversibility': 0.0
            },
            privacy_compliance={
                'gdpr_compliant': False,
                'data_minimization': False,
                'purpose_limitation': False,
                'storage_limitation': False
            }
        ) 