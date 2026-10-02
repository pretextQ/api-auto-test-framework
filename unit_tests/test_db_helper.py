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

    def cursor(self):
        return self._cursor

    def commit(self):
        self.committed += 1

    def rollback(self):
        self.rolled_back += 1

    def close(self):
        self.open = False


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
        install_fake(cursor)

        result = make_helper().fetch_one("users", {"username": "testuser"})

        assert result == row
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

    def test_close_is_idempotent(self, install_fake):
        cursor = FakeCursor(rows=[])
        conn = install_fake(cursor)
        helper = make_helper()
        helper.fetch_one("users", {"id": 1})  # 先触发惰性连接建立

        helper.close()
        helper.close()

        assert conn.open is False
