"""Drain3 service implementation."""

import json
from typing import Any, Dict, Optional
from pathlib import Path
import re # Added for fallback template generation

from drain3 import TemplateMiner
from drain3 import template_miner_config
# FilePersistence non disponibile in questa versione di drain3
# from drain3.persistence_handler import FilePersistence

from ..domain.interfaces.drain3_service import Drain3Service
from ..domain.entities.parsed_record import ParsedRecord
from ..core.services.regex_service import RegexService
from ..domain.interfaces.centralized_regex_service import CentralizedRegexService


class Drain3ServiceImpl(Drain3Service):
    """
    Drain3 service implementation with dual mining (original + anonymized).
    
    IMPORTANTE: Configurato per funzionare SENZA LIMITI PRATICI quando max_clusters e max_children
    sono impostati a 999999 nella configurazione. Questo permette al drain di processare
    file di qualsiasi dimensione sullo stesso file senza limiti pratici sui cluster.
    """
    
    def __init__(self, config: Dict[str, Any], centralized_regex_service: Optional[CentralizedRegexService] = None) -> None:
        """
        Initialize Drain3 service with dual miners.
        
        Args:
            config: Drain3 configuration
            centralized_regex_service: Centralized regex service for configuration
        """
        self._config = config
        # Verbose logging controllato da config app.debug (default: False)
        self._verbose = bool(config.get('app', {}).get('debug', False))
        self._centralized_regex_service = centralized_regex_service
        # Due miner separati: uno per messaggi originali, uno per anonimizzati
        self._original_miner = self._create_template_miner("original")
        self._anonymized_miner = self._create_template_miner("anonymized")
        # RegexService per anonimizzare prima del mining/template
        self._regex_service = RegexService(config)
        self._cluster_count = 0
    
    def add_log_message(self, message: str, miner_type: str = "original") -> Dict[str, Any]:
        """
        Add a log message to the specified miner.
        
        Args:
            message: Log message to add
            miner_type: "original" or "anonymized"
            
        Returns:
            Dictionary with cluster_id and template information
        """
        miner = self._get_miner_by_type(miner_type)
        
        if self._verbose:
            print(f"🔍 DEBUG: Adding message to {miner_type} miner: {message[:100]}...")
            print(f"🔍 DEBUG: Processing message with {miner_type} miner: {message[:100]}...")
        
        # WHY: Drain3 restituisce già il template nel risultato, non dobbiamo cercarlo dopo
        result = miner.add_log_message(message)
        if self._verbose:
            print(f"🔍 DEBUG: Drain3 result: {result}")
        
        cluster_id = result.get('cluster_id')
        template = result.get('template_mined')  # WHY: Usiamo il template già generato
        
        if self._verbose:
            print(f"🔍 DEBUG: Assigned cluster ID: {cluster_id}")
            print(f"🔍 DEBUG: Template from result: {template}")
        
        return {
            'cluster_id': cluster_id,
            'template': template,
            'cluster_size': result.get('cluster_size', 1)
        }
    
    def get_template(self, cluster_id: int, miner_type: str = "original") -> Optional[str]:
        """
        Get template for a specific cluster.
        
        Args:
            cluster_id: ID of the cluster
            miner_type: "original" or "anonymized"
            
        Returns:
            Template string or None if not found
        """
        miner = self._get_miner_by_type(miner_type)
        clusters = miner.drain.clusters
        
        if self._verbose:
            print(f"🔍 DEBUG: Getting template for cluster {cluster_id} in {miner_type} miner")
            print(f"🔍 DEBUG: Total clusters available: {len(clusters)}")
            print(f"🔍 DEBUG: Cluster IDs available: {list(clusters.keys()) if hasattr(clusters, 'keys') else 'No keys method'}")
        
        if cluster_id in clusters:
            cluster = clusters[cluster_id]
            template = cluster.get_template()
            if self._verbose:
                print(f"🔍 DEBUG: Found cluster {cluster_id}, template: {template}")
            
            if template is None:
                # WHY: Fallback per template nulli - ricostruiamo dal log_template_tokens
                template = self._reconstruct_template_from_tokens(cluster)
                if template:
                    if self._verbose:
                        print(f"🔄 DEBUG: Generated template from log_template_tokens for cluster {cluster_id}: {template[:100]}...")
            
            return template
        else:
            if self._verbose:
                print(f"⚠️ DEBUG: Cluster {cluster_id} not found in {miner_type} miner")
                print(f"⚠️ DEBUG: Available cluster IDs: {list(clusters.keys()) if hasattr(clusters, 'keys') else 'No keys method'}")
            return None
    
    def get_cluster_info(self, cluster_id: int, miner_type: str = "original") -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific cluster.
        
        Args:
            cluster_id: The cluster ID
            miner_type: "original" or "anonymized" to specify which miner to use
            
        Returns:
            Dictionary with cluster information or None if not found
        """
        try:
            if self._verbose:
                print(f"🔍 DEBUG: get_cluster_info chiamato per cluster {cluster_id} in {miner_type} miner")
            
            miner = self._get_miner_by_type(miner_type)
            clusters = miner.drain.clusters
            
            if self._verbose:
                print(f"🔍 DEBUG: Trovati {len(clusters)} cluster totali")
                print(f"🔍 DEBUG: Tipo di clusters: {type(clusters)}")
            
            if cluster_id in clusters:
                cluster = clusters[cluster_id]
                if self._verbose:
                    print(f"🔍 DEBUG: Cluster {cluster_id} trovato, tipo: {type(cluster)}")
                    print(f"🔍 DEBUG: Attributi del cluster: {dir(cluster)}")
                
                # Forza la generazione del template se non è disponibile
                template = cluster.get_template()
                if self._verbose:
                    print(f"🔍 DEBUG: Template generato: {template}")
                
                if not template and hasattr(cluster, 'log_template_tokens'):
                    template = " ".join(cluster.log_template_tokens)
                    if self._verbose:
                        print(f"🔄 DEBUG: Generated template from log_template_tokens for cluster {cluster_id}: {template[:100]}...")
                
                # WHY: Debug dettagliato per capire il loop infinito
                log_ids = []
                try:
                    if self._verbose:
                        print(f"🔍 DEBUG: Controllo log_ids per cluster {cluster_id}")
                    if hasattr(cluster, 'log_ids'):
                        if self._verbose:
                            print(f"🔍 DEBUG: log_ids presente, tipo: {type(cluster.log_ids)}")
                            print(f"🔍 DEBUG: log_ids contenuto: {cluster.log_ids}")
                        
                        if cluster.log_ids:
                            # Converti in lista con limite di sicurezza
                            log_ids_list = list(cluster.log_ids)
                            if self._verbose:
                                print(f"🔍 DEBUG: log_ids convertito in lista, lunghezza: {len(log_ids_list)}")
                            log_ids = log_ids_list[:100]  # Limite di sicurezza
                            if self._verbose:
                                print(f"🔍 DEBUG: log_ids limitato a {len(log_ids)} elementi")
                        else:
                            if self._verbose:
                                print(f"🔍 DEBUG: log_ids è vuoto")
                    else:
                        if self._verbose:
                            print(f"🔍 DEBUG: log_ids non presente")
                        
                except Exception as e:
                    if self._verbose:
                        print(f"❌ DEBUG: Errore nell'accesso a log_ids per cluster {cluster_id}: {e}")
                        print(f"❌ DEBUG: Tipo di errore: {type(e)}")
                    import traceback
                    traceback.print_exc()
                    log_ids = []
                
                cluster_info = {
                    "cluster_id": cluster_id,
                    "template": template,
                    "size": getattr(cluster, 'size', 0),
                    "log_ids": log_ids,
                    "miner_type": miner_type,
                }
                
                if self._verbose:
                    print(f"🔍 DEBUG: Cluster info generato: {cluster_info}")
                return cluster_info
            
            if self._verbose:
                print(f"⚠️ DEBUG: Cluster {cluster_id} non trovato in {miner_type} miner")
            return None
            
        except Exception as e:
            if self._verbose:
                print(f"❌ DEBUG: Errore in get_cluster_info per cluster {cluster_id}: {e}")
                print(f"❌ DEBUG: Tipo di errore: {type(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_all_templates(self, miner_type: str = "original") -> Dict[int, str]:
        """
        Get all templates discovered by Drain3.
        
        Args:
            miner_type: "original" or "anonymized" to specify which miner to use
            
        Returns:
            Dictionary mapping cluster IDs to templates
        """
        miner = self._get_miner_by_type(miner_type)
        templates = {}
        clusters = miner.drain.clusters
        
        for cluster_id, cluster in clusters.items() if hasattr(clusters, 'items') else enumerate(clusters):
            # Forza la generazione del template se non è disponibile
            template = cluster.get_template()
            if not template and hasattr(cluster, 'log_template_tokens'):
                template = " ".join(cluster.log_template_tokens)
                if self._verbose:
                    print(f"🔄 DEBUG: Generated template from log_template_tokens for cluster {cluster_id}: {template[:100]}...")
            
            templates[cluster_id] = template
        
        return templates
    
    def get_all_templates_combined(self) -> Dict[str, Dict[int, str]]:
        """
        Get all templates from both miners combined.
        
        Returns:
            Dictionary with "original" and "anonymized" keys, each containing cluster ID to template mappings
        """
        return {
            "original": self.get_all_templates("original"),
            "anonymized": self.get_all_templates("anonymized")
        }
    
    def force_template_generation(self, miner_type: str = "original") -> Dict[int, str]:
        """
        Force template generation for all clusters in a miner.
        
        WHY: Sometimes Drain3 doesn't generate templates immediately,
        this method forces the generation by accessing cluster properties.
        
        Args:
            miner_type: "original" or "anonymized"
            
        Returns:
            Dictionary mapping cluster IDs to templates
        """
        miner = self._get_miner_by_type(miner_type)
        clusters = miner.drain.clusters
        templates = {}
        
        if self._verbose:
            print(f"🔧 DEBUG: Forcing template generation for {miner_type} miner with {len(clusters)} clusters")
        
        for cluster_id, cluster in clusters.items() if hasattr(clusters, 'items') else enumerate(clusters):
            try:
                # Forza la generazione del template
                template = cluster.get_template()
                if template:
                    templates[cluster_id] = template
                    if self._verbose:
                        print(f"✅ DEBUG: Generated template for cluster {cluster_id}: {template[:100]}...")
                else:
                    # Fallback: usa i token del template
                    if hasattr(cluster, 'log_template_tokens'):
                        template = " ".join(cluster.log_template_tokens)
                        templates[cluster_id] = template
                        if self._verbose:
                            print(f"🔄 DEBUG: Used log_template_tokens for cluster {cluster_id}: {template[:100]}...")
                    else:
                        if self._verbose:
                            print(f"⚠️ DEBUG: No template available for cluster {cluster_id}")
            except Exception as e:
                if self._verbose:
                    print(f"❌ DEBUG: Error generating template for cluster {cluster_id}: {e}")
        
        return templates
    
    def get_statistics(self, miner_type: str = "original") -> Dict[str, Any]:
        """
        Get statistics about a specific miner.
        
        Args:
            miner_type: "original" or "anonymized"
            
        Returns:
            Dictionary with statistics
        """
        miner = self._get_miner_by_type(miner_type)
        clusters = miner.drain.clusters
        
        # WHY: Non chiamiamo force_template_generation per evitare loop infiniti
        # templates = self.force_template_generation(miner_type)
        
        # Calcola statistiche senza forzare la generazione dei template
        total_logs = sum(getattr(cluster, 'size', 0) for cluster in clusters.values())
        
        return {
            "total_clusters": len(clusters),
            "total_logs": total_logs,
            "total_templates": 0,  # Non calcoliamo i template per evitare loop infiniti
            "clusters_with_templates": 0,  # Non calcoliamo per evitare loop infiniti
            "clusters_without_templates": len(clusters)  # Tutti i cluster
        }
    
    def get_statistics_combined(self) -> Dict[str, Any]:
        """
        Get statistics about both miners combined.
        
        WHY: Metodo separato per evitare loop infiniti nel metodo get_statistics singolo
        
        Returns:
            Dictionary with statistics for both miners
        """
        original_stats = self.get_statistics("original")
        anonymized_stats = self.get_statistics("anonymized")
        
        return {
            "original": original_stats,
            "anonymized": anonymized_stats,
            "combined": {
                "total_clusters": original_stats["total_clusters"] + anonymized_stats["total_clusters"],
                "total_logs": original_stats["total_logs"] + anonymized_stats["total_logs"],
                "total_templates": original_stats["total_templates"] + anonymized_stats["total_templates"]
            }
        }
    
    def _get_miner_statistics(self, miner_type: str) -> Dict[str, Any]:
        """
        Get statistics for a specific miner.
        
        Args:
            miner_type: "original" or "anonymized"
            
        Returns:
            Statistics dictionary
        """
        miner = self._get_miner_by_type(miner_type)
        clusters = miner.drain.clusters
        
        # Forza la generazione dei template per statistiche accurate
        templates = self.force_template_generation(miner_type)
        
        return {
            "total_clusters": len(clusters),
            "total_logs": sum(cluster.size for cluster in clusters.values()),
            "total_templates": len(templates),
            "clusters_with_templates": len([t for t in templates.values() if t]),
            "clusters_without_templates": len(clusters) - len([t for t in templates.values() if t])
        }
    
    def save_state(self, file_path: str) -> None:
        """
        Save Drain3 state to file for both miners.
        
        Args:
            file_path: Path to save state
        """
        # Salva entrambi i miner in file separati
        original_path = f"{file_path}_original"
        anonymized_path = f"{file_path}_anonymized"
        
        self._original_miner.save_state(original_path)
        self._anonymized_miner.save_state(anonymized_path)
    
    def load_state(self, file_path: str) -> None:
        """
        Load Drain3 state from file for both miners.
        
        Args:
            file_path: Path to load state from
        """
        # Carica entrambi i miner da file separati
        original_path = f"{file_path}_original"
        anonymized_path = f"{file_path}_anonymized"
        
        try:
            self._original_miner.load_state(original_path)
        except Exception as e:
            print(f"Warning: Could not load original miner state from {original_path}: {e}")
        
        try:
            self._anonymized_miner.load_state(anonymized_path)
        except Exception as e:
            print(f"Warning: Could not load anonymized miner state from {anonymized_path}: {e}")
    
    def process_record(self, record: ParsedRecord) -> ParsedRecord:
        """
        Processa un record con Drain3 per entrambi i tipi di miner.
        
        DESIGN: Usa il template anonimizzato coerente per garantire
        che il miner anonimizzato processi dati realmente anonimizzati.
        
        WHY: Il miner anonimizzato DEVE sempre usare anonymized_message
        per garantire coerenza e evitare contaminazione con dati originali.
        """
        # Processa con il miner originale usando il contenuto originale
        original_result = self.add_log_message(record.original_content, "original")
        original_cluster_id = original_result['cluster_id']
        original_template = original_result['template']
        original_cluster_size = original_result['cluster_size']
        
        # 🚨 CORREZIONE: Il miner anonimizzato DEVE sempre usare anonymized_message
        if hasattr(record, 'anonymized_message') and record.anonymized_message:
            # ✅ USO CORRETTO: anonymized_message per il miner anonimizzato
            anonymized_result = self.add_log_message(record.anonymized_message, "anonymized")
            anonymized_cluster_id = anonymized_result['cluster_id']
            anonymized_template = anonymized_result['template']
            anonymized_cluster_size = anonymized_result['cluster_size']
        elif hasattr(record, 'anonymized_template') and record.anonymized_template:
            # Fallback: usa il template anonimizzato se disponibile
            anonymized_result = self.add_log_message(record.anonymized_template, "anonymized")
            anonymized_cluster_id = anonymized_result['cluster_id']
            anonymized_template = anonymized_result['template']
            anonymized_cluster_size = anonymized_result['cluster_size']
        else:
            # ❌ ERRORE: Non dovrebbe mai succedere - log di warning
            print(f"⚠️ WARNING: Record senza anonymized_message per {record.source_file}:{record.line_number}")
            print(f"⚠️ Contenuto originale: {record.original_content[:100]}...")
            
            # 🚨 NON USARE MAI original_content per il miner anonimizzato
            # Crea un template di fallback anonimizzato coerente
            fallback_template = self._create_fallback_anonymized_template(record.original_content)
            anonymized_result = self.add_log_message(fallback_template, "anonymized")
            anonymized_cluster_id = anonymized_result['cluster_id']
            anonymized_template = anonymized_result['template']
            anonymized_cluster_size = anonymized_result['cluster_size']
        
        # ✅ Aggiungi i risultati di Drain3 ai dati parsati
        record.parsed_data["drain3_original"] = {
            "cluster_id": original_cluster_id,
            "template": original_template,
            "cluster_size": original_cluster_size,
        }
        
        record.parsed_data["drain3_anonymized"] = {
            "cluster_id": anonymized_cluster_id,
            "template": anonymized_template,
            "cluster_size": anonymized_cluster_size,
        }
        
        # 🧹 RIMUOVI CAMPI LEGACY NON NECESSARI
        # Mantieni solo i campi essenziali per compatibilità
        if "drain3" in record.parsed_data:
            # Aggiorna il campo legacy con i dati originali (per compatibilità)
            record.parsed_data["drain3"] = {
                "cluster_id": original_cluster_id,
                "template": original_template,
                "cluster_size": original_cluster_size,
            }
        
        return record
    
    def _create_fallback_anonymized_template(self, original_content: str) -> str:
        """
        Crea un template anonimizzato di fallback coerente.
        
        WHY: Quando anonymized_message non è disponibile, creiamo un template
        anonimizzato coerente invece di usare original_content che contamina
        il miner anonimizzato.
        
        Args:
            original_content: Contenuto originale del log
            
        Returns:
            Template anonimizzato coerente
        """
        try:
            # Usa il servizio regex centralizzato per anonimizzazione coerente
            if self._centralized_regex_service:
                fallback_template = self._centralized_regex_service.anonymize_content(original_content)
            else:
                # Fallback: usa il RegexService locale
                fallback_template = self._regex_service.anonymize_content(original_content)
            
            if self._verbose:
                print(f"🔄 DEBUG: Creato template fallback anonimizzato: {fallback_template[:100]}...")
            return fallback_template
            
        except Exception as e:
            print(f"❌ ERRORE nella creazione template fallback: {e}")
            # Fallback estremo: sostituisci pattern comuni
            fallback = original_content
            fallback = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '<IP>', fallback)
            fallback = re.sub(r'\b\d{5,}\b', '<NUMERIC_ID>', fallback)
            fallback = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '<EMAIL>', fallback)
            fallback = re.sub(r'\b(?:[0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})\b', '<MAC>', fallback)
            if self._verbose:
                print(f"🔄 DEBUG: Template fallback estremo creato: {fallback[:100]}...")
            return fallback
    
    def _get_miner_by_type(self, miner_type: str) -> TemplateMiner:
        """
        Get the appropriate miner based on type.
        
        Args:
            miner_type: "original" or "anonymized"
            
        Returns:
            TemplateMiner instance
        """
        if miner_type == "anonymized":
            return self._anonymized_miner
        else:
            return self._original_miner
    
    def _create_template_miner(self, miner_type: str) -> TemplateMiner:
        """
        Create Drain3 template miner with configuration.
        
        IMPORTANTE: Se max_clusters e max_children sono 999999 nella configurazione,
        il drain funziona SENZA LIMITI PRATICI (drain infinito) e può processare file
        di qualsiasi dimensione sullo stesso file.
        
        Args:
            miner_type: "original" or "anonymized" for logging purposes
            
        Returns:
            Configured TemplateMiner instance
        """
        # WHY: Usa il servizio centralizzato se disponibile
        try:
            if self._centralized_regex_service:
                drain3_config = self._centralized_regex_service.get_drain3_config()
            else:
                # WHY: Fallback alla cache invece di ricaricare YAML
                from ...core.services.config_cache import ConfigCache
                config_cache = ConfigCache()
                drain3_config = config_cache.get_drain3_config()
                    
        except Exception as e:
            print(f"❌ Errore nel caricamento della configurazione: {e}")
            print("📝 Usando configurazione di default...")
            drain3_config = {}
        
        # Create proper config object
        config = template_miner_config.TemplateMinerConfig()
        
        # Usa parametri specifici per tipo di miner se disponibili
        if miner_type in drain3_config and isinstance(drain3_config[miner_type], dict):
            miner_specific_config = drain3_config[miner_type]
            config.drain_depth = miner_specific_config.get("depth", drain3_config.get("depth", 4))
            # IMPORTANTE: Usa direttamente i valori dalla configurazione
            # max_children: 999999 = limite praticamente infinito sui figli
            # max_clusters: 999999 = limite praticamente infinito sui cluster
            config.drain_max_children = miner_specific_config.get("max_children", drain3_config.get("max_children", 999999))
            config.drain_max_clusters = miner_specific_config.get("max_clusters", drain3_config.get("max_clusters", 999999))
            config.drain_sim_th = miner_specific_config.get("similarity_threshold", drain3_config.get("similarity_threshold", 0.4))
        else:
            # Fallback ai parametri comuni
            config.drain_depth = drain3_config.get("depth", 4)
            # IMPORTANTE: Usa direttamente i valori dalla configurazione
            # max_children: 999999 = limite praticamente infinito sui figli
            # max_clusters: 999999 = limite praticamente infinito sui cluster
            config.drain_max_children = drain3_config.get("max_children", 999999)
            config.drain_max_clusters = drain3_config.get("max_clusters", 999999)
            config.drain_sim_th = drain3_config.get("similarity_threshold", 0.4)
        
        # Configurazione aggiuntiva per assicurare la generazione dei template
        config.profiling_enabled = True
        config.mask_digits_with_asterisk = True
        config.mask_hex = True
        config.mask_ips = True
        config.persistence_type = "NONE"
        
        if self._verbose:
            print(f"🔧 Creating Drain3 miner '{miner_type}' with config: depth={config.drain_depth}, max_children={config.drain_max_children}, max_clusters={config.drain_max_clusters}, sim_th={config.drain_sim_th}")
        
        # Create template miner without persistence for now
        template_miner = TemplateMiner(config=config)
        
        return template_miner 