class BusinessError(Exception):
    """业务码非0异常:被测服务返回 code != 0 时抛出"""

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"业务错误 code={code}: {message}")


class ContextVariableError(ValueError):
    """请求模板引用了不存在的上下文变量。"""

    def __init__(self, key: str):
        self.key = key
        super().__init__(f"上下文变量未定义: {key}")
