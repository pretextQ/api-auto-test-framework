import allure
import pytest

from core.data_driver import DataDriver
from core.test_case_base import TestCaseBase
from utils.reporter import Reporter


@allure.feature("用户模块")
class TestUserLogin(TestCaseBase):
    """登录接口:一条方法挂载成功/密码错误/账号禁用三条数据"""

    @DataDriver.parametrize("config/test_data.yaml", feature="用户模块", story="用户登录")
    @pytest.mark.smoke
    def test_login(self, api_client, db_helper, chain_context, case):
        """登录接口数据驱动用例,成功后提取token/user_id写入链路上下文"""
        self.run_data_driven_case(api_client, db_helper, chain_context, case)


@allure.feature("用户模块")
class TestUserProfile(TestCaseBase):
    """用户信息:API对象层驱动,演示前置鉴权与链路参数复用"""

    @pytest.mark.smoke
    def test_get_profile(self, auth_client, chain_context):
        """获取当前链路用户的信息"""
        user_id = chain_context.get("user_id")
        if user_id is None:
            pytest.fail("链路上下文中无user_id,请先执行登录用例")

        with Reporter.step(f"获取用户信息 user_id={user_id}"):
            profile = auth_client.get_profile(user_id)

        with Reporter.step("校验用户信息"):
            Reporter.attach_json("用户信息", profile)
            self.assert_jsonpath(profile, "$.username", "testuser")
            self.assert_jsonpath(profile, "$.user_id", user_id)
            self.assert_jsonpath(profile, "$.status", "active")
