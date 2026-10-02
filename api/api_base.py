import requests

from api.http_client import HttpClient
from utils.exceptions import BusinessError


class ApiBase(HttpClient):
    """业务API基类:负责鉴权头注入与通用响应处理"""

    def __init__(self, base_url: str, token: str = None, **kwargs):
        """
        初始化业务API

        Args:
            base_url: 基础URL
            token: 认证token
            **kwargs: 其他HttpClient参数
        """
        super().__init__(base_url, **kwargs)
        if token:
            self.set_token(token)

    def set_token(self, token: str):
        """设置/更新鉴权头"""
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def _check_response(self, resp: requests.Response) -> dict:
        """
        统一处理业务码:非0抛出BusinessError,返回data段

        Args:
            resp: 响应对象

        Returns:
            响应数据的data字段
        """
        resp.raise_for_status()
        result = resp.json()

        if "code" in result and result["code"] != 0:
            raise BusinessError(result["code"], result.get("message", "未知业务错误"))

        return result.get("data", result)
