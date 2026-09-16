# Nexu OpenAI Proxy

将 Nexu 自带的 AI 模型反向代理为 OpenAI 兼容 API，可接入 Cline 等插件并支持 Agent 功能（function calling）。

## 功能特性

- OpenAI 兼容的 API 接口
- 支持 function calling / tools 调用（Agent 功能）
- 支持 streaming 和非 streaming 响应
- 支持多种模型切换
- 可通过环境变量配置

## 快速开始

### Windows

双击 `start.bat` 或在命令行运行：

```cmd
start.bat
```

### Linux / Mac

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# 在 .env 中填入你自己的 NEXU_API_KEY
python main.py
```

启动后代理运行在 `http://127.0.0.1:8866`。

## 接入 Cline

1. 打开 Cline 设置
2. API Provider 选择 `OpenAI Compatible`
3. Base URL 填写 `http://127.0.0.1:8866/v1`
4. API Key 填写任意字符（如 `nexu-proxy`）
5. Model 填写以下任一模型名

## 可用模型

| 模型名称 | 说明 |
|---|---|
| gpt-5.4-mini | OpenAI GPT-5.4 Mini |
| deepseek-v3.2 | DeepSeek V3.2 |
| gemini-3-flash-preview | Gemini 3 Flash |
| glm-5 | GLM-5 |
| kimi-k2.5 | Kimi K2.5 |
| mimo-v2-pro | Mimo V2 Pro |
| minimax-m2.7 | MiniMax M2.7 |

## Agent 功能

代理完整支持 OpenAI 的 function calling 格式，Cline 中的工具调用会自动转发到 Nexu API 处理。

## API 端点

| 端点 | 说明 |
|---|---|
| GET /v1/models | 模型列表 |
| GET /v1/models/{id} | 模型详情 |
| POST /v1/chat/completions | 聊天补全 |
| GET /health | 健康检查 |

## 配置

复制 `.env.example` 为 `.env`，并填入自己的密钥：

```dotenv
NEXU_API_BASE=https://link.nexu.io/v1
NEXU_API_KEY=
PROXY_HOST=127.0.0.1
PROXY_PORT=8866
```

`.env` 已被 Git 忽略，不能提交真实密钥。
