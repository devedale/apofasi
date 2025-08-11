"""
CLI Parser - Interfaccia a linea di comando per il sistema di parsing
Questo script fornisce un'interfaccia semplice per processare file
e cartelle utilizzando il sistema di parsing refactorizzato.
Author: Edoardo D'Alesio
Version: 2.2.0
"""

import sys
import argparse
import time
from pathlib import Path
from typing import List, Dict, Any

# Aggiungi il path del progetto per gli import
sys.path.insert(0, str(Path(__file__).parent))

from src.application.services.parsing_service import ParsingService
from src.application.services.reporting_service import ReportingService
from src.application.services.configuration_service import ConfigurationService
from src.infrastructure.unified.unified_log_writer_fs import UnifiedLogWriterFs
from src.domain.entities.log_entry import LogEntry
from src.infrastructure.log_reader import SimpleLogReader
from src.infrastructure.hybrid_anonymizer_service import HybridAnonymizerService
from src.domain.services.centralized_regex_service import CentralizedRegexServiceImpl


def apply_presidio_anonymization(parsed_results: List[Any], hybrid_anonymizer: HybridAnonymizerService, 
                                mode: str, show_details: bool) -> List[Any]:
    """
    Applica anonimizzazione Presidio ai risultati del parsing e mostra dettagli.
    
    Args:
        parsed_results: Lista dei risultati del parsing
        hybrid_anonymizer: Servizio di anonimizzazione ibrido
        mode: Modalità anonimizzazione ('presidio' o 'hybrid')
        show_details: Se mostrare dettagli completi Presidio
        
    Returns:
        Lista dei risultati con anonimizzazione Presidio applicata
    """

    
    enhanced_results = []
    for i, record in enumerate(parsed_results):
        try:
            # Supporta sia dict che oggetti con attributi
            if isinstance(record, dict):
                original_text = record.get('original_content') or record.get('raw_line') or ''
            else:
                original_text = getattr(record, 'original_content', '') or getattr(record, 'raw_line', '')

            if not original_text:
                enhanced_results.append(record)
                continue

            anonymization_result = hybrid_anonymizer.anonymize_content(original_text, mode)

            # Attacca il risultato completo al record e aggiorna anonymized_message per compatibilità
            if isinstance(record, dict):
                record['presidio_anonymization'] = anonymization_result
                if mode == 'hybrid':
                    record['anonymized_message'] = anonymization_result.get('classic_anonymization', {}).get('anonymized_content', record.get('anonymized_message'))
                elif mode == 'presidio':
                    record['anonymized_message'] = anonymization_result.get('anonymized_content', record.get('anonymized_message'))
            else:
                setattr(record, 'presidio_anonymization', anonymization_result)
                if mode == 'hybrid':
                    setattr(record, 'anonymized_message', anonymization_result.get('classic_anonymization', {}).get('anonymized_content', getattr(record, 'anonymized_message', None)))
                elif mode == 'presidio':
                    setattr(record, 'anonymized_message', anonymization_result.get('anonymized_content', getattr(record, 'anonymized_message', None)))

            # Mostra dettagli (solo primi 5 per non intasare)
            if show_details and i < 5:
                print(f"\n📊 Record {i+1} - Anonimizzazione {mode.upper()}:")
                print(f"   Originale: {original_text[:80]}...")
                if mode == 'hybrid':
                    classic = anonymization_result.get('classic_anonymization', {})
                    presidio = anonymization_result.get('presidio_anonymization', {})
                    print(f"   Classic:   {classic.get('anonymized_content', 'ERROR')[:80]}...")
                    print(f"   Presidio:  {presidio.get('anonymized_content', 'ERROR')[:80]}...")
                    hybrid_meta = anonymization_result.get('hybrid_metadata', {})
                    print(f"   Entità Classic: {hybrid_meta.get('total_entities_classic', 0)}")
                    print(f"   Entità Presidio: {hybrid_meta.get('total_entities_presidio', 0)}")
                elif mode == 'presidio':
                    entities = anonymization_result.get('entities_detected', [])
                    print(f"   Entità rilevate: {len(entities)}")
                    if entities:
                        print("   Entità specifiche:")
                        for entity in entities[:3]:
                            print(f"     - {entity.get('entity_type', 'unknown')}: '{entity.get('text', '')}' (score: {entity.get('score', 0):.2f})")

            enhanced_results.append(record)

        except Exception as e:
            print(f"⚠️ Errore anonimizzazione Presidio per record {i+1}: {e}")
            enhanced_results.append(record)

    return enhanced_results


def run_sampling(input_paths: List[str], output_file: str, lines_per_file: int, config: Dict[str, Any], 
                 anonymization_mode: str = 'hybrid', show_presidio_details: bool = False):
    """
    Estrae e PARSA le prime N righe da ogni file, salvando un report strutturato.
    
    Args:
        input_paths: Percorsi dei file da processare
        output_file: File di output per il report
        lines_per_file: Numero di righe da campionare per file
        config: Configurazione dell'applicazione
        anonymization_mode: Modalità anonimizzazione ('classic', 'presidio', 'hybrid')
        show_presidio_details: Se mostrare dettagli Presidio
    """
    from tqdm import tqdm
    


    # 1. Inizializza il servizio di parsing
    parsing_service = ParsingService(config)
    
    # Inizializza servizio anonimizzazione ibrido se Presidio è abilitato
    hybrid_anonymizer = None
    if anonymization_mode in ['presidio', 'hybrid'] and config.get('presidio', {}).get('enabled', False):
        try:
            centralized_regex_service = CentralizedRegexServiceImpl(config)
            hybrid_anonymizer = HybridAnonymizerService(config, centralized_regex_service)

        except Exception as e:
            print(f"⚠️ Presidio non disponibile: {e}")
            if anonymization_mode == 'presidio':
                print("🔄 Fallback a modalità classic (regex)")
                anonymization_mode = 'classic'
            hybrid_anonymizer = None

    # 2. Trova tutti i file di input
    all_files: List[Path] = []
    for path_str in input_paths:
        path = Path(path_str)
        if path.is_dir():
            all_files.extend(sorted(p for p in path.rglob('*') if p.is_file()))
        elif path.is_file():
            all_files.append(path)
    
    total_files = len(all_files)
    

    # 3. Processa ogni file e scrivi l'output con barra di progresso
    with open(output_file, 'w', encoding='utf-8') as outfile:
        with tqdm(total=total_files, desc="📄 Processing files", unit="file") as pbar:
            for i, file_path in enumerate(all_files):
                # Aggiorna descrizione della barra
                pbar.set_description(f"📄 Processing: {file_path.name}")
                
                try:
                    # Usa il LogProcessingService per processare solo le prime N righe
                    records = list(parsing_service.log_processing_service.process_file_sample(file_path, lines_per_file))
                    
                    if not records:
                        outfile.write(f"  -> File vuoto o illeggibile.\n\n")
                        pbar.update(1)
                        continue
                    
                    # Scrivi header del file
                    outfile.write(f"### File: {file_path.name} ###\n\n")
                    
                    # Formatta e scrivi l'output per ogni record
                    for record in records:
                        # Applica anonimizzazione Presidio se disponibile
                        if hybrid_anonymizer and record.original_content:
                            try:
                                anonymization_result = hybrid_anonymizer.anonymize_content(record.original_content, mode=anonymization_mode)
                                record.presidio_anonymization = anonymization_result
                            except Exception as e:
                                print(f"⚠️ Errore anonimizzazione Presidio per record: {e}")
                        
                        outfile.write(f"  [L:{record.line_number}] Original: {record.original_content[:100]}{'...' if len(record.original_content) > 100 else ''}\n")
                        outfile.write(f"    Parser: {record.parser_name}\n")
                        
                        # Mostra metadati del parsing
                        if record.detected_headers:
                            outfile.write(f"    Detected Headers: {record.detected_headers}\n")
                        if record.template:
                            outfile.write(f"    Template: {record.template[:100]}{'...' if len(record.template) > 100 else ''}\n")
                        if record.cluster_id is not None:
                            outfile.write(f"    Cluster ID: {record.cluster_id}\n")
                        if record.cluster_size is not None:
                            outfile.write(f"    Cluster Size: {record.cluster_size}\n")
                        if record.detected_patterns:
                            outfile.write(f"    Detected Patterns: {record.detected_patterns}\n")
                        
                        # Mostra timestamp_info se presente nei dati parsati
                        parsed_data = record.parsed_data
                        if parsed_data and 'timestamp_info' in parsed_data:
                            outfile.write(f"    Timestamp Info: {parsed_data['timestamp_info']}\n")
                        
                        # Mostra dati parsati (tutti i campi, ma formattati in modo leggibile)
                        if parsed_data:
                            outfile.write(f"    Parsed Data:\n")
                            for key, value in parsed_data.items():
                                # Salta timestamp_info perché già mostrato sopra
                                if key == 'timestamp_info':
                                    continue
                                # Formatta il valore in modo leggibile
                                value_str = str(value)
                                if len(value_str) > 100:
                                    value_str = value_str[:100] + "..."
                                outfile.write(f"      - {key}: {value_str}\n")
                        else:
                            outfile.write(f"    Parsed Data: {{}}\n")
                        
                        # Mostra risultati anonimizzazione Presidio se disponibili
                        if hasattr(record, 'presidio_anonymization') and record.presidio_anonymization:
                            presidio_result = record.presidio_anonymization
                            outfile.write(f"    🔐 Presidio Anonymization ({anonymization_mode.upper()}):\n")
                            
                            if anonymization_mode == 'hybrid':
                                # Modalità ibrida: mostra entrambi i risultati
                                classic = presidio_result.get('classic_anonymization', {})
                                presidio = presidio_result.get('presidio_anonymization', {})
                                
                                outfile.write(f"      Classic: {classic.get('anonymized_content', 'ERROR')[:80]}...\n")
                                outfile.write(f"      Presidio: {presidio.get('anonymized_content', 'ERROR')[:80]}...\n")
                                
                                # Metadati ibridi
                                hybrid_meta = presidio_result.get('hybrid_metadata', {})
                                outfile.write(f"      Entità Classic: {hybrid_meta.get('total_entities_classic', 0)}\n")
                                outfile.write(f"      Entità Presidio: {hybrid_meta.get('total_entities_presidio', 0)}\n")
                                
                            elif anonymization_mode == 'presidio':
                                # Modalità solo Presidio
                                outfile.write(f"      Anonimizzato: {presidio_result.get('anonymized_content', 'ERROR')[:80]}...\n")
                                outfile.write(f"      Entità rilevate: {len(presidio_result.get('entities_detected', []))}\n")
                                
                                # Mostra entità specifiche
                                entities = presidio_result.get('entities_detected', [])
                                if entities:
                                    outfile.write("      Entità specifiche:\n")
                                    for entity in entities[:3]:  # Solo le prime 3
                                        entity_type = entity.get('entity_type', 'unknown')
                                        entity_text = entity.get('text', '')
                                        entity_score = entity.get('score', 0)
                                        outfile.write(f"        - {entity_type}: '{entity_text}' (score: {entity_score:.2f})\n")
                        
                        errors = record.processing_errors if hasattr(record, 'processing_errors') else []
                        if errors:
                            outfile.write("    Errors:\n")
                            for err in errors:
                                outfile.write(f"      - {err}\n")
                        outfile.write("-" * 20 + "\n")
                    outfile.write("\n")
                    
                    # Aggiorna la barra di progresso
                    pbar.update(1)

                except Exception as e:
                    error_message = f"### Errore durante la processazione di: {file_path.name} - {e} ###\n\n"
                    outfile.write(error_message)
                    print(f"❌ Errore in {file_path.name}: {e}")
                    pbar.update(1)

    print(f"\n✅ Campionamento e parsing completati. Report salvato in: {output_file}")


def main():
    """Funzione principale del CLI."""
    parser = argparse.ArgumentParser(
        description='CLI Parser - Sistema di parsing log unificato',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi di utilizzo:
  # Parsing completo con Presidio (modalità ibrida)
  python3 cli_parser.py parse logs/ output/ --anonymization-mode hybrid --show-presidio-details
  
  # Parsing solo con regex classico
  python3 cli_parser.py parse logs/ output/ --anonymization-mode classic
  
  # Parsing solo con Presidio AI
  python3 cli_parser.py parse logs/ output/ --anonymization-mode presidio --show-presidio-details
  
  # Campionamento con Presidio
  python3 cli_parser.py sample logs/ sample_report.txt --lines 5 --anonymization-mode hybrid
  
  # Generazione log unificato
  python3 cli_parser.py generate-unified-log outputs --anonymize
  
  # Mostra formati supportati
  python3 cli_parser.py formats --config config/config.yaml
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', required=True, help='Comandi disponibili')

    # Sub-parser per il comando 'parse'
    parse_parser = subparsers.add_parser('parse', help='Esegue il parsing completo di file o directory')
    parse_parser.add_argument('input_path', type=str, help='Directory o file di input da processare')
    parse_parser.add_argument('output_dir', type=str, help='Directory di output per i risultati')
    parse_parser.add_argument('--config', '-c', default='config/config.yaml', help='File di configurazione')
    parse_parser.add_argument('--export-logppt', action='store_true', help='Esporta dataset training compatibile (TSV/JSON)')
    parse_parser.add_argument('--dump-drain3', action='store_true', help='Esporta dump completo Drain3 (cluster/template)')
    parse_parser.add_argument('--anonymization-mode', '-a', choices=['classic', 'presidio', 'hybrid'], default='hybrid', 
                             help='Modalità anonimizzazione: classic (regex), presidio (AI), hybrid (entrambi)')
    parse_parser.add_argument('--show-presidio-details', action='store_true', help='Mostra dettagli completi Presidio e metadati')

    # Sub-parser per il comando 'sample'
    sample_parser = subparsers.add_parser('sample', help='Estrae e parsa un campione di righe da ogni file')
    sample_parser.add_argument('input_paths', nargs='+', help='Uno o più file o directory di input')
    sample_parser.add_argument('output_file', type=str, help='File di output per il report dei campioni')
    sample_parser.add_argument('--lines', '-l', type=int, default=3, help='Numero di righe da campionare (default: 3)')
    sample_parser.add_argument('--config', '-c', default='config/config.yaml', help='File di configurazione')
    sample_parser.add_argument('--anonymization-mode', '-a', choices=['classic', 'presidio', 'hybrid'], default='hybrid',
                             help='Modalità anonimizzazione per il campionamento')
    sample_parser.add_argument('--show-presidio-details', action='store_true', help='Mostra dettagli Presidio nel campionamento')

    # Sub-parser per il comando 'generate-unified-log'
    unified_log_parser = subparsers.add_parser('generate-unified-log', help='Genera un log unificato dai risultati')
    unified_log_parser.add_argument('input_dir', type=str, help='Directory contenente i risultati del parsing (JSON)')
    unified_log_parser.add_argument('--anonymize', action='store_true', help='Usa i dati anonimizzati se disponibili')

    # Sub-parser per il comando 'formats'
    formats_parser = subparsers.add_parser('formats', help='Mostra i formati di file supportati e le loro configurazioni')
    formats_parser.add_argument('--config', '-c', default='config/config.yaml', help='File di configurazione')
    
    args = parser.parse_args()
    
    # Carica configurazione
    config_service = ConfigurationService()
    config = config_service.load_configuration(args.config if hasattr(args, 'config') else 'config/config.yaml')
    
    print("🚀 CLI Parser - Sistema di Parsing Unificato")
    print("=" * 60)
    
    start_time = time.time()

    try:
        if args.command == 'sample':
            anonymization_mode = getattr(args, 'anonymization_mode', 'hybrid')
            show_presidio_details = getattr(args, 'show_presidio_details', False)
            run_sampling(args.input_paths, args.output_file, args.lines, config, anonymization_mode, show_presidio_details)

        elif args.command == 'parse':
            output_dir = Path(args.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Configura modalità anonimizzazione
            anonymization_mode = getattr(args, 'anonymization_mode', 'hybrid')
            show_presidio_details = getattr(args, 'show_presidio_details', False)
            
            print(f"🔐 Modalità anonimizzazione: {anonymization_mode.upper()}")
            if show_presidio_details:
                print("🔍 Mostrando dettagli completi Presidio e metadati")
            
            # Inizializza servizio anonimizzazione ibrido se Presidio è abilitato
            hybrid_anonymizer = None
            if anonymization_mode in ['presidio', 'hybrid'] and config.get('presidio', {}).get('enabled', False):
                try:
                    centralized_regex_service = CentralizedRegexServiceImpl(config)
                    hybrid_anonymizer = HybridAnonymizerService(config, centralized_regex_service)
                    print("✅ Servizio Presidio inizializzato correttamente")
                except Exception as e:
                    print(f"⚠️ Presidio non disponibile: {e}")
                    if anonymization_mode == 'presidio':
                        print("🔄 Fallback a modalità classic (regex)")
                        anonymization_mode = 'classic'
                    hybrid_anonymizer = None
            
            parsing_service = ParsingService(config)
            
            # Passa config per permettere anonimizzazione mirata di campi in parsed_data
            # WHY: ReportingService ha bisogno di centralized_regex_service per anonimizzazione coerente
            reporting_service = ReportingService(
                output_dir, 
                config=config, 
                centralized_regex_service=parsing_service.centralized_regex_service
            )
            
            print(f"📄 Eseguendo il parsing di: {args.input_path}")
            parsed_results = parsing_service.parse_files(args.input_path)
            
            # Applica anonimizzazione Presidio se richiesto
            if hybrid_anonymizer and anonymization_mode in ['presidio', 'hybrid']:
                print(f"🔐 Applicando anonimizzazione {anonymization_mode.upper()}...")
                enhanced_results = apply_presidio_anonymization(parsed_results, hybrid_anonymizer, anonymization_mode, show_presidio_details)
            else:
                enhanced_results = parsed_results
            
            print("📊 Generando report completi...")
            report = reporting_service.generate_comprehensive_report(enhanced_results)
            reporting_service.generate_pure_data_files(enhanced_results)

            # Export opzionali
            if getattr(args, 'export_logppt', False):
                reporting_service.export_training_datasets(parsed_results)
                reporting_service.export_logppt_input_csv(parsed_results)
            if getattr(args, 'dump_drain3', False):
                reporting_service.export_drain3_dump(parsed_results)
            
            print("🎉 PARSING COMPLETATO")
            print(f"⏱️  Tempo totale: {time.time() - start_time:.2f}s")
            print(f"📈 Record totali: {report['general_statistics']['total_records']}")
            print(f"✅ Success rate: {report['general_statistics']['success_rate']:.1f}%")
            print(f"📄 Report e dati salvati in: {output_dir.as_posix()}")

        elif args.command == 'generate-unified-log':
            print(f"🔄 Generando log unificato da: {args.input_dir}")
            # Carica tutti i ParsedRecord dai risultati JSON esistenti? (placeholder)
            # In questa CLI essenziale ci limitiamo a notificare la feature e a creare un writer
            writer = UnifiedLogWriterFs(Path(args.input_dir))
            print("⚠️  Generazione unificata diretta da input_dir richiede la ricostruzione dei ParsedRecord.")
            print("   Usa il flusso 'parse' per generare i file unificati automaticamente.")

        elif args.command == 'formats':
            """Mostra i formati di file supportati e le loro configurazioni."""
            print("📋 FORMATI DI FILE SUPPORTATI")
            print("=" * 60)
            
            # Carica la configurazione
            config = config_service.load_configuration(args.config)
            
            # Crea il FileFormatService per ottenere le informazioni
            from src.core.services.file_format_service import FileFormatService
            file_format_service = FileFormatService(config)
            
            # Mostra le informazioni sui formati
            formats_summary = file_format_service.get_formats_summary()
            
            print(f"📊 Totale formati supportati: {formats_summary['total_formats']}")
            print(f"🔧 Logging verbose: {'✅ Abilitato' if formats_summary['verbose_logging'] else '❌ Disabilitato'}")
            print()
            
            print("📝 DETTAGLI FORMATI:")
            print("-" * 60)
            
            for format_name, description in formats_summary['supported_formats'].items():
                priority = formats_summary['parser_priorities'].get(format_name, "N/A")
                parser = formats_summary['parser_mapping'].get(format_name, "Default")
                
                print(f"  • {format_name.upper():<12} | Priorità: {priority:<2} | Parser: {parser:<20}")
                print(f"    {description}")
                print()
            
            print("=" * 60)

        return 0

    except FileNotFoundError as e:
        print(f"❌ Errore: File non trovato - {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ Errore inaspettato: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
