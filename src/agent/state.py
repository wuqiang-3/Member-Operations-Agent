"""
Agent 全局状态定义
"""
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage
import operator


class AgentState(TypedDict):
    """LangGraph Agent 全局状态"""

    # ===== 消息历史 =====
    messages: Annotated[Sequence[BaseMessage], operator.add]

    # ===== 用户输入 =====
    user_query: str

    # ===== 意图识别结果 =====
    intent: str                        # "segmentation" | "copywriting" | "prediction"
    intent_confidence: float           # 置信度 0-1
    extracted_params: dict             # {brand, period, segment, goal, tone, ...}

    # ===== 数据检索结果 =====
    retrieved_members: list[dict]      # 召回的会员数据
    retrieved_campaigns: list[dict]    # 召回的历史活动

    # ===== 工具执行结果 =====
    segmentation_result: dict          # 分层结果 {segments: [...], overall: "..."}
    copywriting_result: dict           # 文案结果 {variants: [...], recommendation: "..."}
    prediction_result: dict            # 预测结果 {metrics: {...}, warnings: [...], suggestions: [...]}

    # ===== 执行控制 =====
    current_step: str                  # 当前执行步骤名称
    error_message: str                 # 错误信息
    done: bool                         # 是否完成
