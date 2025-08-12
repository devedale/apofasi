from PyQt6.QtCore import QAbstractTableModel, Qt
from typing import List, Any, Optional

class ResultsTableModel(QAbstractTableModel):
    """
    A Qt Table Model to display ParsedRecord data in a QTableView.
    """
    def __init__(self, data: Optional[List[dict]] = None):
        super().__init__()
        self._data = data or []
        # The header is dynamic, so we determine it from the data
        self._header = self._determine_header()

    def _determine_header(self) -> List[str]:
        """Determines the table header from the keys of the data dictionaries."""
        if not self._data:
            return []
        # Use a union of all keys from all records to create a comprehensive header
        header_set = set()
        for row_data in self._data:
            header_set.update(row_data.keys())

        # Give it a consistent order, but maybe prioritize some columns
        sorted_header = sorted(list(header_set))
        priority_cols = ['line_number', 'parser_name', 'original_content']
        for col in reversed(priority_cols):
            if col in sorted_header:
                sorted_header.remove(col)
                sorted_header.insert(0, col)
        return sorted_header

    def update_data(self, data: List[dict]):
        """Updates the model with new data."""
        self.beginResetModel()
        self._data = data
        self._header = self._determine_header()
        self.endResetModel()

    def rowCount(self, parent=None) -> int:
        return len(self._data)

    def columnCount(self, parent=None) -> int:
        return len(self._header)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or role != Qt.ItemDataRole.DisplayRole:
            return None

        row = index.row()
        col_name = self._header[index.column()]

        # Get the value from the dictionary for the corresponding row and column
        value = self._data[row].get(col_name)

        # Pretty print dicts/lists for display
        if isinstance(value, (dict, list)):
            return str(value)

        return value

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self._header[section].replace('_', ' ').title()
        return None
