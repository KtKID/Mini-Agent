"""
Discussion Handler - 飞书讨论模式状态机

管理用户通过飞书发起的多 Agent 讨论会话：
- 关键词触发 → 展示 Agent 列表 → 用户选择 → 逐条发言 → 多轮讨论 → 结束

Session 以 session_id（即飞书 chat_id）为 key，确保群聊讨论和私聊互不干扰。
"""

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Awaitable, Optional

from mini_agent.agent_team import (
    AgentTeam,
    DiscussionMode,
)
from mini_agent.agent_team.providers import ProvidersConfig
from mini_agent.agents import AgentConfigLoader, AgentDefinition

logger = logging.getLogger(__name__)


class DiscussionState(Enum):
    """讨论会话状态。"""

    SELECTING = "selecting"  # 等待用户选择 Agent
    DISCUSSING = "discussing"  # 讨论进行中


@dataclass
class UserDiscussionSession:
    """单个讨论会话，以 chat_id 区分。"""

    session_id: str  # chat_id — 群聊 ID 或私聊 ID
    topic: str
    state: DiscussionState
    team: AgentTeam
    agent_names: list[str] = field(default_factory=list)
    round_num: int = 0
    message_count: int = 0


class DiscussionHandler:
    """飞书讨论模式状态机。

    路由用户消息到对应的讨论阶段处理方法，
    管理每个会话的独立 AgentTeam 和 Memory。

    session_id 使用 chat_id（而非 open_id），
    这样同一用户在群聊讨论时，私聊不会被误路由。
    """

    def __init__(
        self,
        providers_config: Optional[ProvidersConfig],
        loader: AgentConfigLoader,
        timeout: float = 30.0,
    ):
        self._providers_config = providers_config
        self._loader = loader
        self._timeout = timeout
        self._sessions: dict[str, UserDiscussionSession] = {}
        # 缓存 agent 列表
        self._agent_list_text: Optional[str] = None
        self._agent_defs: Optional[list[AgentDefinition]] = None

    def _ensure_agent_list(self) -> tuple[str, list[AgentDefinition]]:
        """确保 agent 列表已加载并缓存。"""
        if self._agent_list_text is None or self._agent_defs is None:
            self._agent_list_text, self._agent_defs = self._loader.format_agent_list()
        return self._agent_list_text, self._agent_defs

    def is_active(self, session_id: str) -> bool:
        """检查某个会话是否有活跃的讨论。"""
        return session_id in self._sessions

    async def handle_message(
        self,
        session_id: str,
        content: str,
        send_fn: Callable[[str], Awaitable[None]],
    ) -> None:
        """总路由：根据当前状态分派到对应的处理方法。

        Args:
            session_id: 会话标识（chat_id），区分不同群聊/私聊
            content: 消息文本
            send_fn: 发送消息的回调
        """
        content = content.strip()

        # 新讨论：用户发送 "讨论 {话题}"
        if not self.is_active(session_id):
            if content.startswith("讨论 "):
                topic = content[3:].strip()
                if topic:
                    await self._start_discussion(session_id, topic, send_fn)
                else:
                    await send_fn("请提供讨论话题，例如：讨论 如何设计分布式系统")
            return

        session = self._sessions[session_id]

        if session.state == DiscussionState.SELECTING:
            await self._select_agents(session_id, content, send_fn)
        elif session.state == DiscussionState.DISCUSSING:
            await self._handle_discussing(session_id, content, send_fn)

    async def _start_discussion(
        self,
        session_id: str,
        topic: str,
        send_fn: Callable[[str], Awaitable[None]],
    ) -> None:
        """创建讨论 session 并展示 Agent 列表。"""
        list_text, agent_defs = self._ensure_agent_list()

        if not agent_defs:
            await send_fn("暂无可用的 Agent，无法发起讨论。")
            return

        # 创建 AgentTeam（DEBATE 模式）
        team = AgentTeam(
            name=f"discussion_{session_id}",
            timeout=self._timeout,
            providers_config=self._providers_config,
            discussion_mode=DiscussionMode.DEBATE,
        )

        session = UserDiscussionSession(
            session_id=session_id,
            topic=topic,
            state=DiscussionState.SELECTING,
            team=team,
        )
        self._sessions[session_id] = session

        await send_fn(
            f"话题：{topic}\n\n"
            f"可用 Agent:\n{list_text}\n\n"
            f'请输入编号（逗号分隔），或输入"全部"'
        )

    async def _select_agents(
        self,
        session_id: str,
        content: str,
        send_fn: Callable[[str], Awaitable[None]],
    ) -> None:
        """解析用户选择，创建 Agent，启动第一轮讨论。"""
        session = self._sessions[session_id]
        _, agent_defs = self._ensure_agent_list()

        # 解析选择
        if content.strip() == "全部":
            selected_indices = list(range(len(agent_defs)))
        else:
            try:
                selected_indices = []
                for part in content.replace("，", ",").split(","):
                    idx = int(part.strip()) - 1  # 用户输入从 1 开始
                    if 0 <= idx < len(agent_defs):
                        selected_indices.append(idx)
                    else:
                        await send_fn(
                            f"编号 {part.strip()} 无效，请输入 1-{len(agent_defs)} 之间的编号。"
                        )
                        return
            except ValueError:
                await send_fn(
                    f'请输入有效的编号（逗号分隔），或输入"全部"。\n例如: 1,3'
                )
                return

        if not selected_indices:
            await send_fn("未选择任何 Agent，请重新输入。")
            return

        # 去重并保持顺序
        seen = set()
        unique_indices = []
        for idx in selected_indices:
            if idx not in seen:
                seen.add(idx)
                unique_indices.append(idx)
        selected_indices = unique_indices

        # 添加选中的 Agent 到 team
        selected_names = []
        for idx in selected_indices:
            agent_def = agent_defs[idx]
            personality = self._loader.resolve_personality(agent_def)
            session.team.add_agent(
                name=agent_def.name,
                provider_id=agent_def.provider_id,
                model_name=agent_def.model_name,
                personality_name=personality.name,
                system_prompt=personality.system_prompt,
                response_style=personality.response_style,
            )
            selected_names.append(agent_def.name)

        session.agent_names = selected_names
        session.state = DiscussionState.DISCUSSING

        await send_fn(
            f"参与者: {', '.join(selected_names)} — 讨论开始"
        )

        # 运行第 1 轮
        await self._run_round(session, send_fn, user_message=session.topic)

    async def _handle_discussing(
        self,
        session_id: str,
        content: str,
        send_fn: Callable[[str], Awaitable[None]],
    ) -> None:
        """讨论进行中的消息处理。"""
        if content == "讨论结束":
            await self._end_discussion(session_id, send_fn)
        elif content == "继续":
            session = self._sessions[session_id]
            await self._run_round(session, send_fn)
        else:
            # 用户观点作为新消息加入
            session = self._sessions[session_id]
            await self._run_round(session, send_fn, user_message=content)

    async def _run_round(
        self,
        session: UserDiscussionSession,
        send_fn: Callable[[str], Awaitable[None]],
        user_message: Optional[str] = None,
    ) -> None:
        """运行一轮讨论：逐个 Agent 发言并即时发送。"""
        session.round_num += 1

        # 如果有用户消息，加入 Memory
        if user_message:
            session.team.chatroom.memory.add_message(
                role="user", content=user_message
            )

        # 遍历 active agents，逐个调用并即时发送
        agent_list = [
            agent
            for agent in session.team.agents.values()
            if agent.is_active
        ]

        for agent in agent_list:
            # 获取当前 Memory 上下文
            messages = session.team.chatroom.memory.get_messages_for_agent(
                current_agent_name=agent.name
            )

            try:
                response = await asyncio.wait_for(
                    agent.generate_response(messages),
                    timeout=self._timeout,
                )

                # 即时发送到飞书
                try:
                    await send_fn(
                        f"【第 {session.round_num} 轮 · {agent.name}】\n{response}"
                    )
                except Exception as send_err:
                    logger.error(
                        f"DiscussionHandler: Failed to send message for {agent.name}: {send_err}"
                    )

                session.message_count += 1

                # 写入 Memory，让下一个 agent 能看到
                session.team.chatroom.memory.add_message(
                    role="agent",
                    content=response,
                    agent_id=agent.id,
                    agent_name=agent.name,
                )

            except asyncio.TimeoutError:
                logger.warning(
                    f"DiscussionHandler: Agent {agent.name} timed out "
                    f"(round {session.round_num})"
                )
                try:
                    await send_fn(
                        f"【第 {session.round_num} 轮 · {agent.name}】⏰ 响应超时"
                    )
                except Exception:
                    pass
            except Exception as e:
                logger.error(
                    f"DiscussionHandler: Agent {agent.name} error: {e}"
                )
                try:
                    await send_fn(
                        f"【第 {session.round_num} 轮 · {agent.name}】发生错误: {e}"
                    )
                except Exception:
                    pass

        # 轮次提示
        try:
            await send_fn(
                f"第 {session.round_num} 轮结束 | "
                f'发消息继续 | "继续"下一轮 | "讨论结束"'
            )
        except Exception as e:
            logger.error(f"DiscussionHandler: Failed to send round summary: {e}")

    async def _end_discussion(
        self,
        session_id: str,
        send_fn: Callable[[str], Awaitable[None]],
    ) -> None:
        """结束讨论，发送总结并清理 session。"""
        session = self._sessions.pop(session_id)

        await send_fn(
            f"讨论结束 | "
            f"话题: {session.topic} | "
            f"参与: {', '.join(session.agent_names)} | "
            f"{session.round_num} 轮 | "
            f"{session.message_count} 条消息"
        )
        logger.info(
            f"DiscussionHandler: Discussion ended for {session_id}, "
            f"topic={session.topic}, rounds={session.round_num}"
        )
