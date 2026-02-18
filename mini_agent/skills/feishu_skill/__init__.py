"""
Feishu Skill - 长连接消息平台实现

使用飞书 SDK 实现与飞书消息服务的 WebSocket 长连接。
充分利用 SDK 功能：消息收发、回复、读取、删除、表情反应、文件上传。
"""

import asyncio
import json
import logging
import threading
from typing import Optional, Callable, Awaitable
from queue import Queue

from lark_oapi import im
from lark_oapi.ws.client import Client, EventDispatcherHandler
from lark_oapi.core.enum import LogLevel
from lark_oapi.core.model import Config
from lark_oapi.client import ImService
from lark_oapi.api.im.v1.model import P2ImMessageReceiveV1, P2ImMessageReceiveV1Data, Emoji

from mini_agent.long_connection.base import (
    LongConnectionPlatform,
    ConnectionState,
    PlatformMessage,
)
from mini_agent.skills.feishu_skill.config import FeishuConfig
from mini_agent.skills.feishu_skill.session_manager import SessionManager
from mini_agent.skills.feishu_skill.logging_config import get_feishu_logger

logger = get_feishu_logger()


class FeishuSkill(LongConnectionPlatform):
    """
    飞书 Skill - 实现与飞书的长连接集成。

    功能:
    - WebSocket 长连接保持 (SDK)
    - 多用户会话隔离
    - 自动重连 (SDK)
    - 消息收发 (SDK)
    - 消息回复/读取/删除 (SDK)
    - 表情反应 (SDK)
    - 文件上传 (SDK)
    """

    def __init__(self, config: FeishuConfig):
        """
        初始化 Feishu Skill。

        Args:
            config: FeishuConfig 配置实例
        """
        super().__init__(platform_id="feishu")
        self.config = config

        # IM Client for API calls (消息发送/回复/读取/删除等)
        self._im_config = Config()
        self._im_config.app_id = config.app_id
        self._im_config.app_secret = config.app_secret
        self._im_service = ImService(self._im_config)

        # WebSocket Client for receiving events
        self._ws_client: Optional[Client] = None

        # 会话管理器
        self._session_manager: Optional[SessionManager] = None

        # Agent 回调
        self._agent_callback: Optional[Callable[[str, str], Awaitable[str]]] = None

        # 消息队列
        self._message_queue: Queue = Queue()

        # 线程
        self._ws_thread: Optional[threading.Thread] = None
        self._ws_thread_running = threading.Event()
        self._running = False

    @property
    def is_enabled(self) -> bool:
        """检查 Skill 是否启用"""
        return self.config.enabled

    @property
    def session_count(self) -> int:
        """获取当前会话数量"""
        if self._session_manager:
            return self._session_manager.session_count
        return 0

    def set_agent_callback(
        self, callback: Callable[[str, str], Awaitable[str]]
    ) -> None:
        """设置 Agent 回调函数。"""
        self._agent_callback = callback

    def _ws_client_thread(self) -> None:
        """在独立线程中运行飞书 WebSocket 客户端。"""
        try:
            # 创建事件处理器（SDK 自动处理 verification token）
            handler_builder = EventDispatcherHandler.builder(
                self.config.encrypt_key or ""
            )

            # 注册消息接收事件处理
            handler_builder.register_p2_im_message_receive_v1(self._handle_im_message)

            # 构建处理器
            event_handler = handler_builder.build()

            # 创建 WebSocket 客户端
            self._ws_client = Client(
                app_id=self.config.app_id,
                app_secret=self.config.app_secret,
                log_level=LogLevel.INFO,
                event_handler=event_handler,
                auto_reconnect=True,
            )

            logger.info("FeishuSkill: [THREAD] Starting WebSocket client...")
            self._ws_thread_running.set()
            self._ws_client.start()

        except Exception as e:
            logger.error(f"FeishuSkill: [THREAD] Error: {e}")
        finally:
            self._ws_thread_running.clear()
            logger.info("FeishuSkill: [THREAD] Exited")

    async def connect(self) -> None:
        """建立与飞书的 WebSocket 长连接。"""
        if not self.config.is_valid():
            logger.error("FeishuSkill: [CONFIG_ERROR] 配置无效")
            self._set_state(ConnectionState.ERROR)
            raise RuntimeError("Feishu Skill 配置无效")

        app_id_preview = self.config.app_id[:10] + "..." if self.config.app_id and len(self.config.app_id) > 10 else self.config.app_id
        logger.info(f"FeishuSkill: [CONNECT_START] app_id={app_id_preview}")
        self._set_state(ConnectionState.CONNECTING)

        try:
            # 初始化会话管理器
            self._session_manager = SessionManager(config=self.config)

            # 启动 WebSocket 线程
            self._ws_thread = threading.Thread(
                target=self._ws_client_thread,
                daemon=True,
                name="FeishuWSClient"
            )
            self._ws_thread.start()

            # 等待连接建立
            import time
            for _ in range(10):
                time.sleep(0.5)
                if self._ws_thread_running.is_set():
                    break

            # 启动消息队列处理任务
            asyncio.create_task(self._process_message_queue())

            # 启动会话清理任务
            await self._session_manager.start_cleanup_task(interval=60)

            self._running = True
            self._set_state(ConnectionState.CONNECTED)
            logger.info("FeishuSkill: [CONNECTED] WebSocket 连接已建立")

        except Exception as e:
            logger.error(f"FeishuSkill: [CONNECT_FAIL] {e}")
            self._set_state(ConnectionState.ERROR)
            raise

    async def disconnect(self) -> None:
        """断开与飞书的连接。"""
        logger.info("FeishuSkill: [DISCONNECT_START]...")
        self._running = False

        if self._session_manager:
            await self._session_manager.stop_cleanup_task()

        if self._ws_thread and self._ws_thread.is_alive():
            self._ws_thread.join(timeout=5)

        self._set_state(ConnectionState.DISCONNECTED)
        logger.info("FeishuSkill: [DISCONNECTED]")

    async def _process_message_queue(self) -> None:
        """处理消息队列。"""
        while self._running:
            try:
                if not self._message_queue.empty():
                    event_data = self._message_queue.get_nowait()
                    await self._handle_message_event(event_data)
                else:
                    await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"FeishuSkill: [QUEUE_ERROR] {e}")
                await asyncio.sleep(0.5)

    def _handle_im_message(self, event: P2ImMessageReceiveV1) -> None:
        """处理接收到的 IM 消息事件。"""
        try:
            event_data = event.event
            sender = event_data.sender if event_data else None
            message = event_data.message if event_data else None

            open_id = sender.sender_id.open_id if sender and sender.sender_id else "unknown"
            message_id = message.message_id if message else "unknown"
            content = message.content if message else ""
            chat_id = message.chat_id if message else ""

            # 解析消息内容
            try:
                content_data = json.loads(content)
                text = content_data.get("text", "")
            except (json.JSONDecodeError, TypeError):
                text = content

            content_preview = text[:50] + "..." if len(text) > 50 else text
            logger.info(f"FeishuSkill: [RECV] from={open_id} msg_id={message_id} content='{content_preview}'")

            # 放入队列
            self._message_queue.put({
                "open_id": open_id,
                "message_id": message_id,
                "content": text,
                "chat_id": chat_id,
            })

        except Exception as e:
            logger.error(f"FeishuSkill: [PARSE_ERROR] {e}")

    async def _handle_message_event(self, event_data: dict) -> None:
        """处理解析后的消息事件。"""
        open_id = event_data["open_id"]
        message_id = event_data["message_id"]
        content = event_data["content"]
        chat_id = event_data["chat_id"]

        logger.info(f"FeishuSkill: [PROCESS] from={open_id} msg_id={message_id}")

        # 获取或创建会话
        session = self._session_manager.get_or_create(open_id)
        session.message_count += 1
        session.last_activity = asyncio.get_event_loop().time()

        # 如果有 Agent 回调
        if self._agent_callback:
            try:
                # 发送处理中状态 - 使用送心表情回复
                await self.create_reaction(message_id, "LOVE")
                logger.info(f"FeishuSkill: [PROCESSING] open_id={open_id} sent love reaction")

                # 调用 Agent
                response = await self._agent_callback(open_id, content)
                response_preview = response[:50] + "..." if len(response) > 50 else response
                logger.info(f"FeishuSkill: [AGENT_RESP] open_id={open_id} response='{response_preview}'")

                # 发送回复
                await self.send_text(open_id, response)
                logger.info(f"FeishuSkill: [SENT] open_id={open_id}")

            except Exception as e:
                logger.error(f"FeishuSkill: [PROCESS_ERROR] {e}")
                await self.send_text(open_id, "抱歉，处理您的消息时发生错误。")

    # ==================== SDK 功能封装 ====================

    # ==================== SDK 功能封装 ====================

    async def send_text(self, receive_id: str, text: str) -> str:
        """
        发送文本消息。

        Args:
            receive_id: 用户 open_id
            text: 消息内容

        Returns:
            消息 ID
        """
        text_preview = text[:50] + "..." if len(text) > 50 else text
        logger.info(f"FeishuSkill: [SEND_TEXT] to={receive_id} text='{text_preview}'")

        # 构建消息体
        body = im.v1.CreateMessageRequestBody()
        body.receive_id = receive_id
        body.msg_type = "text"
        body.content = json.dumps({"text": text})

        request = im.v1.CreateMessageRequest.builder() \
            .receive_id_type("open_id") \
            .request_body(body) \
            .build()

        response = self._im_service.v1.message.create(request)

        if response.success():
            msg_id = response.data.message_id
            logger.info(f"FeishuSkill: [SEND_OK] msg_id={msg_id} to={receive_id}")
            return msg_id
        else:
            logger.error(f"FeishuSkill: [SEND_FAIL] {response.msg}")
            raise RuntimeError(f"发送消息失败: {response.msg}")

    async def reply_message(self, message_id: str, text: str) -> str:
        """
        回复消息。

        Args:
            message_id: 被回复的消息 ID
            text: 回复内容

        Returns:
            消息 ID
        """
        logger.info(f"FeishuSkill: [REPLY] to={message_id}")

        # 构建消息体
        body = im.v1.ReplyMessageRequestBody()
        body.msg_type = "text"
        body.content = json.dumps({"text": text})

        request = im.v1.ReplyMessageRequest.builder() \
            .message_id(message_id) \
            .request_body(body) \
            .build()

        response = await self._im_service.v1.message.areply(request)

        if response.success():
            msg_id = response.data.message_id
            logger.info(f"FeishuSkill: [REPLY_OK] msg_id={msg_id}")
            return msg_id
        else:
            logger.error(f"FeishuSkill: [REPLY_FAIL] {response.msg}")
            raise RuntimeError(f"回复消息失败: {response.msg}")

    async def get_message(self, message_id: str) -> dict:
        """
        获取消息内容。

        Args:
            message_id: 消息 ID

        Returns:
            消息数据字典
        """
        logger.info(f"FeishuSkill: [GET_MSG] msg_id={message_id}")

        request = im.v1.GetMessageRequest.builder() \
            .message_id(message_id) \
            .build()

        response = await self._im_service.v1.message.aget(request)

        if response.success():
            data = response.data
            logger.info(f"FeishuSkill: [GET_MSG_OK] msg_id={message_id}")
            return {
                "message_id": data.message_id,
                "content": data.content,
                "msg_type": data.msg_type,
            }
        else:
            logger.error(f"FeishuSkill: [GET_MSG_FAIL] {response.msg}")
            raise RuntimeError(f"获取消息失败: {response.msg}")

    async def delete_message(self, message_id: str) -> bool:
        """
        删除消息。

        Args:
            message_id: 消息 ID

        Returns:
            是否成功
        """
        logger.info(f"FeishuSkill: [DELETE_MSG] msg_id={message_id}")

        request = im.v1.DeleteMessageRequest.builder() \
            .message_id(message_id) \
            .build()

        response = await self._im_service.v1.message.adelete(request)

        if response.success():
            logger.info(f"FeishuSkill: [DELETE_OK] msg_id={message_id}")
            return True
        else:
            logger.error(f"FeishuSkill: [DELETE_FAIL] {response.msg}")
            return False

    async def create_reaction(self, message_id: str, emoji_id: str = "SMILE") -> bool:
        """
        添加表情反应。

        Args:
            message_id: 消息 ID
            emoji_id: 表情 ID (如 "SMILE", "HEART", "THUMBUP", "CLAP", "WAVE", "OK")

        Returns:
            是否成功
        """
        logger.info(f"FeishuSkill: [REACTION_ADD] msg_id={message_id} emoji_id={emoji_id}")

        # 构建 Emoji 对象 (必须使用大写格式)
        emoji = Emoji.builder().emoji_type(emoji_id).build()

        body = im.v1.CreateMessageReactionRequestBody()
        body.reaction_type = emoji

        request = im.v1.CreateMessageReactionRequest.builder() \
            .message_id(message_id) \
            .request_body(body) \
            .build()

        response = await self._im_service.v1.message_reaction.acreate(request)

        if response.success():
            logger.info(f"FeishuSkill: [REACTION_OK] msg_id={message_id}")
            return True
        else:
            logger.error(f"FeishuSkill: [REACTION_FAIL] {response.msg}")
            return False

    async def upload_attachment(self, file_type: str, file_name: str, file_path: str) -> str:
        """
        上传文件/图片。

        Args:
            file_type: 文件类型 (image, file, audio, video)
            file_name: 文件名
            file_path: 文件路径

        Returns:
            attachment key
        """
        logger.info(f"FeishuSkill: [UPLOAD] type={file_type} name={file_name}")

        # Note: upload_attachment might need different API
        # This is a placeholder - check SDK for actual implementation
        logger.warning(f"FeishuSkill: [UPLOAD] Not fully implemented yet")
        raise NotImplementedError("Upload attachment not yet implemented")

    def get_stats(self) -> dict:
        """获取统计信息。"""
        stats = {
            "platform": "feishu",
            "state": self._state.value,
            "is_connected": self.is_connected,
            "is_enabled": self.is_enabled,
        }

        if self._session_manager:
            stats.update(self._session_manager.get_stats())

        return stats


# 模块导出
__all__ = [
    "FeishuSkill",
    "FeishuConfig",
]
