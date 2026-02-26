"""
Feishu Logging Configuration

配置 Feishu 相关日志输出到独立文件。
"""

import logging
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime

from mini_agent.config import LOG_DIR


def setup_feishu_logging(log_level: int = logging.INFO) -> logging.Logger:
    """
    配置 Feishu 日志到独立文件。

    Args:
        log_level: 日志级别

    Returns:
        配置好的 logger
    """
    # 创建日志目录
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Feishu 日志文件
    feishu_log_file = LOG_DIR / "feishu.log"

    # 创建 logger
    logger = logging.getLogger("mini_agent.feishu")
    logger.setLevel(log_level)

    # 避免重复添加 handler
    if logger.handlers:
        return logger

    # 文件 Handler - 轮转日志 (10MB per file, 保留 5 个)
    file_handler = RotatingFileHandler(
        feishu_log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)

    # 控制台 Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)  # 控制台只显示 warning 及以上

    # 格式化
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # 添加 handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.info(f"Feishu logging initialized: {feishu_log_file.absolute()}")
    return logger


def get_feishu_logger() -> logging.Logger:
    """
    获取 Feishu logger。

    Returns:
        Feishu logger instance
    """
    logger = logging.getLogger("mini_agent.feishu")

    # 如果没有 handler，进行初始化
    if not logger.handlers:
        try:
            setup_feishu_logging()
        except Exception:
            pass  # 忽略初始化错误

    return logger
