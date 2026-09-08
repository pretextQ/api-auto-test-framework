import allure
import pytest
from core.data_driver import DataDriver
from core.test_case_base import TestCaseBase


@allure.feature("用户模块")
class TestUserLogin(TestCaseBase):
    """用户登录测试"""

    @DataDriver.parametrize("config/test_data.yaml")
    @pytest.mark.smoke
    def test_login(self, api_client, db_helper, case):
        """YAML数据驱动：一条方法 = N条用例"""
        if case.get("feature") != "用户模块" or case.get("story") != "用户登录":
            pytest.skip("非当前模块用例")
        
        request = case["request"]
        expected = case["expected"]
        validation = case.get("validation", {})

        with allure.step("发送登录请求"):
            resp = api_client.post(request["url"], json=request["data"])

        with allure.step("校验HTTP状态码"):
            self.assert_status_code(resp, expected["status_code"])

        if "jsonpath" in validation:
            with allure.step("校验响应数据"):
                jp = validation["jsonpath"]
                self.assert_jsonpath(resp.json(), jp["expr"], jp.get("value"))

        if "database" in validation:
            with allure.step("校验数据库落库"):
                db = validation["database"]
                self.assert_database(db_helper, db["table"], db["conditions"], db["expected"])


@allure.feature("用户模块")
class TestUserProfile(TestCaseBase):
    """用户信息测试"""

    @DataDriver.parametrize("config/test_data.yaml")
    @pytest.mark.smoke
    def test_get_profile(self, api_client, case):
        """获取用户信息"""
        if case.get("feature") != "用户模块" or case.get("story") != "用户信息":
            pytest.skip("非当前模块用例")
        
        request = case["request"]
        expected = case["expected"]
        validation = case.get("validation", {})

        with allure.step("获取用户信息"):
            resp = api_client.get(request["url"])

        with allure.step("校验HTTP状态码"):
            self.assert_status_code(resp, expected["status_code"])

        if "jsonpath" in validation:
            with allure.step("校验响应数据"):
                jp = validation["jsonpath"]
                self.assert_jsonpath(resp.json(), jp["expr"], jp.get("value"))
