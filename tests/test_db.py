import unittest

from db import (
    MySQLClient,
    PostgreSQLClient,
    create_client,
    default_port_for,
    ensure_sql_allowed,
)


class DatabaseBackendSelectionTest(unittest.TestCase):
    def test_default_ports_follow_database_type(self):
        self.assertEqual(default_port_for("mysql"), 3306)
        self.assertEqual(default_port_for("postgresql"), 5432)
        self.assertEqual(default_port_for("PostgreSQL"), 5432)

    def test_create_client_uses_selected_database_type(self):
        self.assertIsInstance(create_client("mysql"), MySQLClient)
        self.assertIsInstance(create_client("postgresql"), PostgreSQLClient)

    def test_create_client_rejects_unknown_database_type(self):
        with self.assertRaises(ValueError):
            create_client("sqlite")


class SqlSafetyTest(unittest.TestCase):
    def assertSqlBlocked(self, sql, command):
        with self.assertRaisesRegex(ValueError, f"{command} statements are not allowed"):
            ensure_sql_allowed(sql)

    def test_rejects_delete_statement(self):
        self.assertSqlBlocked("delete from users where id = 1", "DELETE")

    def test_rejects_delete_case_insensitively_after_comment(self):
        sql = "/* cleanup */\nDELETE FROM users"

        self.assertSqlBlocked(sql, "DELETE")

    def test_rejects_delete_in_multi_statement_sql(self):
        sql = "select * from users; delete from users where id = 1"

        self.assertSqlBlocked(sql, "DELETE")

    def test_rejects_drop_statement(self):
        self.assertSqlBlocked("drop table users", "DROP")

    def test_rejects_drop_case_insensitively_after_comment(self):
        sql = "-- remove temp table\nDROP TABLE users"

        self.assertSqlBlocked(sql, "DROP")

    def test_rejects_drop_in_multi_statement_sql(self):
        sql = "select 1; drop schema public"

        self.assertSqlBlocked(sql, "DROP")

    def test_allows_delete_word_inside_string_literal(self):
        ensure_sql_allowed("select 'delete from users' as sample_text")

    def test_allows_drop_word_inside_string_literal(self):
        ensure_sql_allowed("select 'drop table users' as sample_text")

    def test_allows_select_with_identifier_containing_delete(self):
        ensure_sql_allowed("select deleted_at from users")

    def test_allows_select_with_identifier_containing_drop(self):
        ensure_sql_allowed("select dropdown_value from settings")

    def test_mysql_execute_rejects_delete_before_cursor(self):
        client = MySQLClient()
        client.conn = OpenConnectionProbe()

        with self.assertRaisesRegex(ValueError, "DELETE statements are not allowed"):
            client.execute("delete from users")

        self.assertFalse(client.conn.cursor_called)

    def test_postgresql_execute_rejects_delete_before_cursor(self):
        client = PostgreSQLClient()
        client.conn = OpenConnectionProbe()

        with self.assertRaisesRegex(ValueError, "DELETE statements are not allowed"):
            client.execute("delete from users")

        self.assertFalse(client.conn.cursor_called)

    def test_mysql_execute_rejects_drop_before_cursor(self):
        client = MySQLClient()
        client.conn = OpenConnectionProbe()

        with self.assertRaisesRegex(ValueError, "DROP statements are not allowed"):
            client.execute("drop table users")

        self.assertFalse(client.conn.cursor_called)

    def test_postgresql_execute_rejects_drop_before_cursor(self):
        client = PostgreSQLClient()
        client.conn = OpenConnectionProbe()

        with self.assertRaisesRegex(ValueError, "DROP statements are not allowed"):
            client.execute("drop table users")

        self.assertFalse(client.conn.cursor_called)


class OpenConnectionProbe:
    open = True
    closed = False

    def __init__(self):
        self.cursor_called = False

    def cursor(self):
        self.cursor_called = True
        raise AssertionError("cursor should not be opened for blocked SQL")


if __name__ == "__main__":
    unittest.main()
