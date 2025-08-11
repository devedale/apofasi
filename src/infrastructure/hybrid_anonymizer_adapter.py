"""
Adapter per integrare il servizio di anonimizzazione ibrido nel sistema esistente.
Questo adapter implementa l'interfaccia Anonymizer per mantenere la compatibilità.
"""

from typing import Dict, Any, Optional
from ..domain.interfaces.anonymizer import Anonymizer
from .hybrid_anonymizer_service import HybridAnonymizerService
from ..domain.services.centralized_regex_service import CentralizedRegexService


class HybridAnonymizerAdapter(Anonymizer):
    """
    Adapter che integra il servizio di anonimizzazione ibrido nel sistema esistente.
    
    Questo adapter implementa l'interfaccia Anonymizer per mantenere la compatibilità
    con il LogProcessingService esistente, ma internamente usa il servizio ibrido
    per fornire anonimizzazione Presidio oltre a quella regex.
    """
    
    def __init__(self, config: Dict[str, Any], centralized_regex_service: Optional[CentralizedRegexService] = None):
        """
        Inizializza l'adapter.
        
        Args:
            config: Configurazione dell'applicazione
            centralized_regex_service: Servizio regex centralizzato
        """
        self.config = config
        self.centralized_regex_service = centralized_regex_service
        
        # Inizializza il servizio ibrido se Presidio è abilitato
        self.hybrid_service = None
        if config.get('presidio', {}).get('enabled', False):
            try:
                from .hybrid_anonymizer_service import HybridAnonymizerService
                self.hybrid_service = HybridAnonymizerService(config, centralized_regex_service)
            except Exception as e:
                print(f"⚠️ Presidio non disponibile nell'adapter: {e}")
                self.hybrid_service = None
        
        # Modalità di anonimizzazione (default: hybrid)
        self.anonymization_mode = config.get('presidio', {}).get('anonymization_mode', 'hybrid')
        
        # Fallback al regex classico se Presidio non è disponibile
        if not self.hybrid_service:
            from .anonymizer import RegexAnonymizer
            self.fallback_anonymizer = RegexAnonymizer(config, centralized_regex_service=centralized_regex_service)
        else:
            self.fallback_anonymizer = None
    
    def anonymize(self, text: str, **kwargs) -> str:
        """
        Anonimizza il testo usando il servizio ibrido se disponibile.
        
        Args:
            text: Testo da anonimizzare
            **kwargs: Argomenti aggiuntivi
            
        Returns:
            Testo anonimizzato
        """
        if self.hybrid_service:
            try:
                # Usa il servizio ibrido
                result = self.hybrid_service.anonymize_content(text, mode=self.anonymization_mode)
                
                if self.anonymization_mode == 'hybrid':
                    # Modalità ibrida: restituisci il risultato classic per compatibilità
                    return result.get('classic_anonymization', {}).get('anonymized_content', text)
                elif self.anonymization_mode == 'presidio':
                    # Modalità solo Presidio
                    return result.get('anonymized_content', text)
                else:
                    # Modalità classic
                    return result.get('anonymized_content', text)
                    
            except Exception as e:
                print(f"⚠️ Errore anonimizzazione ibrida, fallback a regex: {e}")
                if self.fallback_anonymizer:
                    return self.fallback_anonymizer.anonymize(text, **kwargs)
                return text
        else:
            # Fallback al regex classico
            if self.fallback_anonymizer:
                return self.fallback_anonymizer.anonymize(text, **kwargs)
            return text
    
    def anonymize_record(self, record: Any, **kwargs) -> Any:
        """
        Anonimizza un record completo.
        
        Args:
            record: Record da anonimizzare
            **kwargs: Argomenti aggiuntivi
            
        Returns:
            Record anonimizzato
        """
        if hasattr(record, 'original_content') and record.original_content:
            # Anonimizza il contenuto originale
            anonymized_content = self.anonymize(record.original_content, **kwargs)
            
            # Aggiorna il record con i risultati Presidio se disponibili
            if self.hybrid_service and hasattr(record, 'original_content'):
                try:
                    presidio_result = self.hybrid_service.anonymize_content(
                        record.original_content, 
                        mode=self.anonymization_mode
                    )
                    
                    # Aggiungi i risultati Presidio al record
                    if not hasattr(record, 'presidio_anonymization'):
                        record.presidio_anonymization = {}
                    
                    record.presidio_anonymization = presidio_result
                    
                    # Aggiorna anche il campo anonymized_message per compatibilità
                    if self.anonymization_mode == 'hybrid':
                        # Modalità ibrida: usa classic per compatibilità
                        record.anonymized_message = presidio_result.get('classic_anonymization', {}).get('anonymized_content', anonymized_content)
                    elif self.anonymization_mode == 'presidio':
                        # Modalità solo Presidio
                        record.anonymized_message = presidio_result.get('anonymized_content', anonymized_content)
                    else:
                        # Modalità classic
                        record.anonymized_message = presidio_result.get('anonymized_content', anonymized_content)
                        
                except Exception as e:
                    print(f"⚠️ Errore aggiunta risultati Presidio al record: {e}")
                    record.anonymized_message = anonymized_content
            else:
                record.anonymized_message = anonymized_content
        
        return record
    
    def get_anonymization_mode(self) -> str:
        """
        Restituisce la modalità di anonimizzazione corrente.
        
        Returns:
            Modalità di anonimizzazione
        """
        return self.anonymization_mode
    
    def is_presidio_available(self) -> bool:
        """
        Verifica se Presidio è disponibile.
        
        Returns:
            True se Presidio è disponibile
        """
        return self.hybrid_service is not None
    
    def get_presidio_insights(self, text: str) -> Dict[str, Any]:
        """
        Estrae insight datamining da Presidio.
        
        Args:
            text: Testo da analizzare
            
        Returns:
            Insight datamining
        """
        if self.hybrid_service:
            try:
                result = self.hybrid_service.anonymize_content(text, mode='presidio')
                return result.get('datamining_insights', {})
            except Exception as e:
                print(f"⚠️ Errore estrazione insight Presidio: {e}")
                return {}
        return {}
    
    def get_hybrid_comparison(self, text: str) -> Dict[str, Any]:
        """
        Ottiene confronto tra anonimizzazione classic e Presidio.
        
        Args:
            text: Testo da analizzare
            
        Returns:
            Confronto tra le due modalità
        """
        if self.hybrid_service:
            try:
                result = self.hybrid_service.anonymize_content(text, mode='hybrid')
                return {
                    'classic': result.get('classic_anonymization', {}),
                    'presidio': result.get('presidio_anonymization', {}),
                    'comparison': result.get('hybrid_metadata', {}),
                    'insights': result.get('combined_datamining_insights', {})
                }
            except Exception as e:
                print(f"⚠️ Errore confronto ibrido: {e}")
                return {}
        return {}
    
    # Implementazione metodi richiesti dall'interfaccia Anonymizer
    
    def anonymize_field(self, field_name: str, field_value: Any) -> Any:
        """
        Anonimizza un campo specifico.
        
        Args:
            field_name: Nome del campo
            field_value: Valore da anonimizzare
            
        Returns:
            Valore anonimizzato
        """
        if isinstance(field_value, str):
            return self.anonymize(field_value)
        return field_value
    
    def anonymize_text(self, text: str) -> str:
        """
        Anonimizza testo usando il servizio ibrido.
        
        Args:
            text: Testo da anonimizzare
            
        Returns:
            Testo anonimizzato
        """
        return self.anonymize(text)
    
    @property
    def anonymization_methods(self) -> Dict[str, str]:
        """Restituisce i metodi di anonimizzazione disponibili."""
        methods = {
            'regex': 'Pattern regex predefiniti',
            'hybrid': 'Combinazione regex + Presidio AI'
        }
        
        if self.hybrid_service:
            methods['presidio'] = 'Microsoft Presidio AI/ML'
        
        return methods
    
    @property
    def always_anonymize_fields(self) -> list[str]:
        """Restituisce i campi che dovrebbero sempre essere anonimizzati."""
        if self.fallback_anonymizer:
            return self.fallback_anonymizer.always_anonymize_fields
        return ['ip_address', 'mac_address', 'email', 'hostname', 'devid', 'devname']
