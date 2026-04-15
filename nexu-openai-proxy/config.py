import os
from dotenv import load_dotenv

load_dotenv()

# Nexu API配置
NEXU_API_BASE = os.getenv("NEXU_API_BASE", "https://link.nexu.io/v1")
NEXU_API_KEY = os.getenv("NEXU_API_KEY", "nxk_09fhi5fbdHzqcNgHloTOkeZnqs0ZGu_T-BKFbkSy8yM")

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
    "minimax-m2.7",
    "web-chatgpt",
    "web-claude",
    "web-bard"
]

# 网页AI配置
WEB_AI_TIMEOUT = int(os.getenv("WEB_AI_TIMEOUT", "60"))
