import re
from typing import Dict, Any, Optional

from .interfaces import AbstractParser, LogEntry, ParsedRecord
from .json_parser import JSONParser
from .csv_parser import CSVParser
from .cef_parser import CEFParser
from .key_value_parser import KeyValueParser
from .regex_parser import RegexParser

def create_parser_chain(config: Dict[str, Any]) -> Optional[AbstractParser]:
    """
    Creates and links a chain of parsers based on the application configuration.

    The order of the chain is hardcoded for now but could be made
    configurable in the future. The typical order is to try the most
    specific and unambiguous parsers first (JSON), followed by more
    general ones (CSV), and finally pattern-based ones (Regex).

    Args:
        config: The application configuration dictionary, which should
                contain settings for the parsers.

    Returns:
        The first parser (head) in the configured chain of responsibility,
        or None if no parsers are enabled.
    """
    head: Optional[AbstractParser] = None
    current: Optional[AbstractParser] = None

    # 1. JSON Parser
    # The JSON parser is usually first as it's very specific.
    if config.get('parsers', {}).get('json', {}).get('enabled', True):
        json_parser = JSONParser()
        if not head:
            head = json_parser
        if current:
            current.set_next(json_parser)
        current = json_parser

    # 2. Key-Value Parser (moved before CSV for Fortinet logs)
    # The Key-Value parser should come before CSV for log formats like Fortinet
    kv_config = config.get('parsers', {}).get('key_value', {})
    if kv_config.get('enabled', True):
        kv_parser = KeyValueParser(
            delimiter=kv_config.get('delimiter', '='),
            min_pairs=kv_config.get('min_pairs', 3)
        )
        if not head:
            head = kv_parser
        if current:
            current.set_next(kv_parser)
        current = kv_parser

    # 3. CSV Parser
    # The CSV parser comes after Key-Value for log formats
    csv_config = config.get('parsers', {}).get('csv', {})
    if csv_config.get('enabled', True):
        csv_parser = CSVParser(
            delimiter=csv_config.get('delimiter', ','),
            header=csv_config.get('header', None),
            config=config  # Pass full config for header detection
        )
        if not head:
            head = csv_parser
        if current:
            current.set_next(csv_parser)
        current = csv_parser

    # 4. CEF Parser
    cef_config = config.get('parsers', {}).get('cef', {})
    if cef_config.get('enabled', True):
        cef_parser = CEFParser()
        if not head:
            head = cef_parser
        if current:
            current.set_next(cef_parser)
        current = cef_parser

    # 5. Regex Parsers
    # We can add multiple regex parsers from the config.
    regex_configs = config.get('centralized_regex', {}).get('parsing', {})
    for name, pattern_str in regex_configs.items():
        try:
            pattern = re.compile(pattern_str)
            regex_parser = RegexParser(pattern=pattern, parser_name=name)
            if not head:
                head = regex_parser
            if current:
                current.set_next(regex_parser)
            current = regex_parser
        except re.error as e:
            print(f"Warning: Could not compile regex pattern '{name}': {e}")

    # Add a final fallback parser that does nothing but create a basic record
    # This ensures that no log entry is ever truly "lost".
    class FallbackParser(AbstractParser):
        def handle(self, log_entry: LogEntry) -> Optional[ParsedRecord]:
            return ParsedRecord(
                original_content=log_entry.content,
                line_number=log_entry.line_number,
                source_file=log_entry.source_file,
                parser_name='FallbackParser',
                parsed_data={'raw_content': log_entry.content}
            )

    fallback_parser = FallbackParser()
    if not head:
        head = fallback_parser
    if current:
        current.set_next(fallback_parser)

    return head
