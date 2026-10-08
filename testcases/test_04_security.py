import allure
import pytest

from api.user_api import UserApi
from core.test_case_base import TestCaseBase


@allure.feature("安全边界")
class TestAuthorization(TestCaseBase):
    @pytest.mark.smoke
    def test_cannot_read_another_user_profile(self, auth_client):
        response = auth_client.get("/api/users/2")
        self.assert_status_code(response, 200)
        self.assert_business_code(response, 403)

    @pytest.mark.smoke
    def test_cannot_create_order_for_another_user(self, auth_client, db_helper):
        before = db_helper.execute_query(
            "SELECT COUNT(*) AS total FROM orders WHERE user_id = %s", (2,)
        )[0]["total"]

        response = auth_client.post("/api/orders", json={
            "user_id": 2,
            "product_id": 1002,
            "quantity": 1,
        })

        self.assert_status_code(response, 200)
        self.assert_business_code(response, 403)
        after = db_helper.execute_query(
            "SELECT COUNT(*) AS total FROM orders WHERE user_id = %s", (2,)
        )[0]["total"]
        assert after == before, "越权请求不应写入订单"

    @pytest.mark.smoke
    def test_tampered_token_is_rejected(self, config):
        client = UserApi(
            base_url=config.get("base_url"),
            timeout=config.get("timeout"),
            retries=config.get("retries"),
            sensitive_fields=config.get("reporting.sensitive_fields", []),
        )
        client.set_token("tampered.token.value")

        response = client.get("/api/users/1")

        self.assert_status_code(response, 200)
        self.assert_business_code(response, 401)
