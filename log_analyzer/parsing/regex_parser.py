import re
from typing import Optional, Pattern

from .interfaces import AbstractParser, LogEntry, ParsedRecord

class RegexParser(AbstractParser):
    """
    A concrete parser that uses a regular expression to parse log entries.
    The regex should use named capture groups to extract structured data.
    """
    def __init__(self, pattern: Pattern[str], parser_name: str = 'RegexParser'):
        """
        Initializes the parser with a compiled regex pattern.

        Args:
            pattern: A compiled regular expression object with named capture groups.
            parser_name: The name to identify this specific regex parser.
        """
        self.pattern = pattern
        self.parser_name = parser_name

    def handle(self, log_entry: LogEntry) -> Optional[ParsedRecord]:
        """
        Tries to match the regex pattern against the log entry content.

        Args:
            log_entry: The log entry to parse.

        Returns:
            A ParsedRecord if the regex matches, otherwise the result from the
            next handler in the chain.
        """
        match = self.pattern.match(log_entry.content)

        if match:
            # If the regex matches, use the named capture groups as the parsed data
            parsed_data = match.groupdict()
            return ParsedRecord(
                original_content=log_entry.content,
                line_number=log_entry.line_number,
                source_file=log_entry.source_file,
                parser_name=self.parser_name,
                parsed_data=parsed_data
            )

        # If no match, pass the request to the next handler
        return super().handle(log_entry)
