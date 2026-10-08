import pytest

from data.data_manager import DataManager

pytestmark = pytest.mark.unit

DATA_YAML = """
test_cases:
  - case_id: TC001
    feature: 用户模块
    story: 登录
    request: {method: POST, url: /api/login}
    expected: {status_code: 200}
  - case_id: TC002
    feature: 订单模块
    story: 下单
    request: {method: GET, url: /api/orders}
    expected: {status_code: 200}
"""


@pytest.fixture
def data_file(tmp_path):
    path = tmp_path / "test_data.yaml"
    path.write_text(DATA_YAML, encoding="utf-8")
    return str(path)


class TestDataManager:
    def test_loads_all_cases(self, data_file):
        assert len(DataManager(data_file).cases) == 2

    def test_filter_by_feature(self, data_file):
        cases = DataManager(data_file).get_test_cases(feature="订单模块")
        assert [c["case_id"] for c in cases] == ["TC002"]

    def test_filter_by_feature_and_story(self, data_file):
        cases = DataManager(data_file).get_test_cases(feature="用户模块", story="登录")
        assert [c["case_id"] for c in cases] == ["TC001"]

    def test_filter_no_match_returns_empty(self, data_file):
        assert DataManager(data_file).get_test_cases(feature="不存在") == []

    def test_get_test_data_by_case_id(self, data_file):
        assert DataManager(data_file).get_test_data("TC001")["feature"] == "用户模块"

    def test_get_test_data_unknown_id_raises(self, data_file):
        with pytest.raises(ValueError):
            DataManager(data_file).get_test_data("TC999")

    def test_missing_case_id_raises(self, tmp_path):
        path = tmp_path / "bad.yaml"
        path.write_text("test_cases:\n  - request: {method: GET, url: /x}\n", encoding="utf-8")
        with pytest.raises(ValueError):
            DataManager(str(path))

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            DataManager(str(tmp_path / "no.yaml"))

    def test_duplicate_case_ids_reported(self, tmp_path):
        path = tmp_path / "duplicate.yaml"
        path.write_text(DATA_YAML.replace("TC002", "TC001"), encoding="utf-8")
        with pytest.raises(ValueError, match="case_id 重复"):
            DataManager(str(path))

    def test_reports_multiple_schema_errors_at_once(self, tmp_path):
        path = tmp_path / "invalid.yaml"
        path.write_text(
            "test_cases:\n"
            "  - case_id: TC001\n"
            "    request: {method: TRACE, url: ''}\n"
            "  - case_id: TC002\n"
            "    request: nope\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError) as exc_info:
            DataManager(str(path))
        message = str(exc_info.value)
        assert "request.method 无效" in message
        assert "request.url" in message
        assert message.count("expected") == 2

    def test_root_and_test_cases_types_are_validated(self, tmp_path):
        path = tmp_path / "invalid-root.yaml"
        path.write_text("- not-an-object\n", encoding="utf-8")
        with pytest.raises(ValueError, match="根节点必须是对象"):
            DataManager(str(path))

    def test_invalid_response_time_is_rejected(self, tmp_path):
        path = tmp_path / "invalid-time.yaml"
        path.write_text(
            "test_cases:\n"
            "  - case_id: TC001\n"
            "    request: {method: GET, url: /health}\n"
            "    expected: {status_code: 200}\n"
            "    validation: {response_time_ms: 0}\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="response_time_ms"):
            DataManager(str(path))
