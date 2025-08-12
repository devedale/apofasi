import re
from typing import Optional, Dict, Any

from .interfaces import AbstractParser, LogEntry, ParsedRecord

class CEFParser(AbstractParser):
    """
    A concrete parser for the Common Event Format (CEF).
    It parses the CEF header and the key-value extension field.
    """
    # Regex to capture the CEF header fields
    header_regex = re.compile(
        r"CEF:(?P<version>\d+)\|(?P<device_vendor>[^|]*)\|(?P<device_product>[^|]*)\|"
        r"(?P<device_version>[^|]*)\|(?P<signature_id>[^|]*)\|(?P<name>[^|]*)\|"
        r"(?P<severity>[^|]*)\|(?P<extension>.*)"
    )

    def handle(self, log_entry: LogEntry) -> Optional[ParsedRecord]:
        """
        Tries to parse the log entry as a CEF record.

        Args:
            log_entry: The log entry to parse.

        Returns:
            A ParsedRecord if the content is valid CEF, otherwise the result
            from the next handler in the chain.
        """
        match = self.header_regex.match(log_entry.content)

        if not match:
            return super().handle(log_entry)

        # Header fields were successfully parsed
        parsed_data = match.groupdict()
        extension_string = parsed_data.pop("extension", "")

        # Parse the key-value pairs in the extension field
        if extension_string:
            try:
                extension_data = self._parse_extension(extension_string)
                parsed_data.update(extension_data)
            except Exception as e:
                parsed_data['extension_parsing_error'] = str(e)

        return ParsedRecord(
            original_content=log_entry.content,
            line_number=log_entry.line_number,
            source_file=log_entry.source_file,
            parser_name='CEFParser',
            parsed_data=parsed_data
        )

    def _parse_extension(self, extension_string: str) -> Dict[str, Any]:
        """
        Parses the extension part of a CEF message.
        This is a best-effort parser for space-separated key=value pairs.
        It handles values with spaces by looking ahead for the next key.
        """
        data = {}
        # Find all potential keys (a word followed by an equals sign)
        keys = re.findall(r"(\w+)=", extension_string)

        if not keys:
            # If no key=value structure is found, return the raw string
            data['raw_extension'] = extension_string
            return data

        # Split the string by the key pattern, which gives us the values
        # The regex uses a positive lookahead `(?=...)` to split without consuming the delimiter
        values = re.split(r"\s+(?=\w+=)", extension_string)

        for i, value_part in enumerate(values):
            # The first part of the split value is the key=value
            parts = value_part.split('=', 1)
            if len(parts) == 2:
                key, val = parts
                data[key.strip()] = val.strip()

        return data
