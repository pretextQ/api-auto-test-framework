import allure
import pytest

from core.data_driver import DataDriver
from core.test_case_base import TestCaseBase


@allure.feature("商品模块")
class TestProduct(TestCaseBase):
    """商品模块:响应断言与落库断言双重校验"""

    @DataDriver.parametrize("config/test_data.yaml", feature="商品模块", story="库存管理")
    @pytest.mark.smoke
    def test_product_stock(self, api_client, db_helper, chain_context, case):
        """商品库存查询:接口返回与MySQL落库数据一致性校验"""
        self.run_data_driven_case(api_client, db_helper, chain_context, case)
