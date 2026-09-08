from jsonpath_ng import parse
from utils.logger import Logger


class JsonPathExtractor:
    """JSONPath工具：基于jsonpath-ng提供数据提取与校验"""

    logger = Logger.get_logger("JsonPathExtractor")

    @staticmethod
    def extract(data, expr: str) -> list:
        """
        提取所有命中的值
        
        Args:
            data: 数据
            expr: JSONPath表达式
            
        Returns:
            命中值列表
        """
        try:
            jsonpath_expr = parse(expr)
            results = [match.value for match in jsonpath_expr.find(data)]
            JsonPathExtractor.logger.debug(f"JSONPath '{expr}' 提取到 {len(results)} 个结果")
            return results
        except Exception as e:
            JsonPathExtractor.logger.error(f"JSONPath解析失败: {expr}, 错误: {e}")
            return []

    @staticmethod
    def extract_first(data, expr: str, default=None):
        """
        提取第一个命中的值
        
        Args:
            data: 数据
            expr: JSONPath表达式
            default: 默认值
            
        Returns:
            第一个命中值或默认值
        """
        results = JsonPathExtractor.extract(data, expr)
        return results[0] if results else default

    @staticmethod
    def validate(data, expr: str, expected) -> bool:
        """
        断言表达式命中值与期望一致
        
        Args:
            data: 数据
            expr: JSONPath表达式
            expected: 期望值
            
        Returns:
            是否一致
        """
        actual = JsonPathExtractor.extract_first(data, expr)
        return actual == expected
