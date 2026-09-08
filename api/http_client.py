import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from utils.logger import Logger


class HttpClient:
    """HTTP客户端基类，封装Requests库，提供统一的HTTP请求能力"""

    def __init__(self, base_url: str, timeout: int = 30, retries: int = 3, headers: dict = None):
        """
        初始化HTTP客户端
        
        Args:
            base_url: 基础URL
            timeout: 请求超时时间（秒）
            retries: 重试次数
            headers: 默认请求头
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.logger = Logger.get_logger(self.__class__.__name__)
        
        self.session = requests.Session()
        
        if headers:
            self.session.headers.update(headers)
        
        retry_strategy = Retry(
            total=retries,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _build_url(self, url: str) -> str:
        """构建完整URL"""
        if url.startswith(("http://", "https://")):
            return url
        return f"{self.base_url}/{url.lstrip('/')}"

    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        统一请求入口
        
        Args:
            method: 请求方法
            url: 请求URL
            **kwargs: 其他请求参数
            
        Returns:
            Response对象
        """
        full_url = self._build_url(url)
        kwargs.setdefault("timeout", self.timeout)
        
        self.logger.info(f"[{method.upper()}] {full_url}")
        
        try:
            response = self.session.request(method, full_url, **kwargs)
            self.logger.info(f"响应状态码: {response.status_code}")
            return response
        except requests.RequestException as e:
            self.logger.error(f"请求异常: {e}")
            raise

    def get(self, url: str, params: dict = None, **kwargs) -> requests.Response:
        """发送GET请求"""
        return self.request("GET", url, params=params, **kwargs)

    def post(self, url: str, data=None, json=None, **kwargs) -> requests.Response:
        """发送POST请求"""
        return self.request("POST", url, data=data, json=json, **kwargs)

    def put(self, url: str, data=None, json=None, **kwargs) -> requests.Response:
        """发送PUT请求"""
        return self.request("PUT", url, data=data, json=json, **kwargs)

    def delete(self, url: str, **kwargs) -> requests.Response:
        """发送DELETE请求"""
        return self.request("DELETE", url, **kwargs)
