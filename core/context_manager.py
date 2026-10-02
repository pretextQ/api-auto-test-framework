import re
from utils.logger import Logger

# 占位符:支持 ${key} 与 ${context.key} 两种写法
PLACEHOLDER_PATTERN = re.compile(r"\$\{(\w+(?:\.\w+)*)\}")


class TestContext:
    """上下文管理模块:解决长链路接口间的动态参数依赖

    配合 YAML 用例中的 extract 段使用:用例执行后按 JSONPath 提取
    响应字段写入上下文,后续用例通过 ${key} 占位符引用。
    """

    __test__ = False  # 提示pytest:这是工具类而非测试类

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
        渲染含 ${key} 占位符的模板,支持字符串/字典/列表递归

        整串恰为一个占位符时保留原始类型(如 user_id 保持 int),
        嵌入字符串时转为 str;未命中的占位符原样保留。

        Args:
            template: 待渲染的模板

        Returns:
            渲染后的值
        """
        if isinstance(template, str):
            return self._render_str(template)
        if isinstance(template, dict):
            return {k: self.render(v) for k, v in template.items()}
        if isinstance(template, list):
            return [self.render(item) for item in template]
        return template

    def _render_str(self, text: str):
        match = PLACEHOLDER_PATTERN.fullmatch(text)
        if match:
            value = self._lookup(match.group(1))
            return value if value is not None else text

        def replacer(m):
            value = self._lookup(m.group(1))
            return str(value) if value is not None else m.group(0)

        return PLACEHOLDER_PATTERN.sub(replacer, text)

    def _lookup(self, key: str):
        if key.startswith("context."):
            key = key[len("context."):]
        return self._data.get(key)

    def clear(self):
        """清空上下文"""
        self._data.clear()
        self.logger.debug("上下文已清空")
