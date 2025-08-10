"""
Pattern Detection Service - Servizio per rilevamento automatico di pattern nei log

WHY: Servizio centralizzato per aggiungere template, cluster e rilevamento regex
a tutti i parser, non solo all'adaptive parser.

Author: Edoardo D'Alesio
"""

import re
from typing import Dict, Any, List, Optional
from collections import defaultdict
from drain3 import TemplateMiner
# from drain3.template import LogCluster  # Non necessario
from pathlib import Path

from .regex_service import RegexService


class PatternDetectionService:
    """
    Servizio per rilevamento automatico di pattern in tutti i tipi di log.
    
    WHY: Centralizza la logica di detection pattern per essere usata
    da tutti i parser, garantendo funzionalità consistenti.
    """
    
    def __init__(self, config: Dict[str, Any] = None, regex_service: Optional["RegexService"] = None):
        """
        Inizializza il servizio di detection pattern.
        
        Args:
            config: Configurazione per Drain3 e pattern detection
            regex_service: Servizio regex condiviso (opzionale)
        """
        self.config = config or {}
        
        # Usa RegexService condiviso o creane uno nuovo
        if regex_service:
            self.regex_service = regex_service
        else:
            from .regex_service import RegexService
            self.regex_service = RegexService()
        
        # Inizializza Drain3 per template mining
        # Usa configurazione di default per TemplateMiner
        try:
            # Usa la stessa configurazione del Drain3Service per coerenza
            if self.config and "drain3" in self.config:
                drain3_config = self.config["drain3"]
                
                # Crea configurazione TemplateMiner
                from drain3 import template_miner_config
                config = template_miner_config.TemplateMinerConfig()
                
                # Usa parametri specifici se disponibili, altrimenti fallback
                if "original" in drain3_config and isinstance(drain3_config["original"], dict):
                    miner_specific_config = drain3_config["original"]
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
                
                self.template_miner = TemplateMiner(config=config)
                print(f"✅ TemplateMiner configurato con parametri Drain3: depth={config.drain_depth}, max_children={config.drain_max_children}, max_clusters={config.drain_max_clusters}, sim_th={config.drain_sim_th}")
            else:
                # Fallback: usa configurazione di default
                self.template_miner = TemplateMiner()
                print("⚠️ Configurazione Drain3 non trovata, uso TemplateMiner di default")
        except Exception as e:
            # Fallback: usa configurazione minima
            print(f"⚠️ Errore configurazione TemplateMiner: {e}, uso configurazione di default")
            self.template_miner = TemplateMiner()
        
        # Pattern regex per detection automatica di entità comuni
        # WHY: Pattern ottimizzati per ridurre falsi positivi e essere più precisi
        self.detection_patterns = {
            'ip_address': r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b',
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'timestamp_iso': r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?',
            'timestamp_log': r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?',
            'timestamp_dotted': r'\d{4}\.\d{2}\.\d{2}',  # Formato 2005.06.03
            'timestamp_detailed': r'\d{4}-\d{2}-\d{2}-\d{2}\.\d{2}\.\d{2}\.\d+',  # Formato 2005-06-03-15.42.50.675872
            'unix_timestamp': r'\b\d{10}\b',  # Timestamp Unix (10 cifre)
            'url': r'https?://[^\s<>"]+',  # Escludi caratteri XML problematici
            'mac_address': r'(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}',
            'uuid': r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}',
            'hash_md5': r'\b[a-fA-F0-9]{32}\b',
            'hash_sha256': r'\b[a-fA-F0-9]{64}\b',
            # Rimuovo port_number che era mal formato
            # Aggiusto file_path per essere meno aggressivo con XML
            'file_path': r'(?:[a-zA-Z]:\\|\/)[^\s<>"]*(?:\/[^\s<>"]*)*',  # Path reali, non tag XML
            'severity_level': r'\b(?:DEBUG|INFO|WARN|WARNING|ERROR|FATAL|CRITICAL|TRACE)\b',
            'process_id': r'\b(?:pid|PID)[\s:=]+(\d+)\b',
            'user_agent': r'Mozilla/[\d\.]+[^\<]*(?=</)',  # Migliore per XML
            'status_code': r'\b(?:[1-5][0-9]{2})\b',  # HTTP status codes più precisi 100-599
            'hostname': r'\b[A-Z]\d{2}-[A-Z]\d+-[A-Z]\d+(?:-[A-Z])?(?::[A-Z]\d+-[A-Z]\d+)?\b',  # Pattern per R02-M1-N0-C:J12-U11
        }
    
    def add_template_and_patterns(self, content: str, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aggiunge template, cluster_id, cluster_size e pattern detection ai dati parsati.
        
        WHY: Arricchisce qualsiasi output di parsing con informazioni strutturali
        e pattern automaticamente rilevati.
        
        Args:
            content: Contenuto originale del log
            parsed_data: Dati già parsati da aggiungere
            
        Returns:
            Dati parsati arricchiti con template e pattern detection
        """
        # Copia i dati esistenti
        enriched_data = parsed_data.copy()
        
        # SAFETY: Gestione intelligente di contenuti molto lunghi
        if len(content) > 50000:  # 50KB limit per singola riga (molto permissivo)
            # Per contenuti enormi, usa solo template semplificato
            enriched_data['template'] = content[:200] + "... [TRUNCATED]"
            enriched_data['cluster_id'] = -1
            enriched_data['cluster_size'] = 1
            enriched_data['warning'] = 'Content too long for full pattern detection'
            
            # Pattern detection limitato solo su inizio del contenuto
            quick_patterns = self._detect_patterns(content[:1000])
            if quick_patterns:
                enriched_data['detected_patterns'] = quick_patterns
                self._add_pattern_fields(enriched_data, quick_patterns)
            
            return enriched_data
        
        # 1. Genera template e cluster usando Drain3
        try:
            cluster = self.template_miner.add_log_message(content)
            template = cluster["template_mined"]
        except Exception as e:
            # Fallback se Drain3 si blocca
            enriched_data['template'] = content[:200] + "..." if len(content) > 200 else content
            enriched_data['cluster_id'] = -1
            enriched_data['cluster_size'] = 1
            enriched_data['warning'] = f'Drain3 failed: {str(e)}'
            return enriched_data
        
        # Aggiunge informazioni template/cluster
        enriched_data['template'] = template
        enriched_data['cluster_id'] = cluster['cluster_id']
        enriched_data['cluster_size'] = cluster['cluster_size']
        
        # 2. Detection automatica di pattern
        detected_patterns = self._detect_patterns(content)
        
        # Aggiunge i pattern rilevati
        if detected_patterns:
            enriched_data['detected_patterns'] = detected_patterns
            
            # Aggiunge anche i singoli pattern come campi separati per facilità d'uso
            for pattern_type, values in detected_patterns.items():
                if values:  # Solo se ci sono valori
                    field_name = f"regex_{pattern_type}"
                    if len(values) == 1:
                        enriched_data[field_name] = values[0]
                    else:
                        enriched_data[field_name] = values
        
        return enriched_data
    
    def _detect_patterns(self, content: str) -> Dict[str, List[str]]:
        """
        Rileva automaticamente pattern regex nel contenuto.
        
        WHY: Estrae automaticamente informazioni strutturali come IP,
        timestamp, email, etc. senza richiedere configurazione specifica.
        
        Args:
            content: Contenuto da analizzare
            
        Returns:
            Dizionario con pattern rilevati e i loro valori
        """
        detected = defaultdict(list)
        
        for pattern_name, pattern_regex in self.detection_patterns.items():
            try:
                # SAFETY: Gestione intelligente per contenuti di diverse dimensioni
                if len(content) > 20000:  # File molto grandi: usa solo l'inizio
                    search_content = content[:2000]
                elif len(content) > 5000:  # File medi: usa porzione più grande
                    search_content = content[:10000]
                else:
                    search_content = content
                matches = re.findall(pattern_regex, search_content, re.IGNORECASE)
                if matches:
                    # Rimuove duplicati mantenendo l'ordine
                    unique_matches = list(dict.fromkeys(matches))
                    detected[pattern_name] = unique_matches
            except Exception as e:
                # Skip pattern problematici invece di bloccare tutto
                continue
        
        return dict(detected)
    
    def _add_pattern_fields(self, data: Dict[str, Any], patterns: Dict[str, Any]) -> None:
        """
        Aggiunge i singoli pattern come campi separati per facilità d'uso.
        
        WHY: Permette accesso diretto ai pattern senza dover navigare detected_patterns.
        """
        for pattern_type, values in patterns.items():
            if values:
                field_name = f"regex_{pattern_type}"
                if len(values) == 1:
                    data[field_name] = values[0]
                else:
                    data[field_name] = values
    
    def extract_variables_from_template(self, content: str, template: str) -> Dict[str, Any]:
        """
        Estrae le variabili dal template Drain3.
        
        WHY: Converte i placeholder <*> in variabili strutturate
        che possono essere utilizzate per analisi successive.
        
        Args:
            content: Contenuto originale
            template: Template generato da Drain3
            
        Returns:
            Dizionario con le variabili estratte
        """
        variables = {}
        
        # Converte il template in regex sostituendo <*> con gruppi di cattura
        regex_pattern = re.escape(template).replace(r'\<\*\>', r'(.+?)')
        
        try:
            match = re.search(regex_pattern, content)
            if match:
                # Assegna nomi alle variabili estratte
                for i, value in enumerate(match.groups()):
                    variables[f'variable_{i+1}'] = value.strip()
        except re.error:
            # Se il regex fallisce, ritorna vuoto
            pass
        
        return variables
    
    def get_template_statistics(self) -> Dict[str, Any]:
        """
        Restituisce statistiche sui template rilevati.
        
        WHY: Fornisce insights sulla varietà e distribuzione
        dei pattern di log rilevati nel sistema.
        
        Returns:
            Statistiche sui template e cluster
        """
        clusters = self.template_miner.drain.clusters
        
        stats = {
            'total_clusters': len(clusters),
            'total_logs_processed': sum(cluster.size for cluster in clusters),
            'top_templates': []
        }
        
        # Top 10 template più frequenti
        sorted_clusters = sorted(clusters, key=lambda c: c.size, reverse=True)
        for cluster in sorted_clusters[:10]:
            stats['top_templates'].append({
                'template': cluster.get_template(),
                'cluster_id': cluster.cluster_id,
                'size': cluster.size
            })
        
        return stats
