import logging
import sys
from pathlib import Path


class Logger:
    """日志工具：统一日志格式，同时输出控制台与文件"""

    _loggers = {}

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        获取logger实例
        
        Args:
            name: logger名称
            
        Returns:
            Logger实例
        """
        if name not in cls._loggers:
            cls._loggers[name] = cls._create_logger(name)
        return cls._loggers[name]

    @classmethod
    def _create_logger(cls, name: str) -> logging.Logger:
        """创建logger"""
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)
        
        if not logger.handlers:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
            
            log_dir = Path(__file__).parent.parent / "logs"
            log_dir.mkdir(exist_ok=True)
            file_handler = logging.FileHandler(
                log_dir / "test.log",
                encoding="utf-8"
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        return logger
