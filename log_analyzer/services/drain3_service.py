from typing import Dict, Any, List, Tuple

from drain3 import TemplateMiner
from drain3.template_miner_config import TemplateMinerConfig

class Drain3Service:
    """
    A service for template mining using Drain3.
    This service manages two separate template miners: one for original content
    and one for anonymized content, as required by the pipeline.
    """
    def __init__(self, config: Dict[str, Any]):
        """
        Initializes the Drain3Service.

        Args:
            config: The application configuration, which should contain a
                    'drain3' section.
        """
        self.config = config.get('drain3', {})

        # Create a template miner for original content
        self.original_miner = self._create_miner('original')

        # Create a template miner for anonymized content
        self.anonymized_miner = self._create_miner('anonymized')

    def _create_miner(self, miner_type: str) -> TemplateMiner:
        """
        Creates and configures a Drain3 TemplateMiner instance.

        Args:
            miner_type: The type of miner to create ('original' or 'anonymized').
                        This is used to get the correct section from the config.

        Returns:
            A configured TemplateMiner instance.
        """
        miner_config = self.config.get(miner_type, {})

        # Fallback to common settings if type-specific ones aren't present
        config = TemplateMinerConfig()
        config.drain_similarity_threshold = miner_config.get('similarity_threshold', self.config.get('similarity_threshold', 0.4))
        config.drain_depth = miner_config.get('depth', self.config.get('depth', 4))
        config.drain_max_children = miner_config.get('max_children', self.config.get('max_children', 1000))
        # Set other Drain3 parameters from config as needed

        return TemplateMiner(config=config)

    def process_batch(self, messages: List[str], miner_type: str) -> List[Dict[str, Any]]:
        """
        Processes a batch of log messages with the specified miner.

        Args:
            messages: A list of log message strings to process.
            miner_type: The type of miner to use ('original' or 'anonymized').

        Returns:
            A list of dictionaries, each containing the result for a message
            (e.g., cluster_id, template).
        """
        if miner_type == 'original':
            miner = self.original_miner
        elif miner_type == 'anonymized':
            miner = self.anonymized_miner
        else:
            raise ValueError(f"Invalid miner_type specified: {miner_type}")

        results = []
        for message in messages:
            try:
                result = miner.add_log_message(message)
                results.append({
                    'cluster_id': result['cluster_id'],
                    'template': result['template_mined'],
                    'change_type': result['change_type'],
                })
            except Exception as e:
                print(f"Error processing message with Drain3 ({miner_type}): {e}")
                results.append({'error': str(e)})

        return results
