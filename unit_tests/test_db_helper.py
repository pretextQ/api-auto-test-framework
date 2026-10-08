import pytest

from utils.db_helper import DatabaseHelper

pytestmark = pytest.mark.unit


class FakeCursor:
    def __init__(self, rows=None, error=None):
        self.rows = rows or []
        self.error = error
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params=None):
        if self.error:
            raise self.error
        self.executed.append((sql, params))

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor
        self.open = True
        self.committed = 0
        self.rolled_back = 0
        self.ping_calls = 0

    def cursor(self):
        return self._cursor

    def commit(self):
        self.committed += 1

    def rollback(self):
        self.rolled_back += 1

    def close(self):
        self.open = False

    def ping(self, reconnect=False):
        self.ping_calls += 1


@pytest.fixture
def install_fake(monkeypatch):
    """替换pymysql.connect,返回连接安装器(调用时传入FakeCursor,返回FakeConnection)"""
    def install(cursor):
        conn = FakeConnection(cursor)
        monkeypatch.setattr("utils.db_helper.pymysql.connect", lambda **kwargs: conn)
        return conn

    return install


def make_helper() -> DatabaseHelper:
    return DatabaseHelper({"host": "h", "port": 3306, "user": "u",
                           "password": "p", "name": "db"})


class TestDatabaseHelper:
    def test_fetch_one_builds_sql_and_returns_row(self, install_fake):
        row = {"user_id": 1, "status": "active"}
        cursor = FakeCursor(rows=[row])
        conn = install_fake(cursor)

        result = make_helper().fetch_one("users", {"username": "testuser"})

        assert result == row
        assert conn.committed == 1
        sql, params = cursor.executed[0]
        assert sql == "SELECT * FROM users WHERE username = %s LIMIT 1"
        assert params == ("testuser",)

    def test_fetch_one_returns_none_when_no_result(self, install_fake):
        install_fake(FakeCursor(rows=[]))
        assert make_helper().fetch_one("users", {"id": 1}) is None

    def test_multiple_conditions_joined_with_and(self, install_fake):
        cursor = FakeCursor(rows=[])
        install_fake(cursor)

        make_helper().fetch_one("orders", {"user_id": 1, "status": "created"})

        sql, params = cursor.executed[0]
        assert "user_id = %s AND status = %s" in sql
        assert params == (1, "created")

    def test_execute_update_commits(self, install_fake):
        cursor = FakeCursor()
        conn = install_fake(cursor)

        make_helper().execute_update("UPDATE products SET stock = %s", (10,))

        assert conn.committed == 1
        assert cursor.executed[0][0].startswith("UPDATE products")

    def test_execute_update_rolls_back_on_error(self, install_fake):
        conn = install_fake(FakeCursor(error=RuntimeError("db down")))

        with pytest.raises(RuntimeError):
            make_helper().execute_update("UPDATE x SET y = 1")

        assert conn.rolled_back == 1
        assert conn.committed == 0

    def test_execute_query_rolls_back_on_error(self, install_fake):
        conn = install_fake(FakeCursor(error=RuntimeError("query failed")))
        with pytest.raises(RuntimeError):
            make_helper().execute_query("SELECT 1")
        assert conn.rolled_back == 1

    def test_close_is_idempotent(self, install_fake):
        cursor = FakeCursor(rows=[])
        conn = install_fake(cursor)
        helper = make_helper()
        helper.fetch_one("users", {"id": 1})  # 先触发惰性连接建立

        helper.close()
        helper.close()

        assert conn.open is False

    @pytest.mark.parametrize("table", ["orders; DROP TABLE users", "orders-name", ""])
    def test_fetch_one_rejects_unsafe_table_names(self, table):
        with pytest.raises(ValueError, match="非法表名"):
            make_helper().fetch_one(table, {"id": 1})

    def test_fetch_one_rejects_unsafe_column_names(self):
        with pytest.raises(ValueError, match="非法列名"):
            make_helper().fetch_one("orders", {"id OR 1=1": 1})

    def test_fetch_one_rejects_empty_conditions(self):
        with pytest.raises(ValueError, match="非空"):
            make_helper().fetch_one("orders", {})

    def test_reuses_live_connection_after_ping(self, install_fake):
        conn = install_fake(FakeCursor(rows=[]))
        helper = make_helper()
        helper.fetch_one("orders", {"id": 1})
        helper.fetch_one("orders", {"id": 2})
        assert conn.ping_calls == 1

    def test_validate_rejects_empty_expected_before_query(self):
        with pytest.raises(ValueError, match="expected"):
            make_helper().validate("orders", {"id": 1}, {})
