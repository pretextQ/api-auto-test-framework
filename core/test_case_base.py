from utils.jsonpath_extractor import JsonPathExtractor
from utils.logger import Logger


class TestCaseBase:
    """断言助手基类：仅聚合断言，不含生命周期钩子"""

    def __init__(self):
        self.logger = Logger.get_logger(self.__class__.__name__)

    @staticmethod
    def assert_status_code(resp, expected: int = 200):
        """
        断言HTTP状态码
        
        Args:
            resp: 响应对象
            expected: 期望状态码
        """
        actual = resp.status_code
        if actual != expected:
            try:
                body = resp.json()
            except Exception:
                body = resp.text
            raise AssertionError(
                f"HTTP状态码不匹配: 期望 {expected}, 实际 {actual}\n响应体: {body}"
            )

    @staticmethod
    def assert_jsonpath(data, expr: str, expected) -> list:
        """
        JSONPath断言：提取结果与期望比对
        
        Args:
            data: 数据
            expr: JSONPath表达式
            expected: 期望值
            
        Returns:
            命中列表
        """
        results = JsonPathExtractor.extract(data, expr)
        
        if not results:
            raise AssertionError(f"JSONPath '{expr}' 未匹配到任何数据")
        
        if expected is not None and expected != "${TMP_TOKEN}":
            if results[0] != expected:
                raise AssertionError(
                    f"JSONPath '{expr}' 值不匹配: 期望 {expected}, 实际 {results[0]}"
                )
        
        return results

    @staticmethod
    def assert_database(db_helper, table: str, conditions: dict, expected: dict):
        """
        数据库校验：按条件查库并与期望逐字段比对
        
        Args:
            db_helper: 数据库助手实例
            table: 表名
            conditions: 查询条件
            expected: 期望数据
        """
        actual = db_helper.fetch_one(table, conditions)
        
        if actual is None:
            raise AssertionError(
                f"数据库查询无结果: 表 {table}, 条件 {conditions}"
            )
        
        for key, expected_value in expected.items():
            actual_value = actual.get(key)
            if actual_value != expected_value:
                raise AssertionError(
                    f"数据库字段不匹配: {key} 期望 {expected_value}, 实际 {actual_value}"
                )
