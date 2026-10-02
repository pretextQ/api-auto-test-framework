import pytest

from data.data_manager import DataManager

pytestmark = pytest.mark.unit

DATA_YAML = """
test_cases:
  - case_id: TC001
    feature: 用户模块
    story: 登录
    request: {method: POST, url: /api/login}
  - case_id: TC002
    feature: 订单模块
    story: 下单
    request: {method: GET, url: /api/orders}
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
