import json

import allure

from utils.jsonpath_extractor import JsonPathExtractor
from utils.sanitizer import sanitize_data


class TestCaseBase:
    """测试基类:统一断言助手与数据驱动用例执行流程

    注意:pytest 不收集定义了 __init__ 的测试类,且会被子类继承,
    因此本基类只提供静态方法,不要在其中定义 __init__。
    """

    def run_data_driven_case(self, api_client, db_helper, context, case: dict):
        """
        数据驱动用例的统一执行流程:渲染 -> 发送 -> 多类断言 -> 提取上下文

        Args:
            api_client: HttpClient实例(按需传未鉴权或已鉴权对象)
            db_helper: DatabaseHelper实例
            context: TestContext实例
            case: YAML用例数据

        Returns:
            Response对象
        """
        resp = self.perform_request(api_client, case["request"], context)

        expected = case["expected"]
        with allure.step("校验HTTP状态码"):
            self.assert_status_code(resp, expected["status_code"])

        if "business_code" in expected:
            with allure.step("校验业务码"):
                self.assert_business_code(resp, expected["business_code"])

        validation = case.get("validation", {})
        jsonpath_specs = validation.get("jsonpath")
        if jsonpath_specs:
            if isinstance(jsonpath_specs, dict):
                jsonpath_specs = [jsonpath_specs]
            for jp in jsonpath_specs:
                with allure.step(f"校验响应数据: {jp['expr']}"):
                    self.assert_jsonpath(resp.json(), jp["expr"], jp.get("value"))

        if "response_time_ms" in validation:
            with allure.step("校验响应时间"):
                self.assert_response_time(resp, validation["response_time_ms"])

        if resp.ok and expected.get("business_code", 0) == 0:
            with allure.step("提取链路参数写入上下文"):
                self.extract_response(resp.json(), case.get("extract"), context)

        if "database" in validation:
            with allure.step("校验数据库落库"):
                db = validation["database"]
                conditions = context.render(db["conditions"]) if context else db["conditions"]
                self.assert_database(db_helper, db["table"], conditions, db["expected"])

        return resp

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
    def assert_business_code(resp, expected: int):
        """
        断言业务码:被测服务统一响应包中的 code 字段

        Args:
            resp: 响应对象
            expected: 期望业务码,0表示成功
        """
        result = resp.json()
        actual = result.get("code")
        if actual != expected:
            raise AssertionError(
                f"业务码不匹配: 期望 {expected}, 实际 {actual}, "
                f"message: {result.get('message')}"
            )

    @staticmethod
    def assert_jsonpath(data, expr: str, expected=None) -> list:
        """
        JSONPath断言:提取结果与期望比对

        expected 为 None 时仅校验字段存在,不做值比对。

        Args:
            data: 数据
            expr: JSONPath表达式
            expected: 期望值,None表示仅校验存在

        Returns:
            命中列表
        """
        results = JsonPathExtractor.extract(data, expr)

        if not results:
            raise AssertionError(f"JSONPath '{expr}' 未匹配到任何数据")

        if expected is not None and results[0] != expected:
            raise AssertionError(
                f"JSONPath '{expr}' 值不匹配: 期望 {expected}, 实际 {results[0]}"
            )

        return results

    @staticmethod
    def assert_database(db_helper, table: str, conditions: dict, expected: dict):
        """
        数据库校验:按条件查库并与期望逐字段比对

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

    @staticmethod
    def assert_response_time(resp, expected_ms: float):
        """断言请求耗时不超过指定毫秒数。"""
        actual_ms = resp.elapsed.total_seconds() * 1000
        if actual_ms > expected_ms:
            raise AssertionError(
                f"响应时间超限: 期望不超过 {expected_ms}ms, 实际 {actual_ms:.2f}ms"
            )

    @staticmethod
    def extract_response(resp_json, extract_spec: dict, context):
        """
        按用例的 extract 段提取响应字段写入上下文

        Args:
            resp_json: 响应JSON
            extract_spec: 提取配置,形如 {"user_id": "$.data.user_id"}
            context: TestContext实例
        """
        if not extract_spec:
            return
        for key, expr in extract_spec.items():
            value = JsonPathExtractor.extract_first(resp_json, expr)
            if value is not None:
                context.set(key, value)

    @staticmethod
    def perform_request(api_client, request: dict, context=None):
        """
        统一请求入口:渲染占位符 -> 发送 -> Allure附件化请求与响应

        Args:
            api_client: HttpClient实例
            request: 用例request段,形如 {"method": "POST", "url": ..., "data": ..., "params": ...}
            context: TestContext实例,可为空

        Returns:
            Response对象
        """
        def render(value):
            return context.render(value) if context else value

        method = request["method"].upper()
        url = render(request["url"])
        kwargs = {}
        if request.get("data") is not None:
            kwargs["json"] = render(request["data"])
        if request.get("params") is not None:
            kwargs["params"] = render(request["params"])
        if request.get("headers") is not None:
            kwargs["headers"] = render(request["headers"])

        with allure.step(f"{method} {url}"):
            headers = dict(api_client.session.headers)
            headers.update(kwargs.get("headers", {}))
            shown = {
                "method": method,
                "url": url,
                "headers": headers,
            }
            if "json" in kwargs:
                shown["data"] = kwargs["json"]
            if "params" in kwargs:
                shown["params"] = kwargs["params"]
            sensitive_fields = getattr(api_client, "sensitive_fields", ())
            allure.attach(
                json.dumps(
                    sanitize_data(shown, sensitive_fields),
                    ensure_ascii=False, indent=2, default=str
                ),
                name="请求", attachment_type=allure.attachment_type.JSON
            )
            resp = api_client.request(method, url, **kwargs)
            try:
                body = resp.json()
            except Exception:
                body = resp.text
            allure.attach(
                json.dumps(sanitize_data(
                    {"status_code": resp.status_code, "body": body},
                    sensitive_fields
                ),
                           ensure_ascii=False, indent=2, default=str),
                name="响应", attachment_type=allure.attachment_type.JSON
            )
        return resp
