import re
import pytest
from data.data_manager import DataManager


class DataDriver:
    """数据驱动模块：把YAML中的用例数据转换为pytest参数"""

    @classmethod
    def parametrize(cls, data_file: str):
        """
        装饰器：从YAML读取全部用例并注入参数case
        
        Args:
            data_file: 数据文件路径
            
        用法：
            @DataDriver.parametrize("config/test_data.yaml")
            def test_login(self, case): ...
        """
        cases = DataManager(data_file).get_test_cases()
        return pytest.mark.parametrize(
            "case", cases,
            ids=[c["case_id"] for c in cases]
        )

    @staticmethod
    def render(value, context: dict):
        """
        递归渲染模板字符串，支持${key}与${context.key}
        
        Args:
            value: 待渲染的值
            context: 上下文字典
            
        Returns:
            渲染后的值
        """
        if isinstance(value, str):
            pattern = r'\$\{(\w+(?:\.\w+)*)\}'
            
            def replacer(match):
                key = match.group(1)
                if key.startswith("context."):
                    key = key[8:]
                return str(context.get(key, match.group(0)))
            
            return re.sub(pattern, replacer, value)
        elif isinstance(value, dict):
            return {k: DataDriver.render(v, context) for k, v in value.items()}
        elif isinstance(value, list):
            return [DataDriver.render(item, context) for item in value]
        return value
