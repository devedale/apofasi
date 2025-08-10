"""
Metrics Service - Servizio per metriche e monitoring

Questo modulo fornisce un servizio per la raccolta e gestione di metriche
di performance, utilizzo risorse e statistiche dell'applicazione.

DESIGN:
- Raccolta automatica di metriche di sistema
- Supporto per metriche custom
- Aggregazione e reporting delle metriche
- Integrazione con sistemi di monitoring esterni

Author: Edoardo D'Alesio
Version: 1.0.0
"""

import time
import psutil
import threading
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from collections import defaultdict, deque

from ..constants import PERFORMANCE_METRICS, METRICS_UPDATE_INTERVAL
from ..enums import ProcessingStatus


class MetricsService:
    """
    Servizio per la raccolta e gestione di metriche dell'applicazione.
    
    WHY: Servizio centralizzato per monitoring e ottimizzazione
    delle performance dell'applicazione.
    
    Contract:
        - Raccolta automatica di metriche di sistema
        - Supporto per metriche custom
        - Aggregazione e reporting
        - Integrazione con monitoring esterni
    """
    
    def __init__(self, auto_collect: bool = True, update_interval: float = METRICS_UPDATE_INTERVAL):
        """
        Inizializza il servizio di metriche.
        
        Args:
            auto_collect: Se True, raccoglie automaticamente metriche di sistema
            update_interval: Intervallo di aggiornamento in secondi
        """
        self.auto_collect = auto_collect
        self.update_interval = update_interval
        self.metrics = defaultdict(deque)
        self.custom_metrics = {}
        self.collectors = {}
        self.running = False
        self._lock = threading.Lock()
        
        # Metriche di sistema
        self.system_metrics = {
            'cpu_percent': 0.0,
            'memory_percent': 0.0,
            'memory_available': 0,
            'disk_usage_percent': 0.0,
            'network_io': {'bytes_sent': 0, 'bytes_recv': 0}
        }
        
        # Metriche dell'applicazione
        self.app_metrics = {
            'files_processed': 0,
            'records_processed': 0,
            'errors_count': 0,
            'warnings_count': 0,
            'processing_time_total': 0.0,
            'active_operations': 0
        }
        
        if auto_collect:
            self.start_collection()
    
    def start_collection(self):
        """Avvia la raccolta automatica di metriche."""
        if self.running:
            return
        
        self.running = True
        self._collection_thread = threading.Thread(target=self._collect_metrics, daemon=True)
        self._collection_thread.start()
    
    def stop_collection(self):
        """Ferma la raccolta automatica di metriche."""
        self.running = False
        if hasattr(self, '_collection_thread'):
            self._collection_thread.join(timeout=1.0)
    
    def _collect_metrics(self):
        """Raccoglie metriche di sistema in background."""
        while self.running:
            try:
                with self._lock:
                    # Metriche CPU
                    self.system_metrics['cpu_percent'] = psutil.cpu_percent(interval=1)
                    
                    # Metriche memoria
                    memory = psutil.virtual_memory()
                    self.system_metrics['memory_percent'] = memory.percent
                    self.system_metrics['memory_available'] = memory.available
                    
                    # Metriche disco
                    disk = psutil.disk_usage('/')
                    self.system_metrics['disk_usage_percent'] = disk.percent
                    
                    # Metriche rete
                    network = psutil.net_io_counters()
                    self.system_metrics['network_io'] = {
                        'bytes_sent': network.bytes_sent,
                        'bytes_recv': network.bytes_recv
                    }
                
                # Salva metriche con timestamp
                timestamp = datetime.now()
                self._save_metric('system', self.system_metrics, timestamp)
                
                time.sleep(self.update_interval)
                
            except Exception as e:
                # Log dell'errore ma continua la raccolta
                print(f"Errore raccolta metriche: {e}")
                time.sleep(self.update_interval)
    
    def _save_metric(self, category: str, data: Dict[str, Any], timestamp: datetime):
        """Salva una metrica con timestamp."""
        metric_entry = {
            'timestamp': timestamp,
            'data': data.copy()
        }
        
        with self._lock:
            self.metrics[category].append(metric_entry)
            
            # Mantieni solo le ultime 1000 metriche per categoria
            if len(self.metrics[category]) > 1000:
                self.metrics[category].popleft()
    
    def record_operation(self, operation: str, duration: float, success: bool = True, **kwargs):
        """
        Registra un'operazione completata.
        
        WHY: Metodo per tracciare performance delle operazioni
        e identificare bottleneck nell'applicazione.
        
        Args:
            operation: Nome dell'operazione
            duration: Durata in secondi
            success: Se l'operazione è stata completata con successo
            **kwargs: Parametri aggiuntivi dell'operazione
        """
        with self._lock:
            self.app_metrics['processing_time_total'] += duration
            self.app_metrics['records_processed'] += kwargs.get('records_processed', 0)
            self.app_metrics['files_processed'] += kwargs.get('files_processed', 0)
            
            if not success:
                self.app_metrics['errors_count'] += 1
            elif kwargs.get('warnings', 0) > 0:
                self.app_metrics['warnings_count'] += kwargs.get('warnings', 0)
        
        # Salva metrica dell'operazione
        operation_metric = {
            'operation': operation,
            'duration': duration,
            'success': success,
            **kwargs
        }
        
        self._save_metric('operations', operation_metric, datetime.now())
    
    def increment_counter(self, counter_name: str, value: int = 1):
        """
        Incrementa un contatore.
        
        WHY: Metodo per tracciare eventi e statistiche
        dell'applicazione in tempo reale.
        
        Args:
            counter_name: Nome del contatore
            value: Valore da incrementare
        """
        with self._lock:
            if counter_name not in self.app_metrics:
                self.app_metrics[counter_name] = 0
            self.app_metrics[counter_name] += value
    
    def set_gauge(self, gauge_name: str, value: float):
        """
        Imposta il valore di un gauge.
        
        WHY: Metodo per tracciare valori istantanei
        come numero di operazioni attive.
        
        Args:
            gauge_name: Nome del gauge
            value: Valore da impostare
        """
        with self._lock:
            self.app_metrics[gauge_name] = value
    
    def add_custom_metric(self, name: str, collector: Callable[[], Any]):
        """
        Aggiunge una metrica custom con collector.
        
        WHY: Permette di aggiungere metriche specifiche
        per diversi componenti dell'applicazione.
        
        Args:
            name: Nome della metrica
            collector: Funzione che restituisce il valore della metrica
        """
        self.custom_metrics[name] = collector
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """
        Restituisce le metriche correnti.
        
        WHY: Metodo per ottenere snapshot delle metriche
        per monitoring e reporting.
        
        Returns:
            Dizionario con tutte le metriche correnti
        """
        with self._lock:
            # Raccogli metriche custom
            custom_data = {}
            for name, collector in self.custom_metrics.items():
                try:
                    custom_data[name] = collector()
                except Exception as e:
                    custom_data[name] = f"Error: {e}"
            
            return {
                'timestamp': datetime.now().isoformat(),
                'system': self.system_metrics.copy(),
                'application': self.app_metrics.copy(),
                'custom': custom_data
            }
    
    def get_metrics_history(self, category: str, minutes: int = 60) -> List[Dict[str, Any]]:
        """
        Restituisce lo storico delle metriche.
        
        WHY: Metodo per analisi delle tendenze
        e identificazione di pattern nelle performance.
        
        Args:
            category: Categoria delle metriche
            minutes: Minuti di storico da restituire
            
        Returns:
            Lista delle metriche storiche
        """
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        with self._lock:
            if category not in self.metrics:
                return []
            
            return [
                {
                    'timestamp': entry['timestamp'].isoformat(),
                    'data': entry['data']
                }
                for entry in self.metrics[category]
                if entry['timestamp'] >= cutoff_time
            ]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Restituisce un riepilogo delle performance.
        
        WHY: Metodo per reporting e dashboard
        con metriche aggregate e statistiche.
        
        Returns:
            Dizionario con riepilogo performance
        """
        current_metrics = self.get_current_metrics()
        
        # Calcola statistiche
        total_operations = current_metrics['application'].get('files_processed', 0)
        total_time = current_metrics['application'].get('processing_time_total', 0.0)
        avg_time = total_time / total_operations if total_operations > 0 else 0.0
        
        error_rate = 0.0
        if total_operations > 0:
            errors = current_metrics['application'].get('errors_count', 0)
            error_rate = (errors / total_operations) * 100
        
        return {
            'summary_timestamp': datetime.now().isoformat(),
            'total_operations': total_operations,
            'total_processing_time': total_time,
            'average_operation_time': avg_time,
            'error_rate_percent': error_rate,
            'current_cpu_percent': current_metrics['system'].get('cpu_percent', 0.0),
            'current_memory_percent': current_metrics['system'].get('memory_percent', 0.0),
            'active_operations': current_metrics['application'].get('active_operations', 0)
        }
    
    def reset_metrics(self):
        """Resetta tutte le metriche."""
        with self._lock:
            self.metrics.clear()
            self.app_metrics = {
                'files_processed': 0,
                'records_processed': 0,
                'errors_count': 0,
                'warnings_count': 0,
                'processing_time_total': 0.0,
                'active_operations': 0
            }
    
    def __del__(self):
        """Cleanup quando l'oggetto viene distrutto."""
        self.stop_collection() 