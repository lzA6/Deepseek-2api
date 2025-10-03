# app/core/config.py

from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    """
    应用配置 - Deepseek-2api
    """
    # --- 服务监听端口 ---
    LISTEN_PORT: int = 8083

    # --- 应用元数据 ---
    APP_NAME: str = "Deepseek Local API"
    APP_VERSION: str = "1.0.0"
    DESCRIPTION: str = "一个支持粘性会话的高性能 Deepseek 网页版聊天本地代理。"

    # --- 认证与安全 ---
    API_MASTER_KEY: Optional[str] = None

    # --- 模型列表 (用户请求时使用) ---
    SUPPORTED_MODELS: List[str] = [
        "deepseek-chat",
        "deepseek-coder", # 备用，实际后端模型可能不支持
    ]

    # --- Deepseek 账号 ---
    # 这是处理所有请求的主力账号，必须填写
    DEEPSEEK_AUTHORIZATION_TOKEN: str = ""
    DEEPSEEK_COOKIE: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

settings = Settings()