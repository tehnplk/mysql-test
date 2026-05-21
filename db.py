import pymysql
from pymysql.cursors import DictCursor


BLOCKED_SQL_COMMANDS = {"delete", "drop"}


def _sql_without_strings_and_comments(sql: str) -> str:
    output = []
    i = 0
    quote = None
    while i < len(sql):
        ch = sql[i]
        nxt = sql[i + 1] if i + 1 < len(sql) else ""

        if quote:
            output.append(" ")
            if ch == quote:
                if nxt == quote:
                    output.append(" ")
                    i += 2
                    continue
                quote = None
            elif ch == "\\" and nxt:
                output.append(" ")
                i += 2
                continue
            i += 1
            continue

        if ch in ("'", '"', "`"):
            quote = ch
            output.append(" ")
            i += 1
            continue

        if ch == "-" and nxt == "-":
            output.extend("  ")
            i += 2
            while i < len(sql) and sql[i] not in "\r\n":
                output.append(" ")
                i += 1
            continue

        if ch == "#":
            output.append(" ")
            i += 1
            while i < len(sql) and sql[i] not in "\r\n":
                output.append(" ")
                i += 1
            continue

        if ch == "/" and nxt == "*":
            output.extend("  ")
            i += 2
            while i < len(sql):
                if sql[i] == "*" and i + 1 < len(sql) and sql[i + 1] == "/":
                    output.extend("  ")
                    i += 2
                    break
                output.append(" ")
                i += 1
            continue

        output.append(ch)
        i += 1

    return "".join(output)


def ensure_sql_allowed(sql: str):
    searchable = _sql_without_strings_and_comments(sql)
    tokens = []
    current = []
    for ch in searchable:
        if ch.isalnum() or ch == "_":
            current.append(ch)
        elif current:
            tokens.append("".join(current).lower())
            current = []
    if current:
        tokens.append("".join(current).lower())

    for command in sorted(BLOCKED_SQL_COMMANDS):
        if command in tokens:
            raise ValueError(f"{command.upper()} statements are not allowed")


def normalize_database_type(database_type: str) -> str:
    db_type = database_type.strip().lower()
    aliases = {
        "mysql": "mysql",
        "postgres": "postgresql",
        "postgresql": "postgresql",
    }
    if db_type not in aliases:
        raise ValueError(f"Unsupported database type: {database_type}")
    return aliases[db_type]


def default_port_for(database_type: str) -> int:
    return 5432 if normalize_database_type(database_type) == "postgresql" else 3306


def create_client(database_type: str):
    if normalize_database_type(database_type) == "postgresql":
        return PostgreSQLClient()
    return MySQLClient()


class MySQLClient:
    def __init__(self):
        self.conn: pymysql.connections.Connection | None = None

    @property
    def connected(self) -> bool:
        return self.conn is not None and self.conn.open

    def connect(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str,
        charset: str,
        connect_timeout: int = 5,
    ):
        self.close()
        self.conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database or None,
            cursorclass=DictCursor,
            autocommit=True,
            charset=charset,
            connect_timeout=connect_timeout,
        )

    def close(self):
        if self.conn is not None:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None

    def list_databases(self) -> list[str]:
        if not self.connected:
            raise RuntimeError("Not connected")
        with self.conn.cursor() as cur:
            cur.execute("SHOW DATABASES")
            rows = cur.fetchall()
        skip = {"information_schema", "performance_schema", "mysql", "sys"}
        names = [list(r.values())[0] for r in rows]
        return [n for n in names if n not in skip] + [n for n in names if n in skip]

    def use_database(self, name: str):
        if not self.connected:
            raise RuntimeError("Not connected")
        self.conn.select_db(name)

    def execute(self, sql: str):
        """
        Returns (columns, rows, affected).
        - SELECT/SHOW/DESCRIBE: columns + rows populated, affected = len(rows)
        - DML/DDL: columns=[], rows=[], affected = rowcount
        """
        if not self.connected:
            raise RuntimeError("Not connected")
        ensure_sql_allowed(sql)

        with self.conn.cursor() as cur:
            affected = cur.execute(sql)
            if cur.description:
                cols = [d[0] for d in cur.description]
                raw = cur.fetchall()
                rows = [[r.get(c) for c in cols] for r in raw]
                return cols, rows, len(rows)
            return [], [], affected


class PostgreSQLClient:
    def __init__(self):
        self.conn = None
        self._params: dict | None = None

    @property
    def connected(self) -> bool:
        return self.conn is not None and not getattr(self.conn, "closed", True)

    def connect(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str,
        charset: str,
        connect_timeout: int = 5,
    ):
        import psycopg
        from psycopg.rows import dict_row

        self.close()
        self._params = {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "database": database,
            "charset": charset,
        }
        self.conn = psycopg.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            dbname=database or None,
            autocommit=True,
            row_factory=dict_row,
            connect_timeout=connect_timeout,
        )

    def close(self):
        if self.conn is not None:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None

    def list_databases(self) -> list[str]:
        if not self.connected:
            raise RuntimeError("Not connected")
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT datname
                FROM pg_database
                WHERE datallowconn
                ORDER BY datistemplate, datname
                """
            )
            rows = cur.fetchall()
        return [r["datname"] for r in rows]

    def use_database(self, name: str):
        if not self.connected:
            raise RuntimeError("Not connected")
        if not self._params:
            raise RuntimeError("Connection parameters are unavailable")
        params = dict(self._params)
        params["database"] = name
        self.connect(**params)

    def execute(self, sql: str):
        """
        Returns (columns, rows, affected).
        - SELECT/SHOW/DESCRIBE: columns + rows populated, affected = len(rows)
        - DML/DDL: columns=[], rows=[], affected = rowcount
        """
        if not self.connected:
            raise RuntimeError("Not connected")
        ensure_sql_allowed(sql)

        with self.conn.cursor() as cur:
            cur.execute(sql)
            if cur.description:
                cols = [d.name for d in cur.description]
                raw = cur.fetchall()
                rows = [[r.get(c) for c in cols] for r in raw]
                return cols, rows, len(rows)
            return [], [], cur.rowcount
