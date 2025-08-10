"""
Servizio per analisi completa dei log unificati con Drain3.

WHY: Combina la generazione di file unificati con l'analisi Drain3
per fornire metadati e template sui log originali.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from tqdm import tqdm

from ...core.services.drain3_analyzer import Drain3Analyzer
from .reporting_service import ReportingService


class UnifiedAnalysisService:
    """
    Servizio per analisi completa dei log unificati.
    
    WHY: Coordina la generazione di file unificati con l'analisi Drain3
    per fornire metadati, template e statistiche sui log originali.
    
    Contract:
        - Input: Risultati di parsing
        - Output: File unificati + analisi Drain3
        - Side effects: Genera file di output
    """
    
    def __init__(self, output_dir: Path):
        """
        Inizializza il servizio di analisi unificata.
        
        Args:
            output_dir: Directory di output
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger(__name__)
        
        # Inizializza servizi
        self.reporting_service = ReportingService(output_dir)
        self.drain3_analyzer = Drain3Analyzer()
    
    def process_parsed_results(self, parsed_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Processa i risultati di parsing con analisi completa.
        
        Args:
            parsed_results: Risultati di parsing
            
        Returns:
            Risultati dell'analisi completa
        """
        print("\n🎯 INIZIANDO ANALISI COMPLETA")
        print("=" * 60)
        
        # Step 1: Genera file unificati
        print("📝 Fase 1/3: Generazione file unificati...")
        with tqdm(total=100, desc="Generazione file unificati", ncols=80) as pbar:
            pbar.update(20)  # Inizio
            self.reporting_service.generate_comprehensive_report(parsed_results)
            pbar.update(80)  # Completato
        
        # Step 2: Analizza con Drain3
        unified_logs_path = self.output_dir / "unified_logs.json"
        if unified_logs_path.exists():
            print("\n🔍 Fase 2/3: Analisi Drain3...")
            with tqdm(total=100, desc="Analisi template e metadati", ncols=80) as pbar:
                pbar.update(30)  # Inizio analisi
                drain3_results = self.drain3_analyzer.analyze_unified_logs(unified_logs_path)
                pbar.update(70)  # Completato
            
            # Step 3: Salva risultati Drain3
            print("\n💾 Fase 3/3: Salvataggio risultati...")
            with tqdm(total=100, desc="Salvataggio risultati", ncols=80) as pbar:
                pbar.update(50)  # Inizio salvataggio
                drain3_output = self.output_dir / "drain3_analysis.json"
                self.drain3_analyzer.save_analysis_results(drain3_results, drain3_output)
                pbar.update(50)  # Completato
            
            return {
                "unified_logs_file": str(unified_logs_path),
                "drain3_analysis_file": str(drain3_output),
                "drain3_results": drain3_results
            }
        else:
            print("❌ File unificati non trovato")
            return {"error": "File unificati non generato"}
    
    def get_analysis_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ottiene un riassunto dell'analisi.
        
        Args:
            results: Risultati dell'analisi
            
        Returns:
            Riassunto dell'analisi
        """
        if "error" in results:
            return {"error": results["error"]}
        
        drain3_results = results.get("drain3_results", {})
        
        summary = {
            "files_generated": [
                results.get("unified_logs_file", "N/A"),
                results.get("drain3_analysis_file", "N/A")
            ],
            "total_records": drain3_results.get("total_records_analyzed", 0),
            "files_analyzed": drain3_results.get("files_analyzed", 0),
            "global_templates": 0,
            "file_templates": {}
        }
        
        # Estrai statistiche globali
        global_analysis = drain3_results.get("global_analysis", {})
        if global_analysis:
            stats = global_analysis.get("statistics", {})
            summary["global_templates"] = stats.get("total_templates", 0)
        
        # Estrai statistiche per file
        file_analyses = drain3_results.get("file_analyses", {})
        for filename, analysis in file_analyses.items():
            stats = analysis.get("statistics", {})
            summary["file_templates"][filename] = {
                "templates": stats.get("total_templates", 0),
                "logs": stats.get("total_logs", 0)
            }
        
        return summary
    
    def print_final_summary(self, results: Dict[str, Any]):
        """
        Stampa il riassunto finale dell'analisi.
        
        Args:
            results: Risultati dell'analisi
        """
        summary = self.get_analysis_summary(results)
        
        if "error" in summary:
            print(f"\n❌ Errore: {summary['error']}")
            return
        
        print("\n" + "="*80)
        print("🎯 ANALISI COMPLETA FINALIZZATA")
        print("="*80)
        
        print(f"📁 File generati:")
        for file_path in summary["files_generated"]:
            print(f"   - {file_path}")
        
        print(f"\n📊 Statistiche:")
        print(f"   - Record totali: {summary['total_records']}")
        print(f"   - File analizzati: {summary['files_analyzed']}")
        print(f"   - Template globali: {summary['global_templates']}")
        
        if summary["file_templates"]:
            print(f"\n📋 Template per file:")
            for filename, stats in list(summary["file_templates"].items())[:5]:
                print(f"   - {filename}: {stats['templates']} template, {stats['logs']} log")
        
        print("="*80) 