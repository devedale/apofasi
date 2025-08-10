"""
Cache Service - Servizio di caching centralizzato

Questo modulo fornisce un servizio di caching per ottimizzare le performance
dell'applicazione, con supporto per cache in memoria e su disco.

DESIGN:
- Cache in memoria con TTL configurabile
- Supporto per cache su disco
- Eviction policies configurabili
- Integrazione con metriche di performance

Author: Edoardo D'Alesio
Version: 1.0.0
"""

import time
import json
import pickle
import threading
from pathlib import Path
from typing import Dict, Any, Optional, Union, Callable
from datetime import datetime, timedelta
from collections import OrderedDict

from ..constants import MAX_CACHE_SIZE, DEFAULT_CACHE_TTL, MAX_CACHE_ENTRIES
from ..enums import CacheStrategy


class CacheEntry:
    """
    Entry della cache con metadati.
    
    WHY: Classe per gestire metadati delle entry della cache
    come TTL, timestamp di creazione e statistiche di accesso.
    """
    
    def __init__(self, key: str, value: Any, ttl: int = DEFAULT_CACHE_TTL):
        """
        Inizializza una entry della cache.
        
        Args:
            key: Chiave della entry
            value: Valore da memorizzare
            ttl: Time-to-live in secondi
        """
        self.key = key
        self.value = value
        self.ttl = ttl
        self.created_at = datetime.now()
        self.last_accessed = datetime.now()
        self.access_count = 0
    
    def is_expired(self) -> bool:
        """Controlla se la entry è scaduta."""
        return datetime.now() > self.created_at + timedelta(seconds=self.ttl)
    
    def access(self):
        """Registra un accesso alla entry."""
        self.last_accessed = datetime.now()
        self.access_count += 1
    
    def get_age(self) -> float:
        """Restituisce l'età della entry in secondi."""
        return (datetime.now() - self.created_at).total_seconds()


class CacheService:
    """
    Servizio di caching centralizzato per l'applicazione.
    
    WHY: Servizio centralizzato per ottimizzare le performance
    riducendo calcoli ripetuti e accessi a risorse costose.
    
    Contract:
        - Cache in memoria con TTL configurabile
        - Supporto per cache su disco
        - Eviction policies configurabili
        - Integrazione con metriche
    """
    
    def __init__(self, 
                 strategy: CacheStrategy = CacheStrategy.MEMORY,
                 max_size: int = MAX_CACHE_SIZE,
                 max_entries: int = MAX_CACHE_ENTRIES,
                 default_ttl: int = DEFAULT_CACHE_TTL,
                 cache_dir: Optional[Path] = None):
        """
        Inizializza il servizio di cache.
        
        Args:
            strategy: Strategia di cache da utilizzare
            max_size: Dimensione massima cache in bytes
            max_entries: Numero massimo di entry
            default_ttl: TTL di default in secondi
            cache_dir: Directory per cache su disco (opzionale)
        """
        self.strategy = strategy
        self.max_size = max_size
        self.max_entries = max_entries
        self.default_ttl = default_ttl
        self.cache_dir = cache_dir
        
        # Cache in memoria
        self.memory_cache = OrderedDict()
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'size_bytes': 0
        }
        
        # Lock per thread safety
        self._lock = threading.Lock()
        
        # Setup cache su disco se richiesto
        if self.strategy.uses_disk() and cache_dir:
            self._setup_disk_cache()
    
    def _setup_disk_cache(self):
        """Configura la cache su disco."""
        if not self.cache_dir:
            return
        
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.disk_cache_index = self.cache_dir / "index.json"
        
        # Carica indice esistente
        if self.disk_cache_index.exists():
            try:
                with open(self.disk_cache_index, 'r') as f:
                    self.disk_index = json.load(f)
            except Exception:
                self.disk_index = {}
        else:
            self.disk_index = {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Recupera un valore dalla cache.
        
        WHY: Metodo principale per accedere ai dati cached
        con gestione automatica di TTL e statistiche.
        
        Args:
            key: Chiave da recuperare
            default: Valore di default se non trovato
            
        Returns:
            Valore cached o default
        """
        with self._lock:
            # Prova cache in memoria
            if key in self.memory_cache:
                entry = self.memory_cache[key]
                
                if entry.is_expired():
                    # Rimuovi entry scaduta
                    del self.memory_cache[key]
                    self.cache_stats['misses'] += 1
                    return default
                
                # Entry valida
                entry.access()
                self.cache_stats['hits'] += 1
                
                # Sposta in fondo (LRU)
                self.memory_cache.move_to_end(key)
                return entry.value
            
            # Prova cache su disco
            if self.strategy.uses_disk() and key in self.disk_index:
                try:
                    disk_entry = self._load_from_disk(key)
                    if disk_entry and not disk_entry.is_expired():
                        # Sposta in memoria
                        self._add_to_memory(key, disk_entry.value, disk_entry.ttl)
                        self.cache_stats['hits'] += 1
                        return disk_entry.value
                except Exception:
                    pass
            
            self.cache_stats['misses'] += 1
            return default
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Memorizza un valore nella cache.
        
        WHY: Metodo per memorizzare dati nella cache
        con gestione automatica di dimensione e eviction.
        
        Args:
            key: Chiave per il valore
            value: Valore da memorizzare
            ttl: Time-to-live in secondi (opzionale)
            
        Returns:
            True se memorizzato con successo
        """
        if ttl is None:
            ttl = self.default_ttl
        
        with self._lock:
            # Rimuovi entry esistente se presente
            if key in self.memory_cache:
                del self.memory_cache[key]
            
            # Aggiungi nuova entry
            return self._add_to_memory(key, value, ttl)
    
    def _add_to_memory(self, key: str, value: Any, ttl: int) -> bool:
        """Aggiunge una entry alla cache in memoria."""
        try:
            # Crea entry
            entry = CacheEntry(key, value, ttl)
            
            # Controlla dimensione
            entry_size = self._estimate_size(entry)
            if self.cache_stats['size_bytes'] + entry_size > self.max_size:
                self._evict_entries(entry_size)
            
            # Controlla numero di entry
            if len(self.memory_cache) >= self.max_entries:
                self._evict_entries(0)
            
            # Aggiungi entry
            self.memory_cache[key] = entry
            self.cache_stats['size_bytes'] += entry_size
            
            # Salva su disco se richiesto
            if self.strategy.uses_disk():
                self._save_to_disk(key, entry)
            
            return True
            
        except Exception as e:
            print(f"Errore aggiunta entry cache: {e}")
            return False
    
    def _estimate_size(self, entry: CacheEntry) -> int:
        """Stima la dimensione di una entry in bytes."""
        try:
            # Stima approssimativa
            key_size = len(entry.key.encode('utf-8'))
            value_size = len(str(entry.value).encode('utf-8'))
            return key_size + value_size + 100  # Overhead approssimativo
        except Exception:
            return 1024  # Stima conservativa
    
    def _evict_entries(self, required_space: int):
        """Rimuove entry dalla cache per fare spazio."""
        while (self.cache_stats['size_bytes'] + required_space > self.max_size or 
               len(self.memory_cache) >= self.max_entries):
            
            if not self.memory_cache:
                break
            
            # Rimuovi entry più vecchia (LRU)
            oldest_key = next(iter(self.memory_cache))
            oldest_entry = self.memory_cache[oldest_key]
            
            del self.memory_cache[oldest_key]
            self.cache_stats['size_bytes'] -= self._estimate_size(oldest_entry)
            self.cache_stats['evictions'] += 1
    
    def _save_to_disk(self, key: str, entry: CacheEntry):
        """Salva una entry su disco."""
        if not self.cache_dir:
            return
        
        try:
            # Salva dati
            file_path = self.cache_dir / f"{key}.cache"
            with open(file_path, 'wb') as f:
                pickle.dump(entry, f)
            
            # Aggiorna indice
            self.disk_index[key] = {
                'file_path': str(file_path),
                'created_at': entry.created_at.isoformat(),
                'ttl': entry.ttl
            }
            
            with open(self.disk_cache_index, 'w') as f:
                json.dump(self.disk_index, f)
                
        except Exception as e:
            print(f"Errore salvataggio su disco: {e}")
    
    def _load_from_disk(self, key: str) -> Optional[CacheEntry]:
        """Carica una entry da disco."""
        if not self.cache_dir or key not in self.disk_index:
            return None
        
        try:
            file_path = Path(self.disk_index[key]['file_path'])
            if not file_path.exists():
                return None
            
            with open(file_path, 'rb') as f:
                return pickle.load(f)
                
        except Exception as e:
            print(f"Errore caricamento da disco: {e}")
            return None
    
    def delete(self, key: str) -> bool:
        """
        Rimuove una entry dalla cache.
        
        Args:
            key: Chiave da rimuovere
            
        Returns:
            True se rimossa con successo
        """
        with self._lock:
            # Rimuovi da memoria
            if key in self.memory_cache:
                entry = self.memory_cache[key]
                del self.memory_cache[key]
                self.cache_stats['size_bytes'] -= self._estimate_size(entry)
            
            # Rimuovi da disco
            if self.strategy.uses_disk() and key in self.disk_index:
                try:
                    file_path = Path(self.disk_index[key]['file_path'])
                    if file_path.exists():
                        file_path.unlink()
                    
                    del self.disk_index[key]
                    
                    with open(self.disk_cache_index, 'w') as f:
                        json.dump(self.disk_index, f)
                        
                except Exception as e:
                    print(f"Errore rimozione da disco: {e}")
            
            return True
    
    def clear(self):
        """Svuota completamente la cache."""
        with self._lock:
            self.memory_cache.clear()
            self.cache_stats['size_bytes'] = 0
            
            if self.strategy.uses_disk():
                # Rimuovi tutti i file di cache
                if self.cache_dir and self.cache_dir.exists():
                    for file_path in self.cache_dir.glob("*.cache"):
                        try:
                            file_path.unlink()
                        except Exception:
                            pass
                
                self.disk_index.clear()
                if self.disk_cache_index.exists():
                    with open(self.disk_cache_index, 'w') as f:
                        json.dump({}, f)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Restituisce statistiche della cache.
        
        WHY: Metodo per monitoring e debugging
        delle performance della cache.
        
        Returns:
            Dizionario con statistiche della cache
        """
        with self._lock:
            hit_rate = 0.0
            total_requests = self.cache_stats['hits'] + self.cache_stats['misses']
            if total_requests > 0:
                hit_rate = (self.cache_stats['hits'] / total_requests) * 100
            
            return {
                'strategy': self.strategy.value,
                'max_size_bytes': self.max_size,
                'current_size_bytes': self.cache_stats['size_bytes'],
                'max_entries': self.max_entries,
                'current_entries': len(self.memory_cache),
                'hits': self.cache_stats['hits'],
                'misses': self.cache_stats['misses'],
                'evictions': self.cache_stats['evictions'],
                'hit_rate_percent': hit_rate,
                'disk_entries': len(self.disk_index) if self.strategy.uses_disk() else 0
            }
    
    def cleanup_expired(self):
        """Rimuove tutte le entry scadute."""
        with self._lock:
            expired_keys = []
            
            for key, entry in self.memory_cache.items():
                if entry.is_expired():
                    expired_keys.append(key)
            
            for key in expired_keys:
                entry = self.memory_cache[key]
                del self.memory_cache[key]
                self.cache_stats['size_bytes'] -= self._estimate_size(entry)
    
    def __contains__(self, key: str) -> bool:
        """Controlla se una chiave è presente nella cache."""
        return self.get(key) is not None 