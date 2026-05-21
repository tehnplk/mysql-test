import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QMessageBox

from dialogs import build_message_box


class MessageDialogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_message_box_text_can_be_selected_for_copying(self):
        box = build_message_box(
            None,
            QMessageBox.Icon.Critical,
            "Query error",
            "permission denied for table users",
        )
        self.addCleanup(box.close)

        flags = box.textInteractionFlags()
        self.assertTrue(flags & Qt.TextInteractionFlag.TextSelectableByMouse)
        self.assertTrue(flags & Qt.TextInteractionFlag.TextSelectableByKeyboard)

    def test_message_box_has_copy_clipboard_button(self):
        box = build_message_box(
            None,
            QMessageBox.Icon.Warning,
            "Connection failed",
            "password authentication failed",
        )
        self.addCleanup(box.close)

        button_texts = [button.text() for button in box.buttons()]

        self.assertIn("Copy Clipboard", button_texts)

    def test_copy_clipboard_button_copies_message_text(self):
        box = build_message_box(
            None,
            QMessageBox.Icon.Information,
            "Connection OK",
            "Connected to PostgreSQL",
        )
        self.addCleanup(box.close)
        QApplication.clipboard().clear()
        copy_button = next(
            button for button in box.buttons() if button.text() == "Copy Clipboard"
        )

        copy_button.click()

        self.assertEqual(QApplication.clipboard().text(), "Connected to PostgreSQL")

    def test_copy_clipboard_button_uses_non_accepting_left_role(self):
        box = build_message_box(
            None,
            QMessageBox.Icon.Critical,
            "Query error",
            "syntax error near FROM",
        )
        self.addCleanup(box.close)
        copy_button = next(
            button for button in box.buttons() if button.text() == "Copy Clipboard"
        )

        self.assertEqual(box.buttonRole(copy_button), QMessageBox.ButtonRole.HelpRole)

    def test_copy_clipboard_button_is_first_button_in_visual_order(self):
        box = build_message_box(
            None,
            QMessageBox.Icon.Critical,
            "Connection failed",
            "authentication failed",
        )
        self.addCleanup(box.close)

        button_texts = [button.text() for button in box.buttons()]

        self.assertEqual(button_texts[0], "Copy Clipboard")
        self.assertEqual(button_texts[-1], "OK")

    def test_copy_clipboard_button_does_not_accept_or_reject_dialog(self):
        box = build_message_box(
            None,
            QMessageBox.Icon.Warning,
            "Connection warning",
            "server closed the connection",
        )
        self.addCleanup(box.close)
        accepted = []
        rejected = []
        box.accepted.connect(lambda: accepted.append(True))
        box.rejected.connect(lambda: rejected.append(True))
        copy_button = next(
            button for button in box.buttons() if button.text() == "Copy Clipboard"
        )

        copy_button.click()
        QApplication.processEvents()

        self.assertEqual(accepted, [])
        self.assertEqual(rejected, [])


if __name__ == "__main__":
    unittest.main()
