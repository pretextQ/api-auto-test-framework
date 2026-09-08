import allure
import pytest
from core.data_driver import DataDriver
from core.test_case_base import TestCaseBase


@allure.feature("订单模块")
class TestOrder(TestCaseBase):
    """订单测试"""

    @DataDriver.parametrize("config/test_data.yaml")
    @pytest.mark.smoke
    def test_create_order(self, api_client, test_context, case):
        """创建订单"""
        if case.get("feature") != "订单模块" or case.get("story") != "订单创建":
            pytest.skip("非当前模块用例")
        
        request = case["request"]
        expected = case["expected"]
        validation = case.get("validation", {})

        with allure.step("渲染请求数据"):
            rendered_data = test_context.render(request["data"])

        with allure.step("创建订单"):
            resp = api_client.post(request["url"], json=rendered_data)

        with allure.step("校验HTTP状态码"):
            self.assert_status_code(resp, expected["status_code"])

        if "jsonpath" in validation:
            with allure.step("校验响应数据"):
                jp = validation["jsonpath"]
                results = self.assert_jsonpath(resp.json(), jp["expr"], jp.get("value"))
                if results and jp["expr"] == "$.data.order_id":
                    test_context.set("order_id", results[0])

    @DataDriver.parametrize("config/test_data.yaml")
    @pytest.mark.smoke
    def test_query_orders(self, api_client, test_context, case):
        """查询订单列表"""
        if case.get("feature") != "订单模块" or case.get("story") != "订单查询":
            pytest.skip("非当前模块用例")
        
        request = case["request"]
        expected = case["expected"]
        validation = case.get("validation", {})

        with allure.step("渲染请求参数"):
            params = test_context.render(request.get("params", {}))

        with allure.step("查询订单列表"):
            resp = api_client.get(request["url"], params=params)

        with allure.step("校验HTTP状态码"):
            self.assert_status_code(resp, expected["status_code"])

        if "jsonpath" in validation:
            with allure.step("校验响应数据"):
                jp = validation["jsonpath"]
                self.assert_jsonpath(resp.json(), jp["expr"], jp.get("value"))
