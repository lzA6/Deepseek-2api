# app/providers/deepseek_provider.py (最终修正版)

import httpx
import json
import uuid
import time
import base64
import hashlib
import traceback
from typing import Dict, Any, AsyncGenerator, Union

from fastapi import Request
from fastapi.responses import StreamingResponse, JSONResponse
from loguru import logger

from app.providers.base import BaseProvider
from app.core.config import settings

class DeepseekProvider(BaseProvider):
    """
    Deepseek 网页版聊天提供商
    - 实现了对 chat.deepseek.com 网页版聊天接口的逆向工程。
    - 核心挑战: 实现了服务端的 Proof-of-Work (PoW) 算法 'DeepSeekHashV1'。
    - 实现了对 Deepseek 定制的 JSON Patch-like SSE 流的解析。
    """

    BASE_URL = "https://chat.deepseek.com/api/v0"
    MODEL_MAP = {
        "deepseek-chat": "deepseek-chat",
        "deepseek-coder": "deepseek-coder",
    }

    # --------------------------------------------------------------------------
    # 核心入口
    # --------------------------------------------------------------------------
    async def chat_completion(self, request_data: Dict[str, Any], original_request: Request) -> Union[StreamingResponse, JSONResponse]:
        try:
            logger.info("检测到 Deepseek 聊天任务，开始处理...")
            return await self._handle_stream_task(request_data)
        except Exception as e:
            logger.error(f"处理 Deepseek 任务时出错: {type(e).__name__}: {e}")
            traceback.print_exc()
            return JSONResponse(content={"error": {"message": f"处理任务时出错: {e}", "type": "provider_error"}}, status_code=500)

    # --------------------------------------------------------------------------
    # PoW (Proof-of-Work) 挑战求解器
    # --------------------------------------------------------------------------
    def _solve_pow(self, challenge: str, salt: str, difficulty: int) -> int:
        """
        在服务端复现 DeepSeekHashV1 算法
        """
        target = (1 << 256) / (difficulty + 1)
        nonce = 0
        start_time = time.time()
        logger.info(f"   [PoW] 开始计算挑战, 难度: {difficulty}...")
        
        while True:
            message = f"{challenge}{salt}{nonce}".encode('utf-8')
            h = hashlib.sha3_256(message).digest()
            hash_int = int.from_bytes(h, 'big')

            if hash_int < target:
                end_time = time.time()
                logger.success(f"   [PoW] 挑战成功! Nonce: {nonce}, 耗时: {(end_time - start_time)*1000:.2f}ms")
                return nonce
            nonce += 1

    async def _get_pow_response(self, client: httpx.AsyncClient) -> str:
        """
        获取 PoW 挑战并计算答案，返回 Base64 编码的响应头
        """
        challenge_payload = {"target_path": "/api/v0/chat/completion"}
        # 注意：获取挑战的请求也需要携带 headers
        response = await client.post(f"{self.BASE_URL}/chat/create_pow_challenge", json=challenge_payload, headers=self._prepare_headers())
        response.raise_for_status()
        challenge_data = response.json()["data"]["biz_data"]["challenge"]
        
        answer = self._solve_pow(
            challenge_data["challenge"],
            challenge_data["salt"],
            challenge_data["difficulty"]
        )
        
        pow_response_data = {
            "algorithm": challenge_data["algorithm"],
            "challenge": challenge_data["challenge"],
            "salt": challenge_data["salt"],
            "answer": answer,
            "signature": challenge_data["signature"],
            "target_path": challenge_data["target_path"],
        }
        
        return base64.b64encode(json.dumps(pow_response_data).encode('utf-8')).decode('utf-8')

    # --------------------------------------------------------------------------
    # 流式任务处理
    # --------------------------------------------------------------------------
    async def _handle_stream_task(self, request_data: Dict[str, Any]) -> StreamingResponse:
        headers = self._prepare_headers()
        model_name_for_client = request_data.get("model", "deepseek-chat")
        
        async with httpx.AsyncClient(timeout=120) as client:
            session_response = await client.post(f"{self.BASE_URL}/chat_session/create", headers=headers, json={})
            session_response.raise_for_status()
            chat_session_id = session_response.json()["data"]["biz_data"]["id"]
            logger.info(f"   [Session] 成功创建会话: {chat_session_id}")

            pow_response_header = await self._get_pow_response(client)
            headers["x-ds-pow-response"] = pow_response_header

            payload = self._prepare_payload(request_data, chat_session_id)
            
            logger.info(f"   [Request] 正在向模型 '{model_name_for_client}' 发送流式请求...")
            return StreamingResponse(
                self._stream_generator(f"{self.BASE_URL}/chat/completion", headers, payload, model_name_for_client),
                media_type="text/event-stream"
            )

    # --------------------------------------------------------------------------
    # 流式解析器 (保持不变)
    # --------------------------------------------------------------------------
    async def _stream_generator(self, url: str, headers: Dict, payload: Dict, model_name: str) -> AsyncGenerator[str, None]:
        chat_id = f"chatcmpl-{uuid.uuid4().hex}"
        is_first_chunk = True

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                async with client.stream("POST", url, headers=headers, json=payload) as response:
                    response.raise_for_status()
                    
                    async for line in response.aiter_lines():
                        if not line.startswith('data:'):
                            continue
                        
                        raw_data_str = line.strip()[len('data:'):]
                        if not raw_data_str:
                            continue
                        
                        try:
                            deepseek_data = json.loads(raw_data_str)
                            delta_content = self._parse_deepseek_chunk(deepseek_data)

                            if delta_content is None:
                                continue

                            if is_first_chunk and delta_content:
                                role_chunk = {
                                    "id": chat_id, "object": "chat.completion.chunk", "created": int(time.time()), "model": model_name,
                                    "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}]
                                }
                                yield f"data: {json.dumps(role_chunk, ensure_ascii=False)}\n\n"
                                is_first_chunk = False

                            if delta_content:
                                openai_chunk = {
                                    "id": chat_id, "object": "chat.completion.chunk", "created": int(time.time()), "model": model_name,
                                    "choices": [{"index": 0, "delta": {"content": delta_content}, "finish_reason": None}]
                                }
                                yield f"data: {json.dumps(openai_chunk, ensure_ascii=False)}\n\n"
                                
                        except json.JSONDecodeError:
                            logger.warning(f"   [Warning] JSON 解析失败: {raw_data_str}")
                            continue
        
        except Exception as e:
            logger.error(f"   [Error] 流式生成器发生错误: {e}")
            traceback.print_exc()
        
        finally:
            final_chunk = {
                "id": chat_id, "object": "chat.completion.chunk", "created": int(time.time()), "model": model_name,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]
            }
            yield f"data: {json.dumps(final_chunk, ensure_ascii=False)}\n\n"
            logger.info("   [Stream] 流式传输结束。")
            yield "data: [DONE]\n\n"

    def _parse_deepseek_chunk(self, chunk: Dict) -> Union[str, None]:
        path = chunk.get("p")
        op = chunk.get("o")
        value = chunk.get("v")

        if path and "response/fragments" in path and path.endswith("/content") and isinstance(value, str):
            return value

        if path == "response/fragments" and op == "APPEND" and isinstance(value, list):
            full_content = ""
            for fragment in value:
                if isinstance(fragment, dict) and fragment.get("type") == "RESPONSE":
                    content = fragment.get("content")
                    if isinstance(content, str):
                        full_content += content
            return full_content if full_content else None

        return None

    # --------------------------------------------------------------------------
    # 辅助函数 (已更新)
    # --------------------------------------------------------------------------
    def _prepare_headers(self) -> Dict[str, str]:
        token = settings.DEEPSEEK_AUTHORIZATION_TOKEN
        cookie = settings.DEEPSEEK_COOKIE
        
        if not token:
            raise ValueError("DEEPSEEK_AUTHORIZATION_TOKEN 未配置。")
        if not cookie:
            raise ValueError("DEEPSEEK_COOKIE 未配置。")
        
        return {
            'accept': '*/*',
            'authorization': token,
            'cookie': cookie,
            'content-type': 'application/json',
            'origin': 'https://chat.deepseek.com',
            'referer': 'https://chat.deepseek.com/',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
            'x-app-version': '20241129.1',
            'x-client-platform': 'web',
            'x-client-version': '1.4.0-fragments',
        }

    def _prepare_payload(self, request_data: Dict[str, Any], chat_session_id: str) -> Dict[str, Any]:
        user_message = request_data.get("messages", [{}])[-1].get("content", "你好")

        return {
            "chat_session_id": chat_session_id,
            "parent_message_id": None,
            "prompt": user_message,
            "ref_file_ids": [],
            "thinking_enabled": True,
            "search_enabled": True,
            "client_stream_id": f"{time.strftime('%Y%m%d')}-{uuid.uuid4().hex[:16]}"
        }