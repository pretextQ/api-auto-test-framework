import json
from datetime import timedelta
from types import SimpleNamespace

import pytest

from core.context_manager import TestContext
from core.test_case_base import TestCaseBase


pytestmark = pytest.mark.unit


class FakeSession:
    headers = {"Authorization": "Bearer header-secret", "Accept": "application/json"}


class FakeResponse:
    status_code = 200
    ok = True

    def json(self):
        return {
            "code": 0,
            "data": {"token": "response-secret", "name": "demo", "order_id": 99},
        }


class FakeClient:
    session = FakeSession()
    sensitive_fields = ("id_card",)

    def request(self, method, url, **kwargs):
        return FakeResponse()


def test_request_and_response_attachments_are_sanitized(monkeypatch):
    attachments = []
    monkeypatch.setattr(
        "core.test_case_base.allure.attach",
        lambda body, **kwargs: attachments.append(json.loads(body)),
    )
    context = TestContext()
    context.set("token", "context-secret")

    TestCaseBase.perform_request(FakeClient(), {
        "method": "POST",
        "url": "/api/login",
        "headers": {"X-Token": "eyJabc.def.ghi"},
        "params": {"id_card": "123456"},
        "data": {"username": "demo", "password": "request-secret"},
    }, context)

    rendered = json.dumps(attachments, ensure_ascii=False)
    for secret in (
        "header-secret", "response-secret", "context-secret",
        "request-secret", "eyJabc.def.ghi", "123456",
    ):
        assert secret not in rendered
    assert "demo" in rendered


def test_extracts_response_before_rendering_database_conditions(monkeypatch):
    monkeypatch.setattr("core.test_case_base.allure.attach", lambda *args, **kwargs: None)
    captured = {}

    class FakeDb:
        def fetch_one(self, table, conditions):
            captured.update({"table": table, "conditions": conditions})
            return {"order_id": 99, "status": "created"}

    context = TestContext()
    case = {
        "request": {"method": "POST", "url": "/api/orders"},
        "expected": {"status_code": 200, "business_code": 0},
        "validation": {
            "database": {
                "table": "orders",
                "conditions": {"order_id": "${context.order_id}"},
                "expected": {"status": "created"},
            }
        },
        "extract": {"order_id": "$.data.order_id"},
    }

    TestCaseBase().run_data_driven_case(FakeClient(), FakeDb(), context, case)

    assert context.get("order_id") == 99
    assert captured == {"table": "orders", "conditions": {"order_id": 99}}


def test_multiple_jsonpath_assertions_are_supported(monkeypatch):
    monkeypatch.setattr("core.test_case_base.allure.attach", lambda *args, **kwargs: None)
    case = {
        "request": {"method": "GET", "url": "/api/orders"},
        "expected": {"status_code": 200, "business_code": 0},
        "validation": {"jsonpath": [
            {"expr": "$.data.name", "value": "demo"},
            {"expr": "$.data.order_id", "value": 99},
        ]},
    }
    TestCaseBase().run_data_driven_case(FakeClient(), None, TestContext(), case)


def test_response_time_assertion_reports_limit():
    fast = SimpleNamespace(elapsed=timedelta(milliseconds=20))
    slow = SimpleNamespace(elapsed=timedelta(milliseconds=120))
    TestCaseBase.assert_response_time(fast, 100)
    with pytest.raises(AssertionError, match="响应时间超限"):
        TestCaseBase.assert_response_time(slow, 100)
