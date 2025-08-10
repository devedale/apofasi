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


def run_sampling(input_paths: List[str], output_file: str, lines_per_file: int, config: Dict[str, Any]):
    """
    Estrae e PARSA le prime N righe da ogni file, salvando un report strutturato.
    """
    from tqdm import tqdm
    
    print(f"📄 Eseguendo parsing di {lines_per_file} righe da ogni file in {len(input_paths)} percorsi...")

    # 1. Inizializza il servizio di parsing
    parsing_service = ParsingService(config)

    # 2. Trova tutti i file di input
    all_files: List[Path] = []
    for path_str in input_paths:
        path = Path(path_str)
        if path.is_dir():
            all_files.extend(sorted(p for p in path.rglob('*') if p.is_file()))
        elif path.is_file():
            all_files.append(path)
    
    total_files = len(all_files)
    print(f"🔍 Trovati {total_files} file da processare.")

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
  python3 cli_parser.py parse examples outputs
  python3 cli_parser.py sample examples outputs/samples_report.txt --lines 5
  python3 cli_parser.py generate-unified-log outputs --anonymize
  python3 cli_parser.py formats --config config/config.ini
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', required=True, help='Comandi disponibili')

    # Sub-parser per il comando 'parse'
    parse_parser = subparsers.add_parser('parse', help='Esegue il parsing completo di file o directory')
    parse_parser.add_argument('input_path', type=str, help='Directory o file di input da processare')
    parse_parser.add_argument('output_dir', type=str, help='Directory di output per i risultati')
    parse_parser.add_argument('--config', '-c', default='config/parser_config.yaml', help='File di configurazione')
    parse_parser.add_argument('--export-logppt', action='store_true', help='Esporta dataset training compatibile (TSV/JSON)')
    parse_parser.add_argument('--dump-drain3', action='store_true', help='Esporta dump completo Drain3 (cluster/template)')

    # Sub-parser per il comando 'sample'
    sample_parser = subparsers.add_parser('sample', help='Estrae e parsa un campione di righe da ogni file')
    sample_parser.add_argument('input_paths', nargs='+', help='Uno o più file o directory di input')
    sample_parser.add_argument('output_file', type=str, help='File di output per il report dei campioni')
    sample_parser.add_argument('--lines', '-l', type=int, default=3, help='Numero di righe da campionare (default: 3)')
    sample_parser.add_argument('--config', '-c', default='config/parser_config.yaml', help='File di configurazione')

    # Sub-parser per il comando 'generate-unified-log'
    unified_log_parser = subparsers.add_parser('generate-unified-log', help='Genera un log unificato dai risultati')
    unified_log_parser.add_argument('input_dir', type=str, help='Directory contenente i risultati del parsing (JSON)')
    unified_log_parser.add_argument('--anonymize', action='store_true', help='Usa i dati anonimizzati se disponibili')

    # Sub-parser per il comando 'formats'
    formats_parser = subparsers.add_parser('formats', help='Mostra i formati di file supportati e le loro configurazioni')
    formats_parser.add_argument('--config', '-c', default='config/config.ini', help='File di configurazione')
    
    args = parser.parse_args()
    
    # Carica configurazione
    config_service = ConfigurationService()
    config = config_service.load_configuration(args.config if hasattr(args, 'config') else 'config/parser_config.yaml')
    
    print("🚀 CLI Parser - Sistema di Parsing Unificato")
    print("=" * 60)
    
    start_time = time.time()

    try:
        if args.command == 'sample':
            run_sampling(args.input_paths, args.output_file, args.lines, config)

        elif args.command == 'parse':
            output_dir = Path(args.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            parsing_service = ParsingService(config)
            # Passa config per permettere anonimizzazione mirata di campi in parsed_data
            reporting_service = ReportingService(output_dir, config=config)
            
            print(f"📄 Eseguendo il parsing di: {args.input_path}")
            parsed_results = parsing_service.parse_files(args.input_path)
            
            print("\n📊 Generando report completi...")
            report = reporting_service.generate_comprehensive_report(parsed_results)
            reporting_service.generate_pure_data_files(parsed_results)

            # Export opzionali
            if getattr(args, 'export_logppt', False):
                reporting_service.export_training_datasets(parsed_results)
                reporting_service.export_logppt_input_csv(parsed_results)
            if getattr(args, 'dump_drain3', False):
                reporting_service.export_drain3_dump(parsed_results)
            
            print("\n" + "="*60)
            print("🎉 PARSING COMPLETATO")
            print(f"⏱️  Tempo totale: {time.time() - start_time:.2f}s")
            print(f"📈 Record totali: {report['general_statistics']['total_records']}")
            print(f"✅ Success rate: {report['general_statistics']['success_rate']:.1f}%")
            print(f"📄 Report e dati salvati in: {output_dir.as_posix()}")
            print("="*60)

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
