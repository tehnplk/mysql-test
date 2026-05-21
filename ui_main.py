from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QLineEdit, QPushButton, QPlainTextEdit, QTableView,
    QSplitter, QStatusBar, QCheckBox, QComboBox,
)
from PyQt6.QtCore import Qt


class MainWindowUI:
    def setup_ui(self, window):
        window.setWindowTitle("SQL Query Tool")
        window.resize(460, 800)

        central = QWidget(window)
        window.setCentralWidget(central)
        root = QVBoxLayout(central)

        # --- Connection group ---
        conn_box = QGroupBox("Connection")
        grid = QGridLayout(conn_box)

        self.db_type_combo = QComboBox()
        self.db_type_combo.addItems(["MySQL", "PostgreSQL"])
        self.host_edit = QLineEdit("127.0.0.1")
        self.port_edit = QLineEdit("3306")
        self.user_edit = QLineEdit("root")
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Normal)
        self.database_combo = QComboBox()
        self.database_combo.setEditable(True)
        self.database_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.charset_combo = QComboBox()
        self.charset_combo.setEditable(True)
        self.charset_combo.addItems(["utf8mb4", "utf8", "latin1", "tis620"])

        grid.addWidget(QLabel("Database Type:"), 0, 0)
        grid.addWidget(self.db_type_combo, 0, 1, 1, 3)
        grid.addWidget(QLabel("Host:"), 1, 0)
        grid.addWidget(self.host_edit, 1, 1)
        grid.addWidget(QLabel("Port:"), 1, 2)
        grid.addWidget(self.port_edit, 1, 3)
        grid.addWidget(QLabel("User:"), 2, 0)
        grid.addWidget(self.user_edit, 2, 1)
        grid.addWidget(QLabel("Password:"), 2, 2)
        grid.addWidget(self.password_edit, 2, 3)
        grid.addWidget(QLabel("Database:"), 3, 0)
        grid.addWidget(self.database_combo, 3, 1, 1, 3)
        self.charset_label = QLabel("Charset:")
        grid.addWidget(self.charset_label, 4, 0)
        grid.addWidget(self.charset_combo, 4, 1, 1, 3)

        self.remember_pw_check = QCheckBox("Remember password")
        grid.addWidget(self.remember_pw_check, 5, 0, 1, 4)

        self.connect_btn = QPushButton("Connect")
        self.test_connection_btn = QPushButton("Test Connection")
        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.setEnabled(False)
        btn_row = QHBoxLayout()
        btn_row.addWidget(self.test_connection_btn)
        btn_row.addWidget(self.connect_btn)
        btn_row.addWidget(self.disconnect_btn)
        btn_row.addStretch()
        grid.addLayout(btn_row, 6, 0, 1, 4)

        root.addWidget(conn_box)

        # --- Query / Result splitter ---
        splitter = QSplitter(Qt.Orientation.Vertical)

        query_box = QGroupBox("Query")
        q_layout = QVBoxLayout(query_box)
        self.query_edit = QPlainTextEdit()
        self.query_edit.setPlaceholderText("เขียน SQL ที่นี่ เช่น SELECT * FROM your_table;")
        q_layout.addWidget(self.query_edit)
        q_btns = QHBoxLayout()
        self.execute_btn = QPushButton("Execute (Ctrl+Enter)")
        self.execute_btn.setEnabled(False)
        self.clear_btn = QPushButton("Clear")
        q_btns.addWidget(self.execute_btn)
        q_btns.addWidget(self.clear_btn)
        q_btns.addStretch()
        q_layout.addLayout(q_btns)
        splitter.addWidget(query_box)

        result_box = QGroupBox("Result")
        r_layout = QVBoxLayout(result_box)
        self.result_table = QTableView()
        self.result_table.setSortingEnabled(True)
        self.result_table.setAlternatingRowColors(True)
        self.result_table.horizontalHeader().setStretchLastSection(True)
        self.result_table.setSelectionBehavior(
            QTableView.SelectionBehavior.SelectRows
        )
        r_layout.addWidget(self.result_table)
        splitter.addWidget(result_box)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        root.addWidget(splitter, 1)

        self.status_bar = QStatusBar()
        window.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Disconnected")
