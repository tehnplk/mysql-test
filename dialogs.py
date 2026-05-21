from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QStyle,
    QVBoxLayout,
)


class CopyableMessageDialog(QDialog):
    def __init__(self, parent, icon, title, message):
        super().__init__(parent)
        self._message = str(message)
        self.setWindowTitle(title)
        self.setModal(True)

        root = QVBoxLayout(self)
        body = QHBoxLayout()

        icon_label = QLabel()
        icon_label.setPixmap(
            self.style().standardIcon(self._standard_icon(icon)).pixmap(48, 48)
        )
        icon_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        body.addWidget(icon_label)

        self.message_label = QLabel(self._message)
        self.message_label.setWordWrap(True)
        self.message_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        body.addWidget(self.message_label, 1)
        root.addLayout(body)

        button_row = QHBoxLayout()
        self.copy_button = QPushButton("Copy Clipboard")
        self.copy_button.clicked.connect(self.copy_to_clipboard)
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        button_row.addWidget(self.copy_button)
        button_row.addStretch()
        button_row.addWidget(self.ok_button)
        root.addLayout(button_row)

        self.ok_button.setDefault(True)
        self.resize(560, 180)

    def _standard_icon(self, icon):
        if icon == QMessageBox.Icon.Critical:
            return QStyle.StandardPixmap.SP_MessageBoxCritical
        if icon == QMessageBox.Icon.Warning:
            return QStyle.StandardPixmap.SP_MessageBoxWarning
        if icon == QMessageBox.Icon.Information:
            return QStyle.StandardPixmap.SP_MessageBoxInformation
        return QStyle.StandardPixmap.SP_MessageBoxQuestion

    def copy_to_clipboard(self):
        QApplication.clipboard().setText(self._message)

    def textInteractionFlags(self):
        return self.message_label.textInteractionFlags()

    def buttons(self):
        return [self.copy_button, self.ok_button]

    def buttonRole(self, button):
        if button is self.copy_button:
            return QMessageBox.ButtonRole.HelpRole
        if button is self.ok_button:
            return QMessageBox.ButtonRole.AcceptRole
        return QMessageBox.ButtonRole.InvalidRole


def build_message_box(parent, icon, title, message):
    return CopyableMessageDialog(parent, icon, title, message)


def show_message_box(parent, icon, title, message):
    build_message_box(parent, icon, title, message).exec()
