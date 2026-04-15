# Nexu OpenAI Proxy

将Nexu自带的AI模型反向代理为OpenAI兼容API，可接入Cline等插件并支持Agent功能（function calling）。

## 功能特性

- OpenAI兼容的API接口
- 支持function calling / tools调用（Agent功能）
- 支持streaming和非streaming响应
- 支持多种模型切换
- 零配置开箱即用

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
python main.py
```

启动后代理运行在 `http://127.0.0.1:8866`

## 接入Cline

1. 打开Cline设置
2. API Provider 选择 `OpenAI Compatible`
3. Base URL 填写 `http://127.0.0.1:8866/v1`
4. API Key 填写任意字符（如 `nexu-proxy`）
5. Model 填写以下任一模型名

## 可用模型

| 模型名称 | 说明 |
|---------|------|
| gpt-5.4-mini | OpenAI GPT-5.4 Mini |
| deepseek-v3.2 | DeepSeek V3.2 |
| gemini-3-flash-preview | Gemini 3 Flash |
| glm-5 | GLM-5 |
| kimi-k2.5 | Kimi K2.5 |
| mimo-v2-pro | Mimo V2 Pro |
| minimax-m2.7 | MiniMax M2.7 |

## Agent功能

代理完整支持OpenAI的function calling格式，Cline中的工具调用会自动转发到Nexu API处理。

## API端点

| 端点 | 说明 |
|------|------|
| GET /v1/models | 模型列表 |
| GET /v1/models/{id} | 模型详情 |
| POST /v1/chat/completions | 聊天补全 |
| GET /health | 健康检查 |

## 配置

编辑 `.env` 文件：
```
NEXU_API_BASE=https://link.nexu.io/v1
NEXU_API_KEY=nxk_09fhi5fbdHzqcNgHloTOkeZnqs0ZGu_T-BKFbkSy8yM
PROXY_HOST=127.0.0.1
PROXY_PORT=8866
```
