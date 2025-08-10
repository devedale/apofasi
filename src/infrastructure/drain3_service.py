"""Drain3 service implementation."""

import json
from typing import Any, Dict, Optional
from pathlib import Path

from drain3 import TemplateMiner
from drain3 import template_miner_config
# FilePersistence non disponibile in questa versione di drain3
# from drain3.persistence_handler import FilePersistence

from ..domain.interfaces.drain3_service import Drain3Service
from ..domain.entities.parsed_record import ParsedRecord
from ..core.services.regex_service import RegexService


class Drain3ServiceImpl(Drain3Service):
    """Drain3 service implementation with dual mining (original + anonymized)."""
    
    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Initialize Drain3 service with dual miners.
        
        Args:
            config: Drain3 configuration
        """
        self._config = config
        # Due miner separati: uno per messaggi originali, uno per anonimizzati
        self._original_miner = self._create_template_miner("original")
        self._anonymized_miner = self._create_template_miner("anonymized")
        # RegexService per anonimizzare prima del mining/template
        self._regex_service = RegexService(config)
        self._cluster_count = 0
    
    def add_log_message(self, log_message: str, miner_type: str = "original") -> int:
        """
        Add a log message to Drain3 for template mining.
        
        Args:
            log_message: The log message to add
            miner_type: "original" or "anonymized" to specify which miner to use
            
        Returns:
            Cluster ID assigned to the message
        """
        try:
            # Seleziona il miner appropriato
            if miner_type == "anonymized":
                # Per messaggi anonimizzati, applica ulteriori pattern se necessario
                safe_message = self._regex_service.apply_patterns_by_category(log_message, 'anonymization') if isinstance(log_message, str) else log_message
                miner = self._anonymized_miner
            else:
                # Per messaggi originali, usa il miner originale
                safe_message = log_message
                miner = self._original_miner
            
            result = miner.add_log_message(safe_message)
            # Il risultato potrebbe essere un oggetto con cluster_id o un dizionario
            if hasattr(result, 'cluster_id'):
                cluster_id = result.cluster_id
            elif isinstance(result, dict) and 'cluster_id' in result:
                cluster_id = result['cluster_id']
            else:
                # Fallback: usa un ID incrementale
                self._cluster_count += 1
                cluster_id = self._cluster_count
            
            self._cluster_count = max(self._cluster_count, cluster_id)
            return cluster_id
        except Exception as e:
            # In caso di errore, usa un ID incrementale
            self._cluster_count += 1
            return self._cluster_count
    
    def get_template(self, cluster_id: int, miner_type: str = "original") -> Optional[str]:
        """
        Get the template for a specific cluster.
        
        Args:
            cluster_id: The cluster ID
            miner_type: "original" or "anonymized" to specify which miner to use
            
        Returns:
            Template string or None if not found
        """
        miner = self._get_miner_by_type(miner_type)
        clusters = miner.drain.clusters
        if cluster_id in clusters:
            return clusters[cluster_id].get_template()
        return None
    
    def get_cluster_info(self, cluster_id: int, miner_type: str = "original") -> Optional[Dict[str, Any]]:
        """
        Get information about a specific cluster.
        
        Args:
            cluster_id: The cluster ID
            miner_type: "original" or "anonymized" to specify which miner to use
            
        Returns:
            Cluster information dictionary or None if not found
        """
        miner = self._get_miner_by_type(miner_type)
        clusters = miner.drain.clusters
        if cluster_id in clusters:
            cluster = clusters[cluster_id]
            return {
                "cluster_id": cluster_id,
                "template": cluster.get_template(),
                "size": cluster.size,
                "log_ids": list(cluster.log_ids),
                "miner_type": miner_type,
            }
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
        
        for cluster_id, cluster in clusters.items():
            templates[cluster_id] = cluster.get_template()
        
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
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get Drain3 statistics for both miners.
        
        Returns:
            Statistics dictionary with combined information
        """
        original_stats = {
            "total_clusters": len(self._original_miner.drain.clusters),
            "total_logs": getattr(self._original_miner.drain, 'total_logs', 0),
        }
        
        anonymized_stats = {
            "total_clusters": len(self._anonymized_miner.drain.clusters),
            "total_logs": getattr(self._anonymized_miner.drain, 'total_logs', 0),
        }
        
        return {
            "original": original_stats,
            "anonymized": anonymized_stats,
            "combined": {
                "total_clusters": original_stats["total_clusters"] + anonymized_stats["total_clusters"],
                "total_logs": original_stats["total_logs"] + anonymized_stats["total_logs"],
            },
            "config": self._config,
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
        """
        # Processa con il miner originale usando il contenuto originale
        original_cluster_id = self.add_log_message(record.original_content, "original")
        original_template = self.get_template(original_cluster_id, "original")
        original_cluster_info = self.get_cluster_info(original_cluster_id, "original")
        
        # Processa con il miner anonimizzato usando il TEMPLATE ANONIMIZZATO COERENTE
        if hasattr(record, 'anonymized_template') and record.anonymized_template:
            # Usa il template anonimizzato coerente (non il messaggio anonimizzato)
            anonymized_cluster_id = self.add_log_message(record.anonymized_template, "anonymized")
            anonymized_template = self.get_template(anonymized_cluster_id, "anonymized")
            anonymized_cluster_info = self.get_cluster_info(anonymized_cluster_id, "anonymized")
        elif hasattr(record, 'anonymized_message') and record.anonymized_message:
            # Fallback: usa il messaggio anonimizzato se non c'è template
            anonymized_cluster_id = self.add_log_message(record.anonymized_message, "anonymized")
            anonymized_template = self.get_template(anonymized_cluster_id, "anonymized")
            anonymized_cluster_info = self.get_cluster_info(anonymized_cluster_id, "anonymized")
        else:
            # Fallback: usa il contenuto originale se non c'è anonimizzazione
            anonymized_cluster_id = self.add_log_message(record.original_content, "anonymized")
            anonymized_template = self.get_template(anonymized_cluster_id, "anonymized")
            anonymized_cluster_info = self.get_cluster_info(anonymized_cluster_id, "anonymized")

        # Mantieni compatibilità con i campi esistenti
        record.drain3_cluster_id = original_cluster_id
        record.drain3_template = original_template

        # Aggiungi i risultati di Drain3 ai dati parsati
        if original_cluster_info:
            record.parsed_data["drain3_original"] = {
                "cluster_id": original_cluster_id,
                "template": original_template,
                "cluster_size": original_cluster_info["size"],
            }
        if anonymized_cluster_info:
            record.parsed_data["drain3_anonymized"] = {
                "cluster_id": anonymized_cluster_id,
                "template": anonymized_template,
                "cluster_size": anonymized_cluster_info["size"],
            }

        # Mantieni compatibilità con i campi legacy
        if "drain3" not in record.parsed_data:
            record.parsed_data["drain3"] = {
                "cluster_id": original_cluster_id,
                "template": original_template,
                "cluster_size": original_cluster_info["size"] if original_cluster_info else 0
            }
        
        # Aggiungi anche i campi legacy per compatibilità
        record.parsed_data["drain3_cluster_id"] = original_cluster_id
        record.parsed_data["drain3_template"] = original_template

        return record
    
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
        
        Args:
            miner_type: "original" or "anonymized" for logging purposes
            
        Returns:
            Configured TemplateMiner instance
        """
        # Extract Drain3 configuration from config.ini (not drain3.ini)
        drain3_config = self._config.get("drain3", {})
        
        # Create proper config object
        config = template_miner_config.TemplateMinerConfig()
        
        # Usa parametri specifici per tipo di miner se disponibili
        if miner_type in drain3_config and isinstance(drain3_config[miner_type], dict):
            miner_specific_config = drain3_config[miner_type]
            config.drain_depth = miner_specific_config.get("depth", drain3_config.get("depth", 4))
            config.drain_max_children = miner_specific_config.get("max_children", drain3_config.get("max_children", 100))
            config.drain_max_clusters = miner_specific_config.get("max_clusters", drain3_config.get("max_clusters", 1000))
            config.drain_sim_th = miner_specific_config.get("similarity_threshold", drain3_config.get("similarity_threshold", 0.4))
        else:
            # Fallback ai parametri comuni
            config.drain_depth = drain3_config.get("depth", 4)
            config.drain_max_children = drain3_config.get("max_children", 100)
            config.drain_max_clusters = drain3_config.get("max_clusters", 1000)
            config.drain_sim_th = drain3_config.get("similarity_threshold", drain3_config.get("similarity_threshold", 0.4))
        
        print(f"🔧 Creating Drain3 miner '{miner_type}' with config: depth={config.drain_depth}, max_children={config.drain_max_children}, max_clusters={config.drain_max_clusters}, sim_th={config.drain_sim_th}")
        
        # Create template miner without persistence for now
        template_miner = TemplateMiner(config=config)
        
        return template_miner 