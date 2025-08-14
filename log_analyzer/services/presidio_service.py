# === DESIGN COMMENT ===
# The PresidioService encapsulates all interactions with the Microsoft Presidio library.
# Its primary responsibilities are:
# 1.  Loading and interpreting the 'presidio' section of the global config.
# 2.  Correctly instantiating the AnalyzerEngine with all its recognizers.
# 3.  Correctly instantiating the AnonymizerEngine with a fully configured set of operators.
# 4.  Providing a simple, high-level interface for anonymizing text.
#
# This service-based approach decouples the web layer (or any other consumer) from the
# complexities of Presidio's configuration, adhering to the Single Responsibility Principle
# and improving the overall architecture of the application.

import logging
from typing import Dict, Any, List, Optional

from presidio_analyzer import AnalyzerEngine, RecognizerRegistry, Pattern, PatternRecognizer
from presidio_anonymizer import AnonymizerEngine, OperatorConfig

# Configure logging for the service
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PresidioService:
    """
    A service to handle all Presidio-related operations, including PII analysis and anonymization.
    """
    def __init__(self, presidio_config: Dict[str, Any]):
        """
        Initializes the PresidioService with a given configuration.

        Args:
            presidio_config: A dictionary containing the 'presidio' section of the main config.
        """
        if not presidio_config or not presidio_config.get('enabled', False):
            logger.info("Presidio service is disabled in the configuration.")
            self.analyzer = None
            self.anonymizer = None
            self.is_enabled = False
            return

        logger.info("Initializing PresidioService...")
        self.config = presidio_config
        self.is_enabled = True
        self.analyzer = self._create_analyzer()
        # The operators are not passed to the constructor, but to the anonymize method.
        # So, we create a default AnonymizerEngine and store the operators separately.
        self.operators = self._get_operators()
        self.anonymizer = AnonymizerEngine()
        logger.info("PresidioService initialized successfully.")

    def _get_operators(self) -> Optional[Dict[str, OperatorConfig]]:
        """
        # === TEACHER COMMENT ===
        # This method builds the dictionary of 'operators' that defines anonymization strategy.
        # Each key is an entity name (e.g., "PHONE_NUMBER"), and the value is an OperatorConfig
        # that defines the anonymization strategy (e.g., 'mask', 'replace', 'hash').
        # This dictionary is then passed to the `anonymize` method on each call.
        """
        try:
            anonymizer_config = self.config.get('anonymizer', {})
            strategies = anonymizer_config.get('strategies', {})
            strategy_configs = anonymizer_config.get('strategy_config', {})

            operators = {}
            # --- GUIDE COMMENT: Build OperatorConfig for each entity ---
            # Iterate through all entity->strategy mappings defined in the config.
            for entity_name, strategy_name in strategies.items():
                # Get the detailed parameters for this strategy (e.g., hash salt, mask character).
                params = strategy_configs.get(strategy_name, {})

                # Create the OperatorConfig and add it to our dictionary.
                operators[entity_name.upper()] = OperatorConfig(strategy_name, params)

            # --- GUIDE COMMENT: Handle ad-hoc recognizers ---
            # Ad-hoc recognizers might also need a specific anonymization strategy.
            ad_hoc_recognizers = self.config.get('analyzer', {}).get('ad_hoc_recognizers', [])
            for rec_conf in ad_hoc_recognizers:
                strategy_name = rec_conf.get("strategy")
                entity_name = rec_conf.get("name")
                if entity_name and strategy_name:
                    params = strategy_configs.get(strategy_name, {})
                    operators[entity_name.upper()] = OperatorConfig(strategy_name, params)

            logger.info(f"Created operators dictionary with {len(operators)} operators.")
            return operators
        except Exception as e:
            logger.error(f"Fatal error creating Presidio operators: {e}", exc_info=True)
            return None

    def _create_analyzer(self) -> Optional[AnalyzerEngine]:
        """
        # === TEACHER COMMENT ===
        # The AnalyzerEngine is the core of PII identification in Presidio. It uses a set of
        # 'recognizers' to find entities in text. Recognizers can be NLP-based (like for PERSON),
        # rule-based, or simple regex-based (PatternRecognizer).
        # This method constructs the engine by:
        # 1.  Initializing a RecognizerRegistry.
        # 2.  Loading predefined recognizers for the specified languages (e.g., 'en', 'it').
        # 3.  Adding custom ad-hoc regex patterns from the config file.
        # 4.  Passing the configured registry and other settings to the AnalyzerEngine constructor.
        """
        try:
            analyzer_config = self.config.get('analyzer', {})
            languages = analyzer_config.get('languages', ['en'])

            registry = RecognizerRegistry()
            registry.load_predefined_recognizers(languages=languages)

            # Add ad-hoc recognizers from the config
            ad_hoc_recognizers = analyzer_config.get('ad_hoc_recognizers', [])
            for rec_conf in ad_hoc_recognizers:
                if rec_conf.get("name") and rec_conf.get("regex"):
                    try:
                        pattern = Pattern(name=rec_conf['name'], regex=rec_conf['regex'], score=float(rec_conf['score']))
                        ad_hoc_recognizer = PatternRecognizer(supported_entity=rec_conf['name'], patterns=[pattern])
                        registry.add_recognizer(ad_hoc_recognizer)
                        logger.info(f"Successfully added ad-hoc recognizer '{rec_conf['name']}'.")
                    except Exception as e:
                        logger.error(f"Failed to add ad-hoc recognizer '{rec_conf.get('name')}': {e}")

            # Extracting other potential AnalyzerEngine parameters from config
            confidence_threshold = analyzer_config.get('analysis', {}).get('confidence_threshold')

            return AnalyzerEngine(
                registry=registry,
                supported_languages=languages,
                default_score_threshold=confidence_threshold
            )
        except Exception as e:
            logger.error(f"Fatal error creating Presidio AnalyzerEngine: {e}", exc_info=True)
            return None

    def anonymize_text(self, text: str, **kwargs) -> str:
        """
        Anonymizes a given text string using the configured Presidio engines.

        Args:
            text: The input string to anonymize.
            **kwargs: Additional parameters to pass to the analyzer's analyze method.

        Returns:
            The anonymized text. Returns the original text if the service is disabled.
        """
        if not self.is_enabled or not self.analyzer or not self.anonymizer:
            return text

        try:
            analyzer_results = self.analyzer.analyze(text=text, **kwargs)

            # The 'operators' dictionary is passed to the anonymize method directly.
            anonymized_result = self.anonymizer.anonymize(
                text=text,
                analyzer_results=analyzer_results,
                operators=self.operators
            )
            return anonymized_result.text
        except Exception as e:
            logger.error(f"Error during anonymization: {e}", exc_info=True)
            # Return original text as a safe fallback
            return text
