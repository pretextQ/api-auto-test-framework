from decimal import Decimal

import pytest
from starlette.requests import Request

from demo_app import main


pytestmark = pytest.mark.unit


def make_request(token=None):
    headers = []
    if token is not None:
        headers.append((b"authorization", f"Bearer {token}".encode("utf-8")))
    return Request({"type": "http", "headers": headers})


class FakeCursor:
    def __init__(self, product=None, update_affected=1, user=None):
        self.product = product
        self.update_affected = update_affected
        self.user = user
        self.lastrowid = 99
        self.executed = []
        self._last_sql = ""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params=None):
        self._last_sql = sql
        self.executed.append((sql, params))
        if sql.startswith("UPDATE products SET stock"):
            return self.update_affected
        return 1

    def fetchone(self):
        if "FROM products" in self._last_sql:
            return self.product
        if "FROM users" in self._last_sql:
            return self.user
        return None


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor
        self.committed = 0
        self.rolled_back = 0
        self.closed = 0

    def cursor(self):
        return self._cursor

    def commit(self):
        self.committed += 1

    def rollback(self):
        self.rolled_back += 1

    def close(self):
        self.closed += 1


def test_get_user_rejects_access_to_another_user(monkeypatch):
    monkeypatch.setattr(main.database, "get_connection", lambda: pytest.fail("不应访问数据库"))
    request = make_request(main.create_token(1))
    assert main.get_user(2, request)["code"] == 403


def test_create_order_rejects_user_id_different_from_token(monkeypatch):
    monkeypatch.setattr(main.database, "get_connection", lambda: pytest.fail("不应访问数据库"))
    request = make_request(main.create_token(1))
    payload = main.OrderRequest(user_id=2, product_id=1002, quantity=1)
    assert main.create_order(payload, request)["code"] == 403


def test_tampered_token_is_rejected_before_database_access(monkeypatch):
    monkeypatch.setattr(main.database, "get_connection", lambda: pytest.fail("不应访问数据库"))
    request = make_request("tampered.token.value")
    payload = main.OrderRequest(product_id=1002, quantity=1)
    assert main.create_order(payload, request)["code"] == 401


def test_missing_user_returns_business_error(monkeypatch):
    cursor = FakeCursor(user=None)
    connection = FakeConnection(cursor)
    monkeypatch.setattr(main.database, "get_connection", lambda: connection)
    request = make_request(main.create_token(999))

    result = main.get_user(999, request)

    assert result["code"] == 2001
    assert connection.committed == 1
    assert connection.closed == 1


def test_atomic_stock_update_prevents_overselling(monkeypatch):
    product = {
        "product_id": 1002,
        "price": Decimal("79.00"),
        "stock": 1,
        "status": "on_sale",
    }
    cursor = FakeCursor(product=product, update_affected=0)
    connection = FakeConnection(cursor)
    monkeypatch.setattr(main.database, "get_connection", lambda: connection)
    request = make_request(main.create_token(1))
    payload = main.OrderRequest(user_id=1, product_id=1002, quantity=2)

    result = main.create_order(payload, request)

    assert result["code"] == 3005
    assert connection.rolled_back == 1
    assert not any(sql.startswith("INSERT INTO orders") for sql, _ in cursor.executed)
    update_sql, update_params = next(
        (sql, params) for sql, params in cursor.executed if sql.startswith("UPDATE products")
    )
    assert "stock >= %s" in update_sql
    assert update_params == (2, 1002, "on_sale", 2)


def test_order_is_written_for_authenticated_user(monkeypatch):
    product = {
        "product_id": 1002,
        "price": Decimal("79.00"),
        "stock": 10,
        "status": "on_sale",
    }
    cursor = FakeCursor(product=product, update_affected=1)
    connection = FakeConnection(cursor)
    monkeypatch.setattr(main.database, "get_connection", lambda: connection)
    request = make_request(main.create_token(7))
    payload = main.OrderRequest(product_id=1002, quantity=2)

    result = main.create_order(payload, request)

    assert result["code"] == 0
    insert_params = next(
        params for sql, params in cursor.executed if sql.startswith("INSERT INTO orders")
    )
    assert insert_params[0] == 7
    assert result["data"]["amount"] == 158.0
    assert connection.committed == 1
