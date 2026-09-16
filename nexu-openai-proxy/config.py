import os
from dotenv import load_dotenv

load_dotenv()

# Nexu API 配置
NEXU_API_BASE = os.getenv("NEXU_API_BASE", "https://link.nexu.io/v1")
NEXU_API_KEY = os.getenv("NEXU_API_KEY", "")

if not NEXU_API_KEY:
    raise RuntimeError("NEXU_API_KEY must be set in the environment or .env file")

# 代理服务器配置
PROXY_HOST = os.getenv("PROXY_HOST", "127.0.0.1")
PROXY_PORT = int(os.getenv("PROXY_PORT", "8866"))

# 可用模型列表
AVAILABLE_MODELS = [
    "deepseek-v3.2",
    "gemini-3-flash-preview",
    "gemini-3.1-flash-lite-preview",
    "glm-5",
    "glm-5-turbo",
    "gpt-5.4-mini",
    "kimi-k2.5",
    "mimo-v2-pro",
    "minimax-m2.7"
]
