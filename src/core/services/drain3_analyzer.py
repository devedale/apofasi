"""
Servizio Drain3 per analisi di template e metadati sui log unificati.

WHY: Drain3 è ottimo per scoprire pattern automaticamente nei log,
estrarre template e identificare variabili dinamiche.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict, Counter
import hashlib

import re
from drain3 import TemplateMiner
from drain3.template_miner_config import TemplateMinerConfig


class Drain3Analyzer:
    """
    Analizzatore Drain3 per estrazione template e metadati.
    
    WHY: Utilizza Drain3 per scoprire automaticamente pattern nei log,
    estrarre template e identificare variabili dinamiche per ogni file
    e per l'intero dataset.
    
    Contract:
        - Input: Lista di log unificati o contenuto originale
        - Output: Template, variabili, statistiche per file e globali
        - Side effects: Nessuno, analisi pura
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Inizializza l'analizzatore Drain3.
        
        Args:
            config_path: Percorso al file di configurazione Drain3
        """
        self.logger = logging.getLogger(__name__)
        
        # Configurazione Drain3 semplificata
        self.config = TemplateMinerConfig()
        self._setup_default_config()
        
        # Template miner per analisi globale (senza persistence)
        self.global_miner = None  # Creeremo quando necessario
        
        # Template miner per file specifici
        self.file_miners = {}
        
        # Statistiche
        self.global_stats = {}
        self.file_stats = {}
    
    def _setup_default_config(self):
        """Configurazione di default per Drain3."""
        # Configurazione base
        self.config.profiling_enabled = True
        self.config.drain_sim_th = 0.4
        self.config.drain_depth = 4
        self.config.drain_max_children = 100
        self.config.drain_max_clusters = 1000
        
        # Disabilita completamente la persistence
        self.config.persistence_type = "NONE"
        self.config.persistence_file_name = None
        self.config.persistence_file_path = None
        
        # Configurazione aggiuntiva per evitare errori
        self.config.mask_digits_with_asterisk = True
        self.config.mask_hex = True
        self.config.mask_ips = True
        
        # Configurazione per evitare errori di persistence
        self.config.persistence_handler = None
    
    def analyze_unified_logs(self, unified_logs_path: Path) -> Dict[str, Any]:
        """
        Analizza i log unificati con Drain3.
        
        Args:
            unified_logs_path: Percorso al file unified_logs.json
            
        Returns:
            Risultati dell'analisi Drain3
        """
        print(f"🔍 DEBUG: Iniziando analisi log unificati: {unified_logs_path}")
        
        # Carica log unificati
        print("📖 DEBUG: Caricamento file JSON...")
        with open(unified_logs_path, 'r', encoding='utf-8') as f:
            unified_logs = json.load(f)
        print(f"📊 DEBUG: Caricati {len(unified_logs)} record")
        
        # Estrai contenuto originale
        print("🔍 DEBUG: Estrazione contenuti originali...")
        original_contents = []
        file_contents = defaultdict(list)
        
        for i, record in enumerate(unified_logs):
            if i % 100 == 0:  # Debug ogni 100 record
                print(f"🔄 DEBUG: Processando record {i}/{len(unified_logs)}")
            
            # Estrai contenuto originale
            content = record.get('original_content', '')
            if not content:
                content = record.get('raw_content', '')
            if not content:
                continue
            
            # Aggiungi a lista globale
            original_contents.append(content)
            
            # Aggiungi per file specifico
            source_file = record.get('source_file', 'unknown')
            file_contents[source_file].append(content)
        
        print(f"📝 DEBUG: Estratti {len(original_contents)} contenuti validi")
        print(f"📁 DEBUG: File trovati: {list(file_contents.keys())}")
        
        # Analisi globale
        print("🌍 DEBUG: Iniziando analisi globale...")
        global_analysis = self._analyze_content_batch(original_contents, "GLOBAL")
        print("✅ DEBUG: Analisi globale completata")
        
        # Analisi per file
        print("📁 DEBUG: Iniziando analisi per file...")
        file_analyses = {}
        for filename, contents in file_contents.items():
            if len(contents) > 0:  # Solo file con contenuto
                print(f"📄 DEBUG: Analizzando file {filename} ({len(contents)} record)")
                file_analyses[filename] = self._analyze_content_batch(contents, filename)
        
        # Risultati completi
        print("📋 DEBUG: Creando risultati finali...")
        results = {
            "analysis_timestamp": self._get_timestamp(),
            "total_records_analyzed": len(original_contents),
            "files_analyzed": len(file_analyses),
            "global_analysis": global_analysis,
            "file_analyses": file_analyses,
            "summary": self._create_summary(global_analysis, file_analyses)
        }
        
        print(f"✅ DEBUG: Analisi Drain3 completata: {len(original_contents)} record")
        return results
    
    def _create_summary(self, global_analysis: Dict[str, Any], file_analyses: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crea un riassunto dell'analisi.
        
        Args:
            global_analysis: Analisi globale
            file_analyses: Analisi per file
            
        Returns:
            Riassunto dell'analisi
        """
        summary = {
            "global_templates": global_analysis.get('statistics', {}).get('total_templates', 0),
            "total_files": len(file_analyses),
            "file_templates": {},
            "coverage_summary": {}
        }
        
        # Statistiche per file
        for filename, analysis in file_analyses.items():
            stats = analysis.get('statistics', {})
            summary["file_templates"][filename] = {
                "templates": stats.get('total_templates', 0),
                "logs": stats.get('total_logs', 0),
                "avg_logs_per_template": stats.get('avg_logs_per_template', 0)
            }
        
        # Riassunto coverage
        global_stats = global_analysis.get('statistics', {})
        coverage = global_stats.get('coverage_analysis', {})
        summary["coverage_summary"] = {
            "high_coverage": coverage.get('high_coverage_count', 0),
            "medium_coverage": coverage.get('medium_coverage_count', 0),
            "low_coverage": coverage.get('low_coverage_count', 0),
            "avg_coverage": coverage.get('avg_coverage_percentage', 0)
        }
        
        return summary
    
    def _analyze_content_batch(self, contents: List[str], identifier: str) -> Dict[str, Any]:
        """
        Analizza un batch di contenuti con Drain3.
        
        Args:
            contents: Lista di contenuti da analizzare
            identifier: Identificatore per il miner (GLOBAL o nome file)
            
        Returns:
            Risultati dell'analisi
        """
        print(f"🔧 DEBUG: Iniziando analisi batch {identifier} con {len(contents)} contenuti")
        
        try:
            # Crea miner per questo batch con configurazione pulita
            print(f"⚙️ DEBUG: Configurazione Drain3 per {identifier}...")
            config = TemplateMinerConfig()
            config.profiling_enabled = True
            config.drain_sim_th = 0.4
            config.drain_depth = 4
            config.drain_max_children = 100
            config.drain_max_clusters = 1000
            config.persistence_type = "NONE"
            config.mask_digits_with_asterisk = True
            config.mask_hex = True
            config.mask_ips = True
            
            # Crea il miner con configurazione personalizzata
            miner = TemplateMiner(config=config)
            print(f"✅ DEBUG: Miner Drain3 creato per {identifier}")
            
            # Processa tutti i contenuti
            print(f"🔄 DEBUG: Processando {len(contents)} contenuti per {identifier}...")
            for i, content in enumerate(contents):
                if i % 50 == 0 and i > 0:  # Debug ogni 50 record
                    print(f"📊 DEBUG: Processati {i}/{len(contents)} contenuti per {identifier}")
                
                try:
                    result = miner.add_log_message(content)
                    if result["change_type"] == "cluster_created":
                        print(f"🆕 DEBUG: Nuovo template in {identifier}: {result['template_mined']}")
                except Exception as e:
                    print(f"⚠️ DEBUG: Errore contenuto {i} in {identifier}: {e}")
            
            print(f"✅ DEBUG: Processamento completato per {identifier}")
            
            # Estrai risultati
            print(f"📋 DEBUG: Estrazione risultati per {identifier}...")
            
            # Crea un riassunto dei template in un formato simile a quello precedente
            templates = [
                {
                    "cluster_id": cluster.cluster_id,
                    "template_mined": " ".join(cluster.log_template_tokens),
                    "size": cluster.size
                }
                for cluster in miner.drain.clusters
            ]
            
            print(f"📊 DEBUG: Trovati {len(templates)} template per {identifier}")
            
            # Calcola statistiche
            stats = self._calculate_template_stats(templates, contents)
            
            # Estrai variabili dinamiche
            variables = self._extract_dynamic_variables(templates)
            
            result = {
                "identifier": identifier,
                "total_logs": len(contents),
                "templates": templates,
                "statistics": stats,
                "dynamic_variables": variables,
                "template_distribution": self._get_template_distribution(templates)
            }
            
            print(f"✅ DEBUG: Analisi batch {identifier} completata")
            return result
            
        except Exception as e:
            print(f"❌ DEBUG: Errore analisi batch {identifier}: {e}")
            import traceback
            traceback.print_exc()
            return {
                "identifier": identifier,
                "total_logs": len(contents),
                "templates": [],
                "statistics": {"error": str(e)},
                "dynamic_variables": {},
                "template_distribution": {}
            }
    
    def _calculate_template_stats(self, templates: List[Dict], contents: List[str]) -> Dict[str, Any]:
        """
        Calcola statistiche sui template.
        
        Args:
            templates: Template estratti da Drain3
            contents: Contenuti originali
            
        Returns:
            Statistiche sui template
        """
        if not templates:
            return {"error": "Nessun template trovato"}
        
        total_logs = len(contents)
        total_templates = len(templates)
        
        # Calcola coverage per template
        template_coverage = {}
        for template in templates:
            template_id = template.get('cluster_id', 'unknown')
            count = template.get('size', 0)
            percentage = (count / total_logs) * 100 if total_logs > 0 else 0
            template_coverage[template_id] = {
                "count": count,
                "percentage": round(percentage, 2),
                "template": template.get('template_mined', 'unknown')
            }
        
        # Trova template più comuni
        sorted_templates = sorted(template_coverage.items(), 
                                key=lambda x: x[1]['count'], reverse=True)
        
        return {
            "total_templates": total_templates,
            "total_logs": total_logs,
            "avg_logs_per_template": round(total_logs / total_templates, 2) if total_templates > 0 else 0,
            "template_coverage": template_coverage,
            "top_templates": sorted_templates[:10],  # Top 10
            "coverage_analysis": self._analyze_coverage(template_coverage)
        }
    
    def _analyze_coverage(self, template_coverage: Dict) -> Dict[str, Any]:
        """
        Analizza la copertura dei template.
        
        Args:
            template_coverage: Dizionario con coverage per template
            
        Returns:
            Analisi della copertura
        """
        if not template_coverage:
            return {"error": "Nessun template disponibile"}
        
        percentages = [info['percentage'] for info in template_coverage.values()]
        
        # Template con alta copertura (>10%)
        high_coverage = {tid: info for tid, info in template_coverage.items() 
                        if info['percentage'] > 10}
        
        # Template con media copertura (1-10%)
        medium_coverage = {tid: info for tid, info in template_coverage.items() 
                          if 1 <= info['percentage'] <= 10}
        
        # Template con bassa copertura (<1%)
        low_coverage = {tid: info for tid, info in template_coverage.items() 
                       if info['percentage'] < 1}
        
        return {
            "high_coverage_count": len(high_coverage),
            "medium_coverage_count": len(medium_coverage),
            "low_coverage_count": len(low_coverage),
            "avg_coverage_percentage": round(sum(percentages) / len(percentages), 2),
            "max_coverage_percentage": max(percentages),
            "min_coverage_percentage": min(percentages)
        }
    
    def _extract_dynamic_variables(self, templates: List[Dict]) -> Dict[str, Any]:
        """
        Estrae variabili dinamiche dai template usando regex per un match preciso.
        
        Args:
            templates: Template estratti
            
        Returns:
            Variabili dinamiche estratte
        """
        variables = {}
        # Regex per trovare tutte le variabili nel formato <...>
        variable_pattern = re.compile(r"<([^>]+)>")

        for template in templates:
            template_text = template.get('template_mined', '')
            if not template_text:
                continue
            
            # Trova tutte le corrispondenze con il pattern regex
            dynamic_parts = variable_pattern.findall(template_text)
            
            if dynamic_parts:
                template_id = template.get('cluster_id', 'unknown')
                
                # Sostituiamo i nomi generici con i nomi reali delle maschere
                named_variables = {}
                for i, var_name in enumerate(dynamic_parts):
                    # Se il nome è '*', usiamo un nome generico, altrimenti il nome della maschera
                    key = f"variable_{i+1}"
                    named_variables[key] = var_name if var_name != '*' else 'wildcard'

                variables[template_id] = {
                    "template": template_text,
                    "variable_count": len(dynamic_parts),
                    "variables": named_variables, # Usiamo il dizionario con nomi
                    "sample_size": template.get('size', 0)
                }
        
        return {
            "total_templates_with_variables": len(variables),
            "templates": variables,
            "variable_statistics": self._calculate_variable_stats(variables)
        }
    
    def _calculate_variable_stats(self, variables: Dict) -> Dict[str, Any]:
        """
        Calcola statistiche sulle variabili.
        
        Args:
            variables: Dizionario con variabili per template
            
        Returns:
            Statistiche sulle variabili
        """
        if not variables:
            return {"error": "Nessuna variabile trovata"}
        
        variable_counts = [info['variable_count'] for info in variables.values()]
        
        return {
            "total_templates": len(variables),
            "avg_variables_per_template": round(sum(variable_counts) / len(variable_counts), 2),
            "max_variables_in_template": max(variable_counts),
            "min_variables_in_template": min(variable_counts),
            "total_variables": sum(variable_counts)
        }
    
    def _get_template_distribution(self, templates: List[Dict]) -> Dict[str, int]:
        """
        Ottiene la distribuzione dei template.
        
        Args:
            templates: Template estratti
            
        Returns:
            Distribuzione template -> count
        """
        distribution = {}
        for template in templates:
            template_id = template.get('cluster_id', 'unknown')
            count = template.get('size', 0)
            distribution[template_id] = count
        
        return distribution
    
    def _get_timestamp(self) -> str:
        """Ottiene timestamp corrente."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def save_analysis_results(self, results: Dict[str, Any], output_path: Path):
        """
        Salva i risultati dell'analisi.
        
        Args:
            results: Risultati dell'analisi
            output_path: Percorso di output
        """
        output_path.parent.mkdir(exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=str)
        
        self.logger.info(f"💾 Risultati analisi salvati: {output_path}")
    
    def print_summary(self, results: Dict[str, Any]):
        """
        Stampa un riassunto dell'analisi.
        
        Args:
            results: Risultati dell'analisi
        """
        print("\n" + "="*80)
        print("📊 RISULTATI ANALISI DRAIN3")
        print("="*80)
        
        summary = results.get('summary', {})
        
        print(f"📈 Statistiche Globali:")
        print(f"   - Record analizzati: {results.get('total_records_analyzed', 0)}")
        print(f"   - File analizzati: {results.get('files_analyzed', 0)}")
        
        global_analysis = results.get('global_analysis', {})
        if global_analysis:
            stats = global_analysis.get('statistics', {})
            print(f"   - Template totali: {stats.get('total_templates', 0)}")
            print(f"   - Media log per template: {stats.get('avg_logs_per_template', 0)}")
            
            coverage = stats.get('coverage_analysis', {})
            print(f"   - Template alta copertura: {coverage.get('high_coverage_count', 0)}")
            print(f"   - Template media copertura: {coverage.get('medium_coverage_count', 0)}")
            print(f"   - Template bassa copertura: {coverage.get('low_coverage_count', 0)}")
        
        print("\n📁 Analisi per File:")
        file_analyses = results.get('file_analyses', {})
        for filename, analysis in list(file_analyses.items())[:5]:  # Mostra solo primi 5
            stats = analysis.get('statistics', {})
            print(f"   - {filename}: {stats.get('total_templates', 0)} template, "
                  f"{stats.get('total_logs', 0)} log")
        
        print("="*80) 