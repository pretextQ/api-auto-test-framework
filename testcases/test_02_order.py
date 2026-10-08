import allure
import pytest

from core.data_driver import DataDriver
from core.test_case_base import TestCaseBase


@allure.feature("订单模块")
class TestOrder(TestCaseBase):
    """订单模块:依赖登录链路写入的user_id(见test_01_user.py)"""

    @DataDriver.parametrize("config/test_data.yaml", feature="订单模块", story="订单创建")
    @pytest.mark.smoke
    def test_create_order(self, auth_client, db_helper, chain_context, order_sandbox, case):
        """创建订单:请求体引用${context.user_id},创建后提取order_id"""
        if chain_context.get("user_id") is None:
            pytest.fail("链路上下文中无user_id,请先执行登录用例")
        self.run_data_driven_case(auth_client, db_helper, chain_context, case)

    @DataDriver.parametrize("config/test_data.yaml", feature="订单模块", story="订单查询")
    @pytest.mark.smoke
    def test_query_orders(self, auth_client, db_helper, chain_context, created_order, case):
        """查询订单列表:校验下单链路的落库结果"""
        if chain_context.get("user_id") is None:
            pytest.fail("链路上下文中无user_id,请先执行登录用例")
        response = self.run_data_driven_case(auth_client, db_helper, chain_context, case)
        order_ids = [item["order_id"] for item in response.json()["data"]["items"]]
        assert created_order["order_id"] in order_ids, "查询结果未包含本测试创建的订单"
