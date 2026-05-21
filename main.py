import sys
from dataclasses import dataclass

from PyQt6.QtCore import (
    QObject,
    QSettings,
    QSortFilterProxyModel,
    Qt,
    QThread,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMessageBox,
)

from db import create_client, default_port_for, normalize_database_type
from dialogs import show_message_box
from models import ResultTableModel
from ui_main import MainWindowUI


DEFAULT_SQL_BY_DATABASE_TYPE = {
    "mysql": (
        "select vn , hn , vstdate,vsttime from ovst "
        "where vstdate = CURDATE() order by vn DESC limit 1"
    ),
    "postgresql": (
        "select vn , hn , vstdate,vsttime from ovst "
        "where vstdate = CURRENT_DATE order by vn DESC limit 1"
    ),
}


def default_sql_for(database_type: str) -> str:
    return DEFAULT_SQL_BY_DATABASE_TYPE[normalize_database_type(database_type)]


@dataclass(frozen=True)
class ConnectionParams:
    database_type: str
    host: str
    port: int
    user: str
    password: str
    database: str
    charset: str


class ConnectionWorker(QObject):
    succeeded = pyqtSignal(str, object, object, str)
    failed = pyqtSignal(str, str)

    def __init__(self, mode: str, params: ConnectionParams):
        super().__init__()
        self.mode = mode
        self.params = params

    @pyqtSlot()
    def run(self):
        client = None
        try:
            client = create_client(self.params.database_type)
            client.connect(
                host=self.params.host,
                port=self.params.port,
                user=self.params.user,
                password=self.params.password,
                database=self.params.database,
                charset=self.params.charset,
                connect_timeout=5,
            )
            databases = client.list_databases() if self.mode == "connect" else []
            message = (
                f"Connected to {self.params.database_type}: "
                f"{self.params.user}@{self.params.host}:{self.params.port}"
            )
            if self.mode == "test":
                client.close()
                client = None
            self.succeeded.emit(self.mode, client, databases, message)
        except Exception as e:
            if client is not None:
                client.close()
            self.failed.emit(self.mode, str(e))


class SortProxy(QSortFilterProxyModel):
    """Numeric-aware sorting; falls back to string compare."""

    def lessThan(self, left, right):
        l = self.sourceModel().data(left, Qt.ItemDataRole.DisplayRole)
        r = self.sourceModel().data(right, Qt.ItemDataRole.DisplayRole)
        if l == "NULL" and r != "NULL":
            return True
        if r == "NULL" and l != "NULL":
            return False
        try:
            return float(l) < float(r)
        except (TypeError, ValueError):
            return (l or "") < (r or "")


class MainWindow(QMainWindow):
    def __init__(self, settings=None):
        super().__init__()
        self.ui = MainWindowUI()
        self.ui.setup_ui(self)

        self.settings = settings or QSettings("mysql-test", "MySQLQueryTool")
        self.db = create_client("mysql")
        self._connection_thread = None
        self._connection_worker = None
        self._loading_settings = False
        self._active_database_type = "MySQL"
        self.source_model = ResultTableModel()
        self.proxy = SortProxy(self)
        self.proxy.setSourceModel(self.source_model)
        self.ui.result_table.setModel(self.proxy)

        self._db_switching = False
        self.ui.test_connection_btn.clicked.connect(self.on_test_connection)
        self.ui.connect_btn.clicked.connect(self.on_connect)
        self.ui.disconnect_btn.clicked.connect(self.on_disconnect)
        self.ui.execute_btn.clicked.connect(self.on_execute)
        self.ui.clear_btn.clicked.connect(self.ui.query_edit.clear)
        self.ui.database_combo.activated.connect(self.on_database_changed)
        self.ui.db_type_combo.currentTextChanged.connect(
            self.on_database_type_changed
        )

        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self.on_execute)
        QShortcut(QKeySequence("Ctrl+Enter"), self, activated=self.on_execute)

        self.load_settings()

    def load_settings(self):
        s = self.settings
        self._loading_settings = True
        db_type = s.value("conn/type", "MySQL", type=str)
        if self.ui.db_type_combo.findText(db_type) >= 0:
            self.ui.db_type_combo.setCurrentText(db_type)
        else:
            self.ui.db_type_combo.setCurrentText("MySQL")
        self._active_database_type = self.ui.db_type_combo.currentText()
        self.load_connection_settings(self._active_database_type)
        self._loading_settings = False
        self.update_database_type_controls()
        self.apply_default_query_sql(self._active_database_type)
        geom = s.value("window/geometry")
        if geom is not None:
            self.restoreGeometry(geom)

    def connection_setting_key(self, database_type, name):
        db_type = normalize_database_type(database_type)
        return f"conn/{db_type}/{name}"

    def load_connection_settings(self, database_type):
        s = self.settings
        key = lambda name: self.connection_setting_key(database_type, name)
        self.ui.host_edit.setText(s.value(key("host"), "127.0.0.1", type=str))
        self.ui.port_edit.setText(
            s.value(key("port"), str(default_port_for(database_type)), type=str)
        )
        self.ui.user_edit.setText(s.value(key("user"), "root", type=str))
        self.ui.database_combo.setEditText(s.value(key("database"), "", type=str))
        self.ui.charset_combo.setCurrentText(
            s.value(key("charset"), "utf8mb4", type=str)
        )
        remember = s.value(key("remember_password"), False, type=bool)
        self.ui.remember_pw_check.setChecked(remember)
        if remember:
            self.ui.password_edit.setText(s.value(key("password"), "", type=str))
        else:
            self.ui.password_edit.clear()

    def save_settings(self):
        s = self.settings
        s.setValue("conn/type", self.ui.db_type_combo.currentText())
        self.save_connection_settings(self.ui.db_type_combo.currentText())
        s.setValue("window/geometry", self.saveGeometry())

    def save_connection_settings(self, database_type):
        s = self.settings
        key = lambda name: self.connection_setting_key(database_type, name)
        s.setValue(key("host"), self.ui.host_edit.text())
        s.setValue(key("port"), self.ui.port_edit.text())
        s.setValue(key("user"), self.ui.user_edit.text())
        s.setValue(key("database"), self.ui.database_combo.currentText())
        s.setValue(key("charset"), self.ui.charset_combo.currentText().strip())
        remember = self.ui.remember_pw_check.isChecked()
        s.setValue(key("remember_password"), remember)
        if remember:
            s.setValue(key("password"), self.ui.password_edit.text())
        else:
            s.remove(key("password"))

    def closeEvent(self, event):
        self.save_settings()
        self.db.close()
        if self._connection_thread is not None:
            self._connection_thread.quit()
            self._connection_thread.wait(1000)
        super().closeEvent(event)

    def on_database_type_changed(self, database_type):
        if self._loading_settings:
            return
        if self.db.connected or self._connection_thread is not None:
            self.ui.db_type_combo.setCurrentText(self._active_database_type)
            return
        self.save_connection_settings(self._active_database_type)
        self.load_connection_settings(database_type)
        self._active_database_type = database_type
        self.db = create_client(database_type)
        self.update_database_type_controls()
        self.apply_default_query_sql(database_type)

    def update_database_type_controls(self):
        is_mysql = (
            normalize_database_type(self.ui.db_type_combo.currentText()) == "mysql"
        )
        self.ui.charset_combo.setEnabled(is_mysql)
        self.ui.charset_label.setEnabled(is_mysql)

    def apply_default_query_sql(self, database_type):
        current_sql = self.ui.query_edit.toPlainText().strip()
        default_sql_values = set(DEFAULT_SQL_BY_DATABASE_TYPE.values())
        if current_sql and current_sql not in default_sql_values:
            return
        self.ui.query_edit.setPlainText(default_sql_for(database_type))

    def connection_params_from_ui(self):
        database_type = self.ui.db_type_combo.currentText()
        try:
            port = int(
                self.ui.port_edit.text() or str(default_port_for(database_type))
            )
        except ValueError:
            show_message_box(
                self,
                QMessageBox.Icon.Warning,
                "Invalid port",
                "Port must be a number",
            )
            return None
        return ConnectionParams(
            database_type=database_type,
            host=self.ui.host_edit.text().strip() or "127.0.0.1",
            port=port,
            user=self.ui.user_edit.text(),
            password=self.ui.password_edit.text(),
            database=self.ui.database_combo.currentText().strip(),
            charset=self.ui.charset_combo.currentText().strip() or "utf8mb4",
        )

    def on_test_connection(self):
        self.start_connection_task("test")

    def on_connect(self):
        self.start_connection_task("connect")

    def start_connection_task(self, mode):
        if self._connection_thread is not None:
            return
        params = self.connection_params_from_ui()
        if params is None:
            return
        self.set_connection_controls_busy(True)
        self.ui.status_bar.showMessage(
            "Testing connection..." if mode == "test" else "Connecting..."
        )
        thread = QThread(self)
        worker = ConnectionWorker(mode, params)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.succeeded.connect(self.on_connection_succeeded)
        worker.failed.connect(self.on_connection_failed)
        worker.succeeded.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(self.clear_connection_task)
        self._connection_thread = thread
        self._connection_worker = worker
        thread.start()

    def set_connection_controls_busy(self, busy):
        self.ui.test_connection_btn.setEnabled(not busy and not self.db.connected)
        self.ui.connect_btn.setEnabled(not busy and not self.db.connected)
        self.ui.disconnect_btn.setEnabled(not busy and self.db.connected)
        self.ui.db_type_combo.setEnabled(not busy and not self.db.connected)

    def clear_connection_task(self):
        if self._connection_thread is not None:
            self._connection_thread.deleteLater()
        self._connection_thread = None
        self._connection_worker = None
        self.set_connection_controls_busy(False)

    def on_connection_succeeded(self, mode, client, databases, message):
        if mode == "test":
            self.ui.status_bar.showMessage("Test connection OK")
            show_message_box(
                self,
                QMessageBox.Icon.Information,
                "Connection OK",
                message,
            )
            return
        self.db = client
        self.ui.connect_btn.setEnabled(False)
        self.ui.test_connection_btn.setEnabled(False)
        self.ui.disconnect_btn.setEnabled(True)
        self.ui.execute_btn.setEnabled(True)
        self.ui.db_type_combo.setEnabled(False)
        self.apply_database_list(databases)
        self.ui.status_bar.showMessage(
            f"Connected {self.ui.db_type_combo.currentText()}: "
            f"{self.ui.user_edit.text()}@{self.ui.host_edit.text()}/"
            f"{self.ui.database_combo.currentText()}"
        )
        self.save_settings()

    def on_connection_failed(self, mode, message):
        title = "Test connection failed" if mode == "test" else "Connection failed"
        show_message_box(self, QMessageBox.Icon.Critical, title, message)
        self.ui.status_bar.showMessage(title)

    def populate_databases(self):
        try:
            dbs = self.db.list_databases()
        except Exception as e:
            self.ui.status_bar.showMessage(f"List DB failed: {e}")
            return
        self.apply_database_list(dbs)

    def apply_database_list(self, dbs):
        current = self.ui.database_combo.currentText().strip()
        self._db_switching = True
        self.ui.database_combo.clear()
        self.ui.database_combo.addItems(dbs)
        if current and current in dbs:
            self.ui.database_combo.setCurrentText(current)
        elif current:
            self.ui.database_combo.setEditText(current)
        self._db_switching = False

    def on_database_changed(self, _index):
        if self._db_switching or not self.db.connected:
            return
        name = self.ui.database_combo.currentText().strip()
        if not name:
            return
        try:
            self.db.use_database(name)
            self.ui.status_bar.showMessage(f"Using database: {name}")
            self.save_settings()
        except Exception as e:
            show_message_box(
                self,
                QMessageBox.Icon.Critical,
                "Switch DB failed",
                str(e),
            )

    def on_disconnect(self):
        current = self.ui.database_combo.currentText()
        self.db.close()
        self._db_switching = True
        self.ui.database_combo.clear()
        self.ui.database_combo.setEditText(current)
        self._db_switching = False
        self.ui.connect_btn.setEnabled(True)
        self.ui.test_connection_btn.setEnabled(True)
        self.ui.disconnect_btn.setEnabled(False)
        self.ui.execute_btn.setEnabled(False)
        self.ui.db_type_combo.setEnabled(True)
        self.ui.status_bar.showMessage("Disconnected")

    def on_execute(self):
        if not self.db.connected:
            return
        sql = self.ui.query_edit.toPlainText().strip().rstrip(";")
        if not sql:
            return
        try:
            cols, rows, affected = self.db.execute(sql)
        except Exception as e:
            show_message_box(
                self,
                QMessageBox.Icon.Critical,
                "Query error",
                str(e),
            )
            self.ui.status_bar.showMessage("Error")
            return

        if cols:
            self.source_model.set_data(cols, rows)
            self.ui.result_table.resizeColumnsToContents()
            self.ui.status_bar.showMessage(f"Returned {len(rows)} row(s)")
        else:
            self.source_model.set_data([], [])
            self.ui.status_bar.showMessage(f"OK, {affected} row(s) affected")


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
