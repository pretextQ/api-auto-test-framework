import pytest

from utils.feishu_notifier import FeishuNotifier

pytestmark = pytest.mark.unit


class FakeResponse:
    def __init__(self):
        self.status_code = 200

    def raise_for_status(self):
        pass

    def json(self):
        return {"code": 0}


@pytest.fixture
def captured(monkeypatch):
    box = {}

    def fake_post(url, json=None, timeout=None):
        box.update({"url": url, "payload": json, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr("utils.feishu_notifier.requests.post", fake_post)
    return box


class TestFeishuNotifier:
    def test_sends_interactive_card_with_result(self, captured):
        notifier = FeishuNotifier("https://open.feishu.cn/hook/x")
        notifier.send_test_result(
            total=6, passed=5, failed=1, skipped=0,
            failures=[f"test_{i}" for i in range(6)]
        )

        payload = captured["payload"]
        assert payload["msg_type"] == "interactive"
        content = payload["card"]["elements"][0]["content"]
        assert "通过: 5" in content
        assert "失败: 1" in content
        # 失败用例最多展示5条
        assert content.count("- test_") == 5
        assert "等 1 个" in content

    def test_sign_added_when_secret_configured(self, captured):
        notifier = FeishuNotifier("https://open.feishu.cn/hook/x", secret="s3cret")
        notifier.send_test_result(total=1, passed=1, failed=0, skipped=0)
        assert "sign" in captured["payload"]
        assert "timestamp" in captured["payload"]

    def test_no_sign_without_secret(self, captured):
        FeishuNotifier("https://open.feishu.cn/hook/x").send_test_result(
            total=1, passed=1, failed=0, skipped=0
        )
        assert "sign" not in captured["payload"]

    def test_network_error_is_swallowed(self, monkeypatch):
        def boom(url, json=None, timeout=None):
            raise RuntimeError("network down")

        monkeypatch.setattr("utils.feishu_notifier.requests.post", boom)
        # 通知失败不应影响测试进程退出码
        FeishuNotifier("https://open.feishu.cn/hook/x").send_test_result(
            total=1, passed=1, failed=0, skipped=0
        )

    def test_execution_error_marks_result_failed(self, captured):
        FeishuNotifier("https://open.feishu.cn/hook/x").send_test_result(
            total=1, passed=0, failed=0, errors=1, skipped=0,
            failures=["test_setup"],
        )
        content = captured["payload"]["card"]["elements"][0]["content"]
        assert "❌ 测试失败" in content
        assert "错误: 1" in content

    def test_ci_and_report_links_are_included(self, captured):
        FeishuNotifier("https://open.feishu.cn/hook/x").send_test_result(
            total=1, passed=1, failed=0, skipped=0,
            run_url="https://ci.example/run/1",
            report_url="https://report.example/1",
        )
        content = captured["payload"]["card"]["elements"][0]["content"]
        assert "https://ci.example/run/1" in content
        assert "https://report.example/1" in content
