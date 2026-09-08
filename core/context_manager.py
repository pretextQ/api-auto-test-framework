import re
from utils.logger import Logger


class TestContext:
    """上下文管理模块：解决长链路接口间的动态参数依赖"""

    def __init__(self):
        self.logger = Logger.get_logger(self.__class__.__name__)
        self._data = {}

    def set(self, key: str, value):
        """
        写入上下文
        
        Args:
            key: 键名
            value: 值
        """
        self._data[key] = value
        self.logger.debug(f"上下文写入: {key} = {value}")

    def get(self, key: str, default=None):
        """
        读取上下文
        
        Args:
            key: 键名
            default: 默认值
            
        Returns:
            上下文值
        """
        return self._data.get(key, default)

    def render(self, template):
        """
        渲染含${key}的模板
        
        Args:
            template: 模板字符串或字典
            
        Returns:
            渲染后的值
        """
        if isinstance(template, str):
            pattern = r'\$\{(\w+)\}'
            
            def replacer(match):
                key = match.group(1)
                value = self._data.get(key)
                if value is not None:
                    return str(value)
                return match.group(0)
            
            return re.sub(pattern, replacer, template)
        elif isinstance(template, dict):
            return {k: self.render(v) for k, v in template.items()}
        elif isinstance(template, list):
            return [self.render(item) for item in template]
        return template

    def clear(self):
        """清空上下文"""
        self._data.clear()
        self.logger.debug("上下文已清空")
