from api.api_base import ApiBase


class UserApi(ApiBase):
    """用户模块API封装"""

    def login(self, username: str, password: str) -> dict:
        """
        用户登录
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            登录响应数据
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

    def update_profile(self, user_id: int, data: dict) -> dict:
        """
        更新用户信息
        
        Args:
            user_id: 用户ID
            data: 更新数据
            
        Returns:
            更新结果
        """
        resp = self.put(f"/api/users/{user_id}", json=data)
        return self._check_response(resp)
