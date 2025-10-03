# main.py (v8.3 终极兼容版)

import time
import sys
import json
import uuid
import traceback
# 👇 关键修正 1: 导入 Callable 和 Awaitable
from typing import Optional, List, Dict, Any, Callable, Awaitable

from fastapi import FastAPI, Request, HTTPException, Depends, Header
# 👇 关键修正 2: 导入 Response
from starlette.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger

from app.core.config import settings
from app.providers.deepseek_provider import DeepseekProvider

# --- 配置 Loguru (保持不变) ---
logger.remove()
logger.add(
    sys.stdout,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
           "<level>{level: <8}</level> | "
           "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    colorize=True,
    serialize=False
)

# --- 创建 FastAPI 应用 (保持不变) ---
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=settings.DESCRIPTION
)

# 实例化 Provider
provider = DeepseekProvider()


# --- 高级日志中间件 (签名已修正) ---
class LoggingMiddleware(BaseHTTPMiddleware):
    # 👇 关键修正 3: 使用标准的 Callable[[Request], Awaitable[Response]] 类型
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        request_id = str(uuid.uuid4())
        start_time = time.time()

        body = await request.body()
        
        model_name = "N/A"
        if "/v1/chat/completions" in request.url.path and body:
            try:
                json_body = json.loads(body)
                model_name = json_body.get("model", "N/A")
            except json.JSONDecodeError:
                pass

        logger.info(f"--> [{request.client.host}] Request ID: {request_id} | {request.method} {request.url.path} | Model: {model_name}")

        response = await call_next(request)
        
        process_time = (time.time() - start_time) * 1000
        formatted_process_time = f"{process_time:.2f}ms"
        
        if response.status_code >= 500:
            logger.error(f"<-- [{request.client.host}] Request ID: {request_id} | Finished in {formatted_process_time} with status {response.status_code}")
        elif response.status_code >= 400:
            logger.warning(f"<-- [{request.client.host}] Request ID: {request_id} | Finished in {formatted_process_time} with status {response.status_code}")
        else:
            logger.success(f"<-- [{request.client.host}] Request ID: {request_id} | Finished in {formatted_process_time} with status {response.status_code}")

        return response

app.add_middleware(LoggingMiddleware)


# --- 认证依赖项 (保持不变) ---
async def verify_api_key(authorization: Optional[str] = Header(None)):
    if not settings.API_MASTER_KEY:
        logger.warning("API_MASTER_KEY 未配置，服务将对所有请求开放！")
        return
    if authorization is None:
        raise HTTPException(status_code=401, detail="Unauthorized: Missing Authorization header.")
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer": raise ValueError("Invalid scheme")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid authentication scheme. Use 'Bearer <your_api_key>'.")
    if token != settings.API_MASTER_KEY:
        raise HTTPException(status_code=403, detail="Forbidden: Invalid API Key.")


# --- API 路由 (保持不变) ---

@app.post("/v1/chat/completions", dependencies=[Depends(verify_api_key)])
async def chat_completions(request: Request):
    try:
        request_data = await request.json()
        return await provider.chat_completion(request_data, request)
    except Exception as e:
        logger.error(f"在 chat_completions 路由中发生严重错误: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"内部服务器错误: {str(e)}")


@app.get("/v1/models", dependencies=[Depends(verify_api_key)])
async def list_models():
    model_names: List[str] = settings.SUPPORTED_MODELS
    model_data: List[Dict[str, Any]] = []
    for name in model_names:
        model_data.append({
            "id": name,
            "object": "model",
            "created": int(time.time()),
            "owned_by": "system"
        })
    return {"object": "list", "data": model_data}


@app.get("/")
def root():
    return {"message": f"Welcome to {settings.APP_NAME}", "version": settings.APP_VERSION}