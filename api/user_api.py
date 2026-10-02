from api.api_base import ApiBase


class UserApi(ApiBase):
    """用户模块API封装:负责鉴权前置与用户接口的流程编排"""

    def login(self, username: str, password: str) -> dict:
        """
        用户登录

        Args:
            username: 用户名
            password: 密码

        Returns:
            登录响应数据(token/user_id/username)
        """
        resp = self.post("/api/login", json={
            "username": username,
            "password": password
        })
        return self._check_response(resp)

    def get_profile(self, user_id: int) -> dict:
        """
        获取用户信息

        Args:
            user_id: 用户ID

        Returns:
            用户信息
        """
        resp = self.get(f"/api/users/{user_id}")
        return self._check_response(resp)
