from PyQt6.QtCore import QAbstractTableModel, Qt, QModelIndex


class ResultTableModel(QAbstractTableModel):
    def __init__(self, columns=None, rows=None, parent=None):
        super().__init__(parent)
        self._columns = list(columns or [])
        self._rows = [list(r) for r in (rows or [])]

    def set_data(self, columns, rows):
        self.beginResetModel()
        self._columns = list(columns)
        self._rows = [list(r) for r in rows]
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._columns)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            value = self._rows[index.row()][index.column()]
            return "NULL" if value is None else str(value)
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return self._columns[section] if 0 <= section < len(self._columns) else None
        return section + 1
