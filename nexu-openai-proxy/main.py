import os
import sys
import json
import time
import uuid
import signal
import subprocess
import threading
from typing import AsyncGenerator, Optional, List, Dict, Any, Union
from contextlib import asynccontextmanager

import httpx
import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

NEXU_API_BASE = os.getenv("NEXU_API_BASE", "https://link.nexu.io/v1")
NEXU_API_KEY = os.getenv("NEXU_API_KEY", "")
PROXY_HOST = os.getenv("PROXY_HOST", "127.0.0.1")
PROXY_PORT = int(os.getenv("PROXY_PORT", "8866"))

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

server_process = None
server_thread = None


class ChatMessage(BaseModel):
    role: str
    content: Optional[Union[str, List[Dict[str, Any]]]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 1.0
    top_p: Optional[float] = 1.0
    n: Optional[int] = 1
    stream: Optional[bool] = False
    stop: Optional[Union[str, List[str]]] = None
    max_tokens: Optional[int] = None
    presence_penalty: Optional[float] = 0
    frequency_penalty: Optional[float] = 0
    logit_bias: Optional[Dict[str, float]] = None
    user: Optional[str] = None
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    response_format: Optional[Dict[str, str]] = None

class ModelInfo(BaseModel):
    id: str
    object: str = "model"
    created: int = Field(default_factory=lambda: int(time.time()))
    owned_by: str = "nexu"

class ModelList(BaseModel):
    object: str = "list"
    data: List[ModelInfo]

http_client: Optional[httpx.AsyncClient] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global http_client
    http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(300.0, connect=30.0),
        follow_redirects=True
    )
    yield
    await http_client.aclose()

app = FastAPI(title="Nexu OpenAI Proxy", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {NEXU_API_KEY}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }

def convert_messages(messages: List[ChatMessage]) -> List[Dict[str, Any]]:
    result = []
    for msg in messages:
        item = {"role": msg.role}
        if msg.content is not None:
            item["content"] = msg.content
        if msg.tool_calls is not None:
            item["tool_calls"] = msg.tool_calls
        if msg.tool_call_id is not None:
            item["tool_call_id"] = msg.tool_call_id
        if msg.name is not None:
            item["name"] = msg.name
        result.append(item)
    return result

def convert_tools(tools: Optional[List[Dict[str, Any]]]) -> Optional[List[Dict[str, Any]]]:
    if not tools:
        return None
    return tools

def build_request_body(req: ChatCompletionRequest) -> Dict[str, Any]:
    body = {
        "model": req.model,
        "messages": convert_messages(req.messages),
        "stream": req.stream,
    }
    if req.temperature is not None:
        body["temperature"] = req.temperature
    if req.top_p is not None:
        body["top_p"] = req.top_p
    if req.max_tokens is not None:
        body["max_tokens"] = req.max_tokens
    if req.stop is not None:
        body["stop"] = req.stop
    if req.presence_penalty is not None:
        body["presence_penalty"] = req.presence_penalty
    if req.frequency_penalty is not None:
        body["frequency_penalty"] = req.frequency_penalty
    if req.response_format is not None:
        body["response_format"] = req.response_format
    if req.tools is not None:
        body["tools"] = convert_tools(req.tools)
    if req.tool_choice is not None:
        body["tool_choice"] = req.tool_choice
    return body

@app.get("/v1/models")
async def list_models():
    models = [ModelInfo(id=m) for m in AVAILABLE_MODELS]
    return ModelList(data=models)

@app.get("/v1/models/{model_id}")
async def get_model(model_id: str):
    if model_id not in AVAILABLE_MODELS:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
    return ModelInfo(id=model_id)

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest, raw_request: Request):
    if not http_client:
        raise HTTPException(status_code=500, detail="HTTP client not initialized")

    body = build_request_body(request)

    if request.stream:
        return StreamingResponse(
            stream_response(body),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    else:
        return await non_stream_response(body)

async def non_stream_response(body: Dict[str, Any]) -> JSONResponse:
    url = f"{NEXU_API_BASE}/chat/completions"
    try:
        resp = await http_client.post(url, json=body, headers=get_headers())
        resp.raise_for_status()
        data = resp.json()

        if "id" not in data:
            data["id"] = f"chatcmpl-{uuid.uuid4().hex[:24]}"
        if "object" not in data:
            data["object"] = "chat.completion"
        if "created" not in data:
            data["created"] = int(time.time())

        return JSONResponse(content=data)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def stream_response(body: Dict[str, Any]) -> AsyncGenerator[str, None]:
    url = f"{NEXU_API_BASE}/chat/completions"
    chat_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
    created = int(time.time())

    try:
        async with http_client.stream("POST", url, json=body, headers=get_headers()) as resp:
            if resp.status_code != 200:
                error_body = await resp.aread()
                error_msg = error_body.decode() if error_body else "Unknown error"
                yield f"data: {json.dumps({'error': {'message': error_msg, 'type': 'api_error'}})}\n\n"
                yield "data: [DONE]\n\n"
                return

            async for line in resp.aiter_lines():
                if not line:
                    continue
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        yield "data: [DONE]\n\n"
                        break
                    try:
                        chunk = json.loads(data_str)
                        if "id" not in chunk:
                            chunk["id"] = chat_id
                        if "object" not in chunk:
                            chunk["object"] = "chat.completion.chunk"
                        if "created" not in chunk:
                            chunk["created"] = created
                        yield f"data: {json.dumps(chunk)}\n\n"
                    except json.JSONDecodeError:
                        yield f"data: {data_str}\n\n"

    except Exception as e:
        error_chunk = {
            "id": chat_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": body.get("model", ""),
            "choices": [{
                "index": 0,
                "delta": {"content": f"\n[Error: {str(e)}]"},
                "finish_reason": "stop"
            }]
        }
        yield f"data: {json.dumps(error_chunk)}\n\n"
        yield "data: [DONE]\n\n"

@app.get("/health")
async def health():
    return {"status": "ok", "nexu_api_base": NEXU_API_BASE}


def run_server():
    import uvicorn
    uvicorn.run(app, host=PROXY_HOST, port=PROXY_PORT, log_level="warning")


def check_server_status() -> bool:
    try:
        resp = requests.get(f"http://{PROXY_HOST}:{PROXY_PORT}/health", timeout=3)
        return resp.status_code == 200
    except:
        return False


def check_api_key() -> bool:
    if not NEXU_API_KEY:
        return False
    try:
        resp = requests.get(
            f"{NEXU_API_BASE}/models",
            headers=get_headers(),
            timeout=10
        )
        return resp.status_code == 200
    except:
        return False


def test_model(model: str = "gpt-5.4-mini") -> dict:
    try:
        resp = requests.post(
            f"{NEXU_API_BASE}/chat/completions",
            headers=get_headers(),
            json={
                "model": model,
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 10
            },
            timeout=30
        )
        if resp.status_code == 200:
            data = resp.json()
            return {"success": True, "model": model, "response": data["choices"][0]["message"]["content"]}
        else:
            return {"success": False, "model": model, "error": f"HTTP {resp.status_code}", "detail": resp.text[:200]}
    except Exception as e:
        return {"success": False, "model": model, "error": str(e)}


def find_proxy_process() -> Optional[int]:
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True
        )
        for line in result.stdout.split("\n"):
            if f":{PROXY_PORT}" in line and "LISTENING" in line:
                parts = line.split()
                if len(parts) > 4:
                    return int(parts[-1])
    except:
        pass
    return None


def kill_proxy_process():
    pid = find_proxy_process()
    if pid:
        try:
            subprocess.run(f"taskkill /F /PID {pid}", shell=True, check=True)
            return True
        except:
            return False
    return False


def start_server():
    global server_process, server_thread
    if check_server_status():
        print(f"  [!] Server is already running on http://{PROXY_HOST}:{PROXY_PORT}")
        return
    
    print(f"  Starting server on http://{PROXY_HOST}:{PROXY_PORT}...")
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    time.sleep(2)
    if check_server_status():
        print(f"  [OK] Server started successfully!")
    else:
        print(f"  [X] Failed to start server")


def stop_server():
    if kill_proxy_process():
        print(f"  [OK] Server stopped")
    else:
        print(f"  [!] No running server found")


def show_status():
    print(f"\n{'='*50}")
    print(f"  Nexu OpenAI Proxy - Status")
    print(f"{'='*50}")
    print(f"  Proxy URL:  http://{PROXY_HOST}:{PROXY_PORT}")
    print(f"  Nexu API:   {NEXU_API_BASE}")
    
    running = check_server_status()
    print(f"  Status:     {'RUNNING' if running else 'STOPPED'}")
    
    api_ok = check_api_key()
    print(f"  API Key:    {'VALID' if api_ok else 'INVALID/MISSING'}")
    print(f"  Models:     {len(AVAILABLE_MODELS)} available")
    
    if running:
        print(f"\n  Available endpoints:")
        print(f"    - http://{PROXY_HOST}:{PROXY_PORT}/v1/models")
        print(f"    - http://{PROXY_HOST}:{PROXY_PORT}/v1/chat/completions")
        print(f"    - http://{PROXY_HOST}:{PROXY_PORT}/health")
    print(f"{'='*50}\n")


def main_menu():
    global server_process
    
    while True:
        print(f"\n{'='*50}")
        print(f"  Nexu OpenAI Proxy")
        print(f"{'='*50}")
        print(f"  1. Test Model Connection")
        print(f"  2. Check Status")
        print(f"  3. Start Server")
        print(f"  4. Stop Server")
        print(f"  5. Configuration")
        print(f"  0. Exit")
        print(f"{'='*50}")
        
        choice = input("  Select [0-5]: ").strip()
        
        if choice == "1":
            print("\n--- Test Model Connection ---")
            print(f"Available models:")
            for i, m in enumerate(AVAILABLE_MODELS):
                print(f"  {i+1}. {m}")
            try:
                idx = int(input(f"\nSelect model [1-{len(AVAILABLE_MODELS)}]: ").strip()) - 1
                if 0 <= idx < len(AVAILABLE_MODELS):
                    model = AVAILABLE_MODELS[idx]
                    print(f"\n  Testing {model}...")
                    result = test_model(model)
                    if result["success"]:
                        print(f"\n  [OK] Success!")
                        print(f"  Response: {result['response']}")
                    else:
                        print(f"\n  [X] Failed: {result['error']}")
                        if "detail" in result:
                            print(f"  Detail: {result['detail']}")
                else:
                    print("  Invalid selection")
            except ValueError:
                print("  Invalid input")
        
        elif choice == "2":
            show_status()
        
        elif choice == "3":
            start_server()
        
        elif choice == "4":
            stop_server()
        
        elif choice == "5":
            print(f"\n--- Configuration ---")
            print(f"  NEXU_API_BASE: {NEXU_API_BASE}")
            print(f"  NEXU_API_KEY:  {NEXU_API_KEY[:20]}..." if NEXU_API_KEY else "  NEXU_API_KEY:  (not set)")
            print(f"  PROXY_HOST:   {PROXY_HOST}")
            print(f"  PROXY_PORT:   {PROXY_PORT}")
            print(f"\n  Edit .env file to change settings")
        
        elif choice == "0":
            if check_server_status():
                print("\n  Stopping server before exit...")
                stop_server()
            print("\n  Goodbye!")
            break
        
        else:
            print("\n  Invalid option")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--server":
        run_server()
    else:
        main_menu()
