import http.server
import socketserver
import json
import asyncio
from web_ai import get_web_ai_response

PORT = 8866

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())
        elif self.path == "/v1/models":
            models = [
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
            model_list = [{
                "id": m,
                "object": "model",
                "created": 1677610602,
                "owned_by": "nexu"
            } for m in models]
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"object": "list", "data": model_list}).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        if self.path == "/v1/chat/completions":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data)
            
            model = request_data.get("model")
            messages = request_data.get("messages", [])
            stream = request_data.get("stream", False)
            
            if model and model.startswith("web-"):
                if stream:
                    self.send_response(200)
                    self.send_header("Content-type", "text/event-stream")
                    self.send_header("Cache-Control", "no-cache")
                    self.send_header("Connection", "keep-alive")
                    self.end_headers()
                    
                    # 异步处理流式响应
                    async def handle_stream():
                        async for chunk in get_web_ai_response(model, messages, stream):
                            if chunk == "[DONE]":
                                self.wfile.write(b"data: [DONE]\n\n")
                            else:
                                self.wfile.write(f"data: {chunk}\n\n".encode())
                    
                    asyncio.run(handle_stream())
                else:
                    # 处理非流式响应
                    chunks = []
                    async def handle_non_stream():
                        async for chunk in get_web_ai_response(model, messages, False):
                            if chunk != "[DONE]":
                                chunks.append(chunk)
                    
                    asyncio.run(handle_non_stream())
                    
                    if chunks:
                        try:
                            last_chunk = json.loads(chunks[-1])
                            if "choices" in last_chunk:
                                complete_response = {
                                    "id": last_chunk.get("id"),
                                    "object": "chat.completion",
                                    "created": last_chunk.get("created"),
                                    "model": model,
                                    "choices": last_chunk["choices"],
                                    "usage": {
                                        "prompt_tokens": 0,
                                        "completion_tokens": 0,
                                        "total_tokens": 0
                                    }
                                }
                                self.send_response(200)
                                self.send_header("Content-type", "application/json")
                                self.end_headers()
                                self.wfile.write(json.dumps(complete_response).encode())
                                return
                        except Exception as e:
                            pass
                    
                    self.send_response(500)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": {"message": "No response from web AI", "type": "api_error"}}).encode())
            else:
                self.send_response(400)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": {"message": "Model not supported", "type": "invalid_model"}}).encode())
        else:
            self.send_response(404)
            self.end_headers()

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"Server running at http://localhost:{PORT}")
    httpd.serve_forever()
