import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication

import main as main_module
from main import MainWindow


class AsyncConnectionDispatchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make_window(self):
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".ini")
        tmp.close()
        self.addCleanup(lambda: os.path.exists(tmp.name) and os.unlink(tmp.name))
        settings = QSettings(tmp.name, QSettings.Format.IniFormat)
        return MainWindow(settings=settings)

    def test_test_connection_button_dispatches_test_mode(self):
        win = self.make_window()
        self.addCleanup(win.close)
        calls = []
        win.start_connection_task = lambda mode: calls.append(mode)

        win.ui.test_connection_btn.click()

        self.assertEqual(calls, ["test"])

    def test_connect_dispatches_connect_mode_without_sync_client_creation(self):
        win = self.make_window()
        self.addCleanup(win.close)
        calls = []
        win.start_connection_task = lambda mode: calls.append(mode)
        original_create_client = main_module.create_client
        main_module.create_client = self.fail_if_create_client_is_called
        self.addCleanup(lambda: setattr(main_module, "create_client", original_create_client))

        win.on_connect()

        self.assertEqual(calls, ["connect"])

    def fail_if_create_client_is_called(self, _database_type):
        raise AssertionError("UI thread must not create/connect database clients directly")


if __name__ == "__main__":
    unittest.main()
