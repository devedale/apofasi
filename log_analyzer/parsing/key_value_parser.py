import re
from typing import Optional, Dict, Any

from .interfaces import AbstractParser, LogEntry, ParsedRecord

class KeyValueParser(AbstractParser):
    """
    A concrete parser for generic key-value log formats.
    It can be configured with different delimiters.
    Example: key1=value1 key2="value with spaces"
    """
    def __init__(self, delimiter: str = '=', min_pairs: int = 3):
        """
        Initializes the parser.

        Args:
            delimiter: The character separating keys and values.
            min_pairs: The minimum number of key-value pairs required to
                       consider the line a match for this parser.
        """
        self.delimiter = delimiter
        self.min_pairs = min_pairs
        # Regex to find key-value pairs. It handles quoted values.
        # It looks for a key (word), the delimiter, and then either a
        # quoted string or a non-quoted string until the next space.
        self.kv_regex = re.compile(
            rf'(\w+){re.escape(self.delimiter)}(?:"([^"]*)"|(\S+))'
        )

    def handle(self, log_entry: LogEntry) -> Optional[ParsedRecord]:
        """
        Tries to parse the log entry as a key-value formatted string.

        Args:
            log_entry: The log entry to parse.

        Returns:
            A ParsedRecord if enough key-value pairs are found, otherwise
            the result from the next handler in the chain.
        """
        matches = self.kv_regex.findall(log_entry.content)

        if len(matches) >= self.min_pairs:
            parsed_data = {}
            for key, quoted_val, unquoted_val in matches:
                # The regex captures one of the two value groups.
                # If quoted_val is not empty, that's our value.
                value = quoted_val if quoted_val else unquoted_val
                parsed_data[key] = value

            return ParsedRecord(
                original_content=log_entry.content,
                line_number=log_entry.line_number,
                source_file=log_entry.source_file,
                parser_name='KeyValueParser',
                parsed_data=parsed_data
            )

        # If not enough pairs were found, pass to the next handler
        return super().handle(log_entry)
