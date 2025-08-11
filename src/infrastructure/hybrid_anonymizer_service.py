"""
Servizio di anonimizzazione ibrido che combina regex classico e Microsoft Presidio.
Permette di scegliere tra anonimizzazione classica, Presidio o ibrida.
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

from .presidio_service import PresidioService
from ..domain.interfaces.centralized_regex_service import CentralizedRegexService
from ..core.services.config_cache import ConfigCache


class HybridAnonymizerService:
    """
    Servizio di anonimizzazione ibrido che combina:
    - Anonimizzazione regex classica (sistema esistente)
    - Anonimizzazione Microsoft Presidio (AI-powered)
    - Modalità ibrida (combinazione di entrambi)
    
    Mantiene la configurazione regex centralizzata per compatibilità.
    """
    
    def __init__(self, config: Dict[str, Any], centralized_regex_service: Optional[CentralizedRegexService] = None):
        """
        Inizializza il servizio di anonimizzazione ibrido.
        
        Args:
            config: Configurazione dell'applicazione
            centralized_regex_service: Servizio regex centralizzato esistente
        """
        self.config = config
        self.centralized_regex_service = centralized_regex_service
        
        # Carica configurazione
        self.presidio_config = self._load_presidio_config()
        
        # Inizializza Presidio se abilitato
        if self.presidio_config.get('enabled', False):
            self.presidio_service = PresidioService(config, centralized_regex_service)
        else:
            self.presidio_service = None
        
        # Modalità di anonimizzazione
        self.anonymization_mode = self.presidio_config.get('anonymization_mode', 'classic')
        
        print(f"🔧 Hybrid Anonymizer Service inizializzato in modalità: {self.anonymization_mode}")
    
    def _load_presidio_config(self) -> Dict[str, Any]:
        """Carica la configurazione Presidio."""
        try:
            if self.centralized_regex_service:
                return self.centralized_regex_service.get_presidio_config()
            else:
                config_cache = ConfigCache()
                return config_cache.get_presidio_config()
        except Exception as e:
            print(f"⚠️ Errore nel caricamento configurazione Presidio: {e}")
            return {}
    
    def anonymize_content(self, content: str, mode: Optional[str] = None) -> Dict[str, Any]:
        """
        Anonimizza il contenuto usando la modalità specificata.
        
        Args:
            content: Contenuto da anonimizzare
            mode: Modalità di anonimizzazione (override configurazione)
            
        Returns:
            Dizionario con risultati dell'anonimizzazione
        """
        # Usa modalità specificata o quella di configurazione
        anonymization_mode = mode or self.anonymization_mode
        
        try:
            if anonymization_mode == "classic":
                return self._anonymize_classic(content)
            elif anonymization_mode == "presidio":
                return self._anonymize_presidio(content)
            elif anonymization_mode == "hybrid":
                return self._anonymize_hybrid(content)
            else:
                print(f"⚠️ Modalità di anonimizzazione non riconosciuta: {anonymization_mode}")
                return self._anonymize_classic(content)
                
        except Exception as e:
            print(f"❌ Errore nell'anonimizzazione ibrida: {e}")
            return {
                'success': False,
                'error': str(e),
                'original_content': content,
                'anonymized_content': content,
                'mode': anonymization_mode
            }
    
    def _anonymize_classic(self, content: str) -> Dict[str, Any]:
        """
        Anonimizzazione classica usando regex esistente.
        
        Args:
            content: Contenuto da anonimizzare
            
        Returns:
            Dizionario con risultati anonimizzazione classica
        """
        try:
            # Usa il servizio regex centralizzato esistente
            if self.centralized_regex_service:
                anonymized_content = self.centralized_regex_service.anonymize_content(content)
            else:
                # Fallback: usa pattern di base
                anonymized_content = self._fallback_regex_anonymization(content)
            
            return {
                'success': True,
                'mode': 'classic',
                'original_content': content,
                'anonymized_content': anonymized_content,
                'method': 'regex_patterns',
                'entities_detected': [],  # Regex non fornisce entità strutturate
                'anonymization_metadata': {
                    'method': 'classic_regex',
                    'patterns_applied': 'centralized_regex_service'
                }
            }
            
        except Exception as e:
            print(f"❌ Errore nell'anonimizzazione classica: {e}")
            return {
                'success': False,
                'error': str(e),
                'mode': 'classic',
                'original_content': content,
                'anonymized_content': content
            }
    
    def _anonymize_presidio(self, content: str) -> Dict[str, Any]:
        """
        Anonimizzazione usando solo Microsoft Presidio.
        
        Args:
            content: Contenuto da anonimizzare
            
        Returns:
            Dizionario con risultati anonimizzazione Presidio
        """
        if not self.presidio_service:
            print("⚠️ Presidio non disponibile, fallback a classico")
            return self._anonymize_classic(content)
        
        try:
            # Processa completo con Presidio
            presidio_result = self.presidio_service.process_with_presidio(content)
            
            if presidio_result.get('presidio_enabled', False) and 'error' not in presidio_result:
                return {
                    'success': True,
                    'mode': 'presidio',
                    'original_content': content,
                    'anonymized_content': presidio_result.get('anonymized_text', content),
                    'method': 'presidio_ai',
                    'entities_detected': presidio_result.get('entities_detected', []),
                    'anonymization_metadata': presidio_result.get('anonymization_metadata', []),
                    'datamining_insights': presidio_result.get('datamining_insights', {}),
                    'processing_metadata': presidio_result.get('processing_metadata', {})
                }
            else:
                print(f"⚠️ Presidio fallito: {presidio_result.get('error', 'Unknown error')}")
                return self._anonymize_classic(content)
                
        except Exception as e:
            print(f"❌ Errore nell'anonimizzazione Presidio: {e}")
            return self._anonymize_classic(content)
    
    def _anonymize_hybrid(self, content: str) -> Dict[str, Any]:
        """
        Anonimizzazione ibrida: processa il messaggio originale SEPARATAMENTE con entrambi i sistemi.
        
        IMPORTANTE: NON sovrappone le anonimizzazioni, ma fornisce entrambi i risultati separatamente.
        
        Args:
            content: Contenuto originale da anonimizzare
            
        Returns:
            Dizionario con entrambi i risultati di anonimizzazione separati
        """
        try:
            # 1. Anonimizzazione CLASSICA (regex) sul messaggio ORIGINALE
            classic_result = self._anonymize_classic(content)
            
            # 2. Anonimizzazione PRESIDIO (AI) sul messaggio ORIGINALE (non sul già anonimizzato)
            presidio_result = self._anonymize_presidio(content)
            
            # 3. Combina risultati mantenendo entrambi separati
            hybrid_result = {
                'success': True,
                'mode': 'hybrid',
                'original_content': content,
                
                # RISULTATI CLASSIC (regex)
                'classic_anonymization': {
                    'anonymized_content': classic_result.get('anonymized_content', content),
                    'method': 'classic_regex',
                    'entities_detected': classic_result.get('entities_detected', []),
                    'anonymization_metadata': classic_result.get('anonymization_metadata', {}),
                    'success': classic_result.get('success', False)
                },
                
                # RISULTATI PRESIDIO (AI)
                'presidio_anonymization': {
                    'anonymized_content': presidio_result.get('anonymized_content', content),
                    'method': 'presidio_ai',
                    'entities_detected': presidio_result.get('entities_detected', []),
                    'anonymization_metadata': presidio_result.get('anonymization_metadata', []),
                    'datamining_insights': presidio_result.get('datamining_insights', {}),
                    'success': presidio_result.get('success', False)
                },
                
                # METADATI COMBINATI
                'hybrid_metadata': {
                    'total_entities_classic': len(classic_result.get('entities_detected', [])),
                    'total_entities_presidio': len(presidio_result.get('entities_detected', [])),
                    'entities_types_classic': list(set(e.get('entity_type', '') for e in classic_result.get('entities_detected', []))),
                    'entities_types_presidio': list(set(e.get('entity_type', '') for e in presidio_result.get('entities_detected', []))),
                    'processing_method': 'separate_processing_original_content',
                    'comparison_notes': 'Entrambi i sistemi hanno processato il messaggio originale separatamente'
                },
                
                # INSIGHT DATAMINING COMBINATI
                'combined_datamining_insights': {
                    'classic_insights': {
                        'method': 'regex_patterns',
                        'patterns_applied': classic_result.get('anonymization_metadata', {}).get('patterns_applied', 'unknown')
                    },
                    'presidio_insights': presidio_result.get('datamining_insights', {}),
                    'comparison_analysis': {
                        'total_entities_detected': len(classic_result.get('entities_detected', [])) + len(presidio_result.get('entities_detected', [])),
                        'unique_entity_types': len(set(
                            list(set(e.get('entity_type', '') for e in classic_result.get('entities_detected', []))) +
                            list(set(e.get('entity_type', '') for e in presidio_result.get('entities_detected', [])))
                        )),
                        'coverage_analysis': 'Entrambi i sistemi forniscono copertura complementare'
                    }
                }
            }
            
            return hybrid_result
            
        except Exception as e:
            print(f"❌ Errore nell'anonimizzazione ibrida: {e}")
            return {
                'success': False,
                'error': str(e),
                'mode': 'hybrid',
                'original_content': content
            }
    
    def _fallback_regex_anonymization(self, content: str) -> str:
        """
        Anonimizzazione regex di fallback se il servizio centralizzato non è disponibile.
        
        Args:
            content: Contenuto da anonimizzare
            
        Returns:
            Contenuto anonimizzato
        """
        # Pattern di base per fallback
        fallback_patterns = {
            r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b': '<IP_ADDRESS>',
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b': '<EMAIL>',
            r'\b(?:[0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})\b': '<MAC_ADDRESS>',
            r'\b\d{5,}\b': '<NUMERIC_ID>',
            r'\b[A-Z]{2,}[A-Z0-9]{8,}\b': '<DEVICE_ID>',
            r'\b(?:mg-|dev-|prod-|test-)[a-zA-Z0-9_-]+\b': '<DEVICE_NAME>'
        }
        
        anonymized_content = content
        for pattern, replacement in fallback_patterns.items():
            anonymized_content = re.sub(pattern, replacement, anonymized_content)
        
        return anonymized_content
    
    def batch_anonymize(self, contents: List[str], mode: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Anonimizza un batch di contenuti.
        
        Args:
            contents: Lista di contenuti da anonimizzare
            mode: Modalità di anonimizzazione
            
        Returns:
            Lista di risultati per ogni contenuto
        """
        results = []
        
        for i, content in enumerate(contents):
            try:
                result = self.anonymize_content(content, mode)
                result['batch_index'] = i
                results.append(result)
                
                if i % 100 == 0:
                    print(f"   Processati {i}/{len(contents)} contenuti...")
                    
            except Exception as e:
                print(f"❌ Errore nell'anonimizzazione batch per contenuto {i}: {e}")
                results.append({
                    'success': False,
                    'error': str(e),
                    'original_content': content,
                    'anonymized_content': content,
                    'mode': mode or self.anonymization_mode,
                    'batch_index': i
                })
        
        return results
    
    def get_anonymization_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Genera un riepilogo dell'anonimizzazione.
        
        Args:
            results: Lista di risultati di anonimizzazione
            
        Returns:
            Dizionario con riepilogo statistiche
        """
        try:
            summary = {
                'total_processed': len(results),
                'successful': len([r for r in results if r.get('success', False)]),
                'failed': len([r for r in results if not r.get('success', False)]),
                'modes_used': {},
                'entities_detected': {},
                'performance_metrics': {}
            }
            
            # Statistiche per modalità
            for result in results:
                mode = result.get('mode', 'unknown')
                summary['modes_used'][mode] = summary['modes_used'].get(mode, 0) + 1
            
            # Statistiche entità rilevate
            total_entities = 0
            entity_types = set()
            for result in results:
                entities = result.get('entities_detected', [])
                total_entities += len(entities)
                for entity in entities:
                    entity_types.add(entity.get('entity_type', 'unknown'))
            
            summary['entities_detected'] = {
                'total_count': total_entities,
                'unique_types': len(entity_types),
                'types_list': list(entity_types)
            }
            
            # Metriche performance
            if results:
                content_lengths = [len(r.get('original_content', '')) for r in results]
                summary['performance_metrics'] = {
                    'average_content_length': sum(content_lengths) / len(content_lengths),
                    'total_content_length': sum(content_lengths),
                    'success_rate': (summary['successful'] / summary['total_processed']) * 100
                }
            
            return summary
            
        except Exception as e:
            print(f"❌ Errore nella generazione riepilogo: {e}")
            return {
                'error': str(e),
                'total_processed': len(results)
            }
    
    def get_configuration_summary(self) -> Dict[str, Any]:
        """Ottiene un riepilogo della configurazione del servizio."""
        return {
            'anonymization_mode': self.anonymization_mode,
            'presidio_enabled': self.presidio_service is not None,
            'centralized_regex_available': self.centralized_regex_service is not None,
            'presidio_config': self.presidio_config if self.presidio_service else None
        }
