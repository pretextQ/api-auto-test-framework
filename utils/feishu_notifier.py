import time
import hmac
import hashlib
import base64
import requests
from utils.logger import Logger


class FeishuNotifier:
    """飞书通知模块：把测试执行结果推送到飞书群机器人"""

    def __init__(self, webhook_url: str, secret: str = None):
        """
        初始化飞书通知器
        
        Args:
            webhook_url: Webhook地址
            secret: 签名密钥（可选）
        """
        self.webhook_url = webhook_url
        self.secret = secret
        self.logger = Logger.get_logger(self.__class__.__name__)

    def _generate_sign(self) -> tuple:
        """生成签名"""
        if not self.secret:
            return None, None
        
        timestamp = str(int(time.time()))
        string_to_sign = f"{timestamp}\n{self.secret}"
        hmac_code = hmac.new(
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256
        ).digest()
        sign = base64.b64encode(hmac_code).decode("utf-8")
        return timestamp, sign

    def send_test_result(self, total: int, passed: int, failed: int,
                         skipped: int, duration: float = None, failures: list = None):
        """
        发送测试结果
        
        Args:
            total: 总用例数
            passed: 通过数
            failed: 失败数
            skipped: 跳过数
            duration: 执行时长（秒）
            failures: 失败用例列表
        """
        status = "✅ 测试通过" if failed == 0 else "❌ 测试失败"
        
        content = f"""
**测试执行结果**
状态: {status}
总计: {total} | 通过: {passed} | 失败: {failed} | 跳过: {skipped}
"""
        if duration:
            content += f"耗时: {duration:.2f}秒\n"
        
        if failures:
            content += "\n**失败用例:**\n"
            for failure in failures[:5]:
                content += f"- {failure}\n"
            if len(failures) > 5:
                content += f"... 等 {len(failures) - 5} 个\n"
        
        self._send_message(content)

    def _send_message(self, content: str):
        """
        发送消息
        
        Args:
            content: 消息内容
        """
        timestamp, sign = self._generate_sign()
        
        payload = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": "自动化测试报告"
                    },
                    "template": "blue"
                },
                "elements": [
                    {
                        "tag": "markdown",
                        "content": content
                    }
                ]
            }
        }
        
        if timestamp and sign:
            payload["timestamp"] = timestamp
            payload["sign"] = sign
        
        try:
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            if result.get("code") == 0:
                self.logger.info("飞书通知发送成功")
            else:
                self.logger.error(f"飞书通知发送失败: {result}")
        except Exception as e:
            self.logger.error(f"飞书通知发送异常: {e}")
