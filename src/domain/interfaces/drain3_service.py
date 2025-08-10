"""Drain3 service interface."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Iterator, Optional

from ..entities.parsed_record import ParsedRecord


class Drain3Service(ABC):
    """Abstract interface for Drain3 template mining service with dual mining support."""
    
    @abstractmethod
    def add_log_message(self, log_message: str, miner_type: str = "original") -> int:
        """
        Add a log message to Drain3 for template mining.
        
        Args:
            log_message: The log message to add
            miner_type: "original" or "anonymized" to specify which miner to use
            
        Returns:
            Cluster ID assigned to the message
        """
        pass
    
    @abstractmethod
    def get_template(self, cluster_id: int, miner_type: str = "original") -> Optional[str]:
        """
        Get the template for a specific cluster.
        
        Args:
            cluster_id: The cluster ID
            miner_type: "original" or "anonymized" to specify which miner to use
            
        Returns:
            Template string or None if not found
        """
        pass
    
    @abstractmethod
    def get_cluster_info(self, cluster_id: int, miner_type: str = "original") -> Optional[Dict[str, Any]]:
        """
        Get information about a specific cluster.
        
        Args:
            cluster_id: The cluster ID
            miner_type: "original" or "anonymized" to specify which miner to use
            
        Returns:
            Cluster information dictionary or None if not found
        """
        pass
    
    @abstractmethod
    def get_all_templates(self, miner_type: str = "original") -> Dict[int, str]:
        """
        Get all templates discovered by Drain3.
        
        Args:
            miner_type: "original" or "anonymized" to specify which miner to use
            
        Returns:
            Dictionary mapping cluster IDs to templates
        """
        pass
    
    @abstractmethod
    def get_all_templates_combined(self) -> Dict[str, Dict[int, str]]:
        """
        Get all templates from both miners combined.
        
        Returns:
            Dictionary with "original" and "anonymized" keys, each containing cluster ID to template mappings
        """
        pass
    
    @abstractmethod
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get Drain3 statistics for both miners.
        
        Returns:
            Statistics dictionary with combined information
        """
        pass
    
    @abstractmethod
    def save_state(self, file_path: str) -> None:
        """
        Save Drain3 state to file for both miners.
        
        Args:
            file_path: Path to save state
        """
        pass
    
    @abstractmethod
    def load_state(self, file_path: str) -> None:
        """
        Load Drain3 state from file for both miners.
        
        Args:
            file_path: Path to load state from
        """
        pass
    
    @abstractmethod
    def process_record(self, record: ParsedRecord) -> ParsedRecord:
        """
        Process a parsed record with Drain3 using both miners.
        
        Args:
            record: The record to process
            
        Returns:
            Updated record with Drain3 information from both miners
        """
        pass 