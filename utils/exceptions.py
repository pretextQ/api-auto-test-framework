class BusinessError(Exception):
    """业务码非0异常:被测服务返回 code != 0 时抛出"""

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"业务错误 code={code}: {message}")
