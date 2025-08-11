"""
Servizio Microsoft Presidio integrato per analisi PII e datamining.
Integra Presidio Analyzer e Anonymizer mantenendo la configurazione regex centralizzata.
"""

import json
import hashlib
import re
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

from presidio_analyzer import AnalyzerEngine, BatchAnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import RecognizerResult, OperatorConfig
from presidio_anonymizer.operators import OperatorType

from ..domain.interfaces.centralized_regex_service import CentralizedRegexService
from ..core.services.config_cache import ConfigCache


class PresidioService:
    """
    Servizio Microsoft Presidio integrato per analisi PII e datamining.
    
    Caratteristiche:
    - Analisi PII avanzata con AI/ML
    - Anonimizzazione intelligente
    - Estrazione dati per datamining
    - Integrazione con sistema regex esistente
    - Configurazione centralizzata
    """
    
    def __init__(self, config: Dict[str, Any], centralized_regex_service: Optional[CentralizedRegexService] = None):
        """
        Inizializza il servizio Presidio.
        
        Args:
            config: Configurazione dell'applicazione
            centralized_regex_service: Servizio regex centralizzato esistente
        """
        self.config = config
        self.centralized_regex_service = centralized_regex_service
        
        # Carica configurazione Presidio
        self.presidio_config = self._load_presidio_config()
        
        # Inizializza Presidio se abilitato
        if self.presidio_config.get('enabled', False):
            self._initialize_presidio()
        else:
            self.analyzer_engine = None
            self.anonymizer_engine = None
            self.batch_analyzer = None
    
    def _load_presidio_config(self) -> Dict[str, Any]:
        """Carica la configurazione Presidio dalla cache."""
        try:
            if self.centralized_regex_service:
                return self.centralized_regex_service.get_presidio_config()
            else:
                config_cache = ConfigCache()
                return config_cache.get_presidio_config()
        except Exception as e:
            print(f"⚠️ Errore nel caricamento configurazione Presidio: {e}")
            return {}
    
    def _initialize_presidio(self):
        """Inizializza i componenti Presidio."""
        try:
            # Configurazione NLP Engine
            nlp_config = {
                "nlp_engine_name": "spacy",
                "models": [
                    {
                        "lang_code": "en",
                        "model_name": "en_core_web_sm"
                    },
                    {
                        "lang_code": "it", 
                        "model_name": "it_core_news_sm"
                    }
                ]
            }
            
            # Crea NLP Engine Provider
            nlp_engine_provider = NlpEngineProvider(nlp_config=nlp_config)
            nlp_engine = nlp_engine_provider.create_engine()
            
            # Crea Analyzer Engine
            self.analyzer_engine = AnalyzerEngine(
                nlp_engine=nlp_engine,
                supported_languages=self.presidio_config.get('analyzer', {}).get('languages', ['en'])
            )
            
            # Crea Batch Analyzer per performance
            if self.presidio_config.get('analyzer', {}).get('performance', {}).get('enable_batch', True):
                self.batch_analyzer = BatchAnalyzerEngine(
                    nlp_engine=nlp_engine,
                    supported_languages=self.presidio_config.get('analyzer', {}).get('languages', ['en'])
                )
            
            # Crea Anonymizer Engine
            self.anonymizer_engine = AnonymizerEngine()
            
            print("✅ Presidio inizializzato con successo")
            
        except Exception as e:
            print(f"❌ Errore nell'inizializzazione di Presidio: {e}")
            self.analyzer_engine = None
            self.anonymizer_engine = None
            self.batch_analyzer = None
    
    def analyze_text(self, text: str, language: str = "en") -> List[Dict[str, Any]]:
        """
        Analizza il testo per rilevare entità PII.
        
        Args:
            text: Testo da analizzare
            language: Lingua del testo
            
        Returns:
            Lista di entità rilevate con metadati
        """
        if not self.analyzer_engine:
            print("⚠️ Presidio non inizializzato, impossibile analizzare")
            return []
        
        try:
            # Ottieni configurazione entità
            entities_config = self.presidio_config.get('analyzer', {}).get('entities', {})
            confidence_threshold = self.presidio_config.get('analyzer', {}).get('analysis', {}).get('confidence_threshold', 0.7)
            
            # Filtra entità abilitate
            enabled_entities = [entity for entity, enabled in entities_config.items() if enabled]
            
            # Analizza con Presidio
            results = self.analyzer_engine.analyze(
                text=text,
                language=language,
                entities=enabled_entities
            )
            
            # Filtra per confidence e formatta risultati
            filtered_results = []
            for result in results:
                if result.score >= confidence_threshold:
                    entity_info = {
                        'entity_type': result.entity_type,
                        'text': result.text,
                        'start': result.start,
                        'end': result.end,
                        'score': result.score,
                        'analysis_explanation': result.analysis_explanation,
                        'recognition_metadata': result.recognition_metadata
                    }
                    filtered_results.append(entity_info)
            
            return filtered_results
            
        except Exception as e:
            print(f"❌ Errore nell'analisi Presidio: {e}")
            return []
    
    def analyze_batch(self, texts: List[str], language: str = "en") -> List[List[Dict[str, Any]]]:
        """
        Analizza un batch di testi per performance ottimizzata.
        
        Args:
            texts: Lista di testi da analizzare
            language: Lingua dei testi
            
        Returns:
            Lista di risultati per ogni testo
        """
        if not self.batch_analyzer:
            print("⚠️ Batch Analyzer non disponibile, uso analisi singola")
            return [self.analyze_text(text, language) for text in texts]
        
        try:
            # Configura batch size
            batch_size = self.presidio_config.get('analyzer', {}).get('performance', {}).get('batch_size', 1000)
            
            # Analizza in batch
            batch_results = []
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                batch_analysis = self.batch_analyzer.analyze(
                    texts=batch,
                    language=language,
                    entities=self._get_enabled_entities()
                )
                
                # Formatta risultati batch
                for text_results in batch_analysis:
                    filtered_results = []
                    for result in text_results:
                        if result.score >= self._get_confidence_threshold():
                            entity_info = {
                                'entity_type': result.entity_type,
                                'text': result.text,
                                'start': result.start,
                                'end': result.end,
                                'score': result.score,
                                'analysis_explanation': result.analysis_explanation,
                                'recognition_metadata': result.recognition_metadata
                            }
                            filtered_results.append(entity_info)
                    batch_results.append(filtered_results)
            
            return batch_results
            
        except Exception as e:
            print(f"❌ Errore nell'analisi batch Presidio: {e}")
            return [self.analyze_text(text, language) for text in texts]
    
    def anonymize_text(self, text: str, entities: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Anonimizza il testo basandosi sulle entità rilevate.
        
        Args:
            text: Testo da anonimizzare
            entities: Entità rilevate da Presidio
            
        Returns:
            Tupla (testo anonimizzato, metadati anonimizzazione)
        """
        if not self.anonymizer_engine:
            print("⚠️ Presidio Anonymizer non inizializzato, impossibile anonimizzare")
            return text, []
        
        try:
            # Converti entità in formato Presidio
            recognizer_results = []
            for entity in entities:
                recognizer_result = RecognizerResult(
                    entity_type=entity['entity_type'],
                    start=entity['start'],
                    end=entity['end'],
                    score=entity['score']
                )
                recognizer_results.append(recognizer_result)
            
            # Ottieni configurazione strategie
            strategies_config = self.presidio_config.get('anonymizer', {}).get('strategies', {})
            strategy_config = self.presidio_config.get('anonymizer', {}).get('strategy_config', {})
            
            # Crea configurazioni operatori
            operator_configs = []
            for entity in entities:
                entity_type = entity['entity_type']
                strategy = strategies_config.get(entity_type, 'replace')
                
                if strategy == 'replace':
                    placeholder = strategy_config.get('replace', {}).get('placeholders', {}).get(entity_type, f"<{entity_type}>")
                    operator_config = OperatorConfig(
                        "replace",
                        {"new_value": placeholder}
                    )
                elif strategy == 'hash':
                    hash_config = strategy_config.get('hash', {})
                    algorithm = hash_config.get('algorithm', 'sha256')
                    salt = hash_config.get('salt', 'presidio_salt_2025')
                    include_type = hash_config.get('include_entity_type', True)
                    truncate_length = hash_config.get('truncate_length', 16)
                    
                    # Crea hash
                    hash_input = f"{entity['text']}:{entity_type}:{salt}" if include_type else f"{entity['text']}:{salt}"
                    hash_value = hashlib.new(algorithm, hash_input.encode()).hexdigest()[:truncate_length]
                    
                    operator_config = OperatorConfig(
                        "replace",
                        {"new_value": f"<HASH_{algorithm.upper()}_{hash_value}>"}
                    )
                elif strategy == 'mask':
                    mask_config = strategy_config.get('mask', {})
                    mask_char = mask_config.get('mask_char', '*')
                    mask_ratio = mask_config.get('mask_ratio', 0.7)
                    
                    # Calcola caratteri da mascherare
                    text_length = len(entity['text'])
                    mask_count = int(text_length * mask_ratio)
                    mask_start = (text_length - mask_count) // 2
                    
                    masked_text = entity['text'][:mask_start] + mask_char * mask_count + entity['text'][mask_start + mask_count:]
                    
                    operator_config = OperatorConfig(
                        "replace",
                        {"new_value": masked_text}
                    )
                else:  # keep
                    operator_config = OperatorConfig("keep", {})
                
                operator_configs.append(operator_config)
            
            # Anonimizza
            anonymized_result = self.anonymizer_engine.anonymize(
                text=text,
                analyzer_results=recognizer_results,
                operators=operator_configs
            )
            
            # Formatta metadati
            anonymization_metadata = []
            for i, entity in enumerate(entities):
                metadata = {
                    'original_entity': entity,
                    'anonymization_strategy': strategies_config.get(entity['entity_type'], 'replace'),
                    'operator_config': operator_configs[i].to_dict() if i < len(operator_configs) else {}
                }
                anonymization_metadata.append(metadata)
            
            return anonymized_result.text, anonymization_metadata
            
        except Exception as e:
            print(f"❌ Errore nell'anonimizzazione Presidio: {e}")
            return text, []
    
    def extract_datamining_insights(self, entities: List[Dict[str, Any]], text: str) -> Dict[str, Any]:
        """
        Estrae insight per datamining dalle entità rilevate.
        
        Args:
            entities: Entità rilevate da Presidio
            text: Testo originale
            
        Returns:
            Dizionario con insight per datamining
        """
        if not self.presidio_config.get('datamining', {}).get('enabled', False):
            return {}
        
        try:
            insights = {
                'entity_summary': {},
                'patterns': {},
                'metrics': {},
                'relationships': {},
                'timeline': {},
                'geographic': {},
                'security': {},
                'business': {},
                'technical': {}
            }
            
            # Raggruppa entità per tipo
            entity_counts = {}
            entity_texts = {}
            
            for entity in entities:
                entity_type = entity['entity_type']
                entity_counts[entity_type] = entity_counts.get(entity_type, 0) + 1
                
                if entity_type not in entity_texts:
                    entity_texts[entity_type] = []
                entity_texts[entity_type].append(entity['text'])
            
            # Riepilogo entità
            insights['entity_summary'] = {
                'total_entities': len(entities),
                'unique_entity_types': len(entity_counts),
                'entity_distribution': entity_counts,
                'entity_examples': entity_texts
            }
            
            # Pattern temporali
            temporal_entities = ['DATE_TIME', 'DATE', 'TIME']
            temporal_data = [e for e in entities if e['entity_type'] in temporal_entities]
            if temporal_data:
                insights['patterns']['temporal'] = {
                    'count': len(temporal_data),
                    'types': list(set(e['entity_type'] for e in temporal_data)),
                    'values': [e['text'] for e in temporal_data]
                }
            
            # Pattern geografici
            geographic_entities = ['LOCATION', 'ADDRESS', 'CITY', 'COUNTRY', 'ZIP_CODE']
            geographic_data = [e for e in entities if e['entity_type'] in geographic_entities]
            if geographic_data:
                insights['patterns']['geographic'] = {
                    'count': len(geographic_data),
                    'types': list(set(e['entity_type'] for e in geographic_data)),
                    'values': [e['text'] for e in geographic_data]
                }
            
            # Pattern di sicurezza
            security_entities = ['PASSWORD', 'SECRET_KEY', 'ACCESS_TOKEN', 'CREDIT_CARD', 'IBAN_CODE']
            security_data = [e for e in entities if e['entity_type'] in security_entities]
            if security_data:
                insights['security']['sensitive_data'] = {
                    'count': len(security_data),
                    'types': list(set(e['entity_type'] for e in security_data)),
                    'risk_level': 'HIGH' if len(security_data) > 0 else 'LOW'
                }
            
            # Pattern di rete
            network_entities = ['IP_ADDRESS', 'DOMAIN_NAME', 'URL', 'MAC_ADDRESS', 'HOSTNAME']
            network_data = [e for e in entities if e['entity_type'] in network_entities]
            if network_data:
                insights['patterns']['network'] = {
                    'count': len(network_data),
                    'types': list(set(e['entity_type'] for e in network_data)),
                    'values': [e['text'] for e in network_data]
                }
            
            # Metriche generali
            insights['metrics'] = {
                'text_length': len(text),
                'entity_density': len(entities) / len(text) if len(text) > 0 else 0,
                'confidence_average': sum(e['score'] for e in entities) / len(entities) if entities else 0,
                'confidence_distribution': {
                    'high': len([e for e in entities if e['score'] >= 0.8]),
                    'medium': len([e for e in entities if 0.6 <= e['score'] < 0.8]),
                    'low': len([e for e in entities if e['score'] < 0.6])
                }
            }
            
            # Insight di business
            business_entities = ['ORGANIZATION', 'COMPANY', 'JOB_TITLE', 'PERSON']
            business_data = [e for e in entities if e['entity_type'] in business_entities]
            if business_data:
                insights['business']['organizational'] = {
                    'count': len(business_data),
                    'types': list(set(e['entity_type'] for e in business_data)),
                    'values': [e['text'] for e in business_data]
                }
            
            # Insight tecnici
            technical_entities = ['ID', 'KEY', 'UUID', 'PROCESS_ID', 'SESSION_ID']
            technical_data = [e for e in entities if e['entity_type'] in technical_entities]
            if technical_data:
                insights['technical']['identifiers'] = {
                    'count': len(technical_data),
                    'types': list(set(e['entity_type'] for e in technical_data)),
                    'values': [e['text'] for e in technical_data]
                }
            
            return insights
            
        except Exception as e:
            print(f"❌ Errore nell'estrazione insight datamining: {e}")
            return {}
    
    def process_with_presidio(self, text: str, language: str = "en") -> Dict[str, Any]:
        """
        Processa completo con Presidio: analisi, anonimizzazione e datamining.
        
        Args:
            text: Testo da processare
            language: Lingua del testo
            
        Returns:
            Dizionario completo con risultati
        """
        if not self.presidio_config.get('enabled', False):
            return {
                'presidio_enabled': False,
                'error': 'Presidio non abilitato'
            }
        
        try:
            # 1. Analisi entità
            entities = self.analyze_text(text, language)
            
            # 2. Anonimizzazione
            anonymized_text, anonymization_metadata = self.anonymize_text(text, entities)
            
            # 3. Estrazione insight datamining
            datamining_insights = self.extract_datamining_insights(entities, text)
            
            # 4. Risultato completo
            result = {
                'presidio_enabled': True,
                'original_text': text,
                'anonymized_text': anonymized_text,
                'entities_detected': entities,
                'anonymization_metadata': anonymization_metadata,
                'datamining_insights': datamining_insights,
                'processing_metadata': {
                    'language': language,
                    'text_length': len(text),
                    'entities_count': len(entities),
                    'anonymization_strategy': self.presidio_config.get('anonymization_mode', 'hybrid')
                }
            }
            
            return result
            
        except Exception as e:
            print(f"❌ Errore nel processing Presidio completo: {e}")
            return {
                'presidio_enabled': True,
                'error': str(e),
                'original_text': text
            }
    
    def _get_enabled_entities(self) -> List[str]:
        """Ottiene la lista delle entità abilitate."""
        entities_config = self.presidio_config.get('analyzer', {}).get('entities', {})
        return [entity for entity, enabled in entities_config.items() if enabled]
    
    def _get_confidence_threshold(self) -> float:
        """Ottiene la soglia di confidenza."""
        return self.presidio_config.get('analyzer', {}).get('analysis', {}).get('confidence_threshold', 0.7)
    
    def get_configuration_summary(self) -> Dict[str, Any]:
        """Ottiene un riepilogo della configurazione Presidio."""
        return {
            'enabled': self.presidio_config.get('enabled', False),
            'anonymization_mode': self.presidio_config.get('anonymization_mode', 'hybrid'),
            'languages': self.presidio_config.get('analyzer', {}).get('languages', []),
            'enabled_entities': self._get_enabled_entities(),
            'confidence_threshold': self._get_confidence_threshold(),
            'datamining_enabled': self.presidio_config.get('datamining', {}).get('enabled', False),
            'performance': {
                'batch_enabled': self.presidio_config.get('analyzer', {}).get('performance', {}).get('enable_batch', False),
                'parallel_enabled': self.presidio_config.get('analyzer', {}).get('performance', {}).get('enable_parallel', False),
                'caching_enabled': self.presidio_config.get('analyzer', {}).get('performance', {}).get('enable_caching', False)
            }
        }
