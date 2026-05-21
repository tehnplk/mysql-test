import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication, QLineEdit

from main import MainWindow


class PerBackendSettingsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make_window(self):
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".ini")
        tmp.close()
        self.addCleanup(lambda: os.path.exists(tmp.name) and os.unlink(tmp.name))
        settings = QSettings(tmp.name, QSettings.Format.IniFormat)
        return MainWindow(settings=settings)

    def test_switching_database_type_loads_that_type_settings(self):
        win = self.make_window()
        self.addCleanup(win.close)

        win.ui.db_type_combo.setCurrentText("MySQL")
        win.ui.host_edit.setText("mysql.local")
        win.ui.port_edit.setText("3307")
        win.ui.user_edit.setText("mysql_user")
        win.ui.password_edit.setText("mysql_secret")
        win.ui.database_combo.setEditText("mysql_db")
        win.ui.charset_combo.setCurrentText("utf8")
        win.ui.remember_pw_check.setChecked(True)
        win.save_settings()

        win.ui.db_type_combo.setCurrentText("PostgreSQL")
        self.assertEqual(win.ui.port_edit.text(), "5432")
        self.assertEqual(win.ui.password_edit.text(), "")
        win.ui.host_edit.setText("postgres.local")
        win.ui.port_edit.setText("5433")
        win.ui.user_edit.setText("postgres_user")
        win.ui.password_edit.setText("postgres_secret")
        win.ui.database_combo.setEditText("postgres_db")
        win.ui.remember_pw_check.setChecked(False)
        win.save_settings()

        win.ui.db_type_combo.setCurrentText("MySQL")
        self.assertEqual(win.ui.host_edit.text(), "mysql.local")
        self.assertEqual(win.ui.port_edit.text(), "3307")
        self.assertEqual(win.ui.user_edit.text(), "mysql_user")
        self.assertEqual(win.ui.password_edit.text(), "mysql_secret")
        self.assertEqual(win.ui.database_combo.currentText(), "mysql_db")
        self.assertEqual(win.ui.charset_combo.currentText(), "utf8")
        self.assertTrue(win.ui.remember_pw_check.isChecked())

        win.ui.db_type_combo.setCurrentText("PostgreSQL")
        self.assertEqual(win.ui.host_edit.text(), "postgres.local")
        self.assertEqual(win.ui.port_edit.text(), "5433")
        self.assertEqual(win.ui.user_edit.text(), "postgres_user")
        self.assertEqual(win.ui.password_edit.text(), "")
        self.assertEqual(win.ui.database_combo.currentText(), "postgres_db")
        self.assertFalse(win.ui.remember_pw_check.isChecked())

    def test_password_field_shows_plain_text(self):
        win = self.make_window()
        self.addCleanup(win.close)

        self.assertEqual(win.ui.password_edit.echoMode(), QLineEdit.EchoMode.Normal)

    def test_query_editor_starts_with_mysql_default_sql(self):
        win = self.make_window()
        self.addCleanup(win.close)

        self.assertEqual(
            win.ui.query_edit.toPlainText(),
            "select vn , hn , vstdate,vsttime from ovst "
            "where vstdate = CURDATE() order by vn DESC limit 1",
        )

    def test_switching_to_postgresql_updates_default_sql_date_function(self):
        win = self.make_window()
        self.addCleanup(win.close)

        win.ui.db_type_combo.setCurrentText("PostgreSQL")

        self.assertEqual(
            win.ui.query_edit.toPlainText(),
            "select vn , hn , vstdate,vsttime from ovst "
            "where vstdate = CURRENT_DATE order by vn DESC limit 1",
        )

    def test_switching_database_type_does_not_replace_custom_sql(self):
        win = self.make_window()
        self.addCleanup(win.close)

        win.ui.query_edit.setPlainText("select 1")
        win.ui.db_type_combo.setCurrentText("PostgreSQL")

        self.assertEqual(win.ui.query_edit.toPlainText(), "select 1")


if __name__ == "__main__":
    unittest.main()
