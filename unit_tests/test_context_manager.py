import pytest

from core.context_manager import TestContext
from utils.exceptions import ContextVariableError

pytestmark = pytest.mark.unit


@pytest.fixture
def context():
    ctx = TestContext()
    ctx.set("user_id", 1001)
    ctx.set("token", "abc123")
    ctx.set("order_id", "ORD-1")
    return ctx


class TestRender:
    """${key}占位符渲染"""

    def test_full_placeholder_keeps_original_type(self, context):
        """整串占位符渲染后保留原始类型"""
        assert context.render("${user_id}") == 1001

    def test_embedded_placeholder_converted_to_str(self, context):
        """嵌入字符串的占位符转为文本拼接"""
        assert context.render("前缀-${order_id}-后缀") == "前缀-ORD-1-后缀"

    def test_context_prefix_supported(self, context):
        """支持${context.key}写法"""
        assert context.render("${context.user_id}") == 1001

    def test_missing_placeholder_raises(self, context):
        """未命中的占位符快速失败"""
        with pytest.raises(ContextVariableError, match="missing"):
            context.render("${missing}")

    def test_dict_rendered_recursively(self, context):
        data = context.render({"a": "${user_id}", "b": ["${token}", "x"]})
        assert data == {"a": 1001, "b": ["abc123", "x"]}

    def test_list_rendered_recursively(self, context):
        assert context.render(["${user_id}", {"k": "${token}"}]) == [1001, {"k": "abc123"}]

    def test_non_string_value_returned_unchanged(self, context):
        assert context.render(123) == 123
        assert context.render(None) is None


class TestGetSet:
    def test_get_missing_key_returns_default(self, context):
        assert context.get("nope") is None
        assert context.get("nope", "dft") == "dft"

    def test_clear_empties_context(self, context):
        context.clear()
        assert context.get("user_id") is None
        with pytest.raises(ContextVariableError):
            context.render("${user_id}")
