import pytest
from data.data_manager import DataManager


class DataDriver:
    """数据驱动模块:从YAML按模块加载用例并转换为pytest参数"""

    @classmethod
    def parametrize(cls, data_file: str, feature: str = None, story: str = None):
        """
        装饰器:从YAML加载用例(可按 feature/story 过滤)并注入参数 case

        过滤发生在用例收集阶段,而非运行时 skip,
        保证每条测试方法只挂载属于自己的用例数据。

        Args:
            data_file: 数据文件路径
            feature: 按模块过滤,为空时不过滤
            story: 按故事过滤,为空时不过滤

        用法:
            @DataDriver.parametrize("config/test_data.yaml", feature="用户模块")
            def test_login(self, case): ...
        """
        cases = DataManager(data_file).get_test_cases(feature=feature, story=story)
        return pytest.mark.parametrize(
            "case", cases,
            ids=[c["case_id"] for c in cases]
        )
