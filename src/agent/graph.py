"""
Agent 核心图结构 — LangGraph StateGraph
"""
import os
import json
import logging
from typing import Literal

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, END

from agent.state import AgentState
from agent.prompts.templates import (
    INTENT_RECOGNITION_PROMPT,
    SEGMENTATION_PROMPT,
    COPYWRITING_PROMPT,
    PREDICTION_PROMPT,
)
from agent.llm_utils import safe_invoke, parse_llm_json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent.graph")

load_dotenv()

# ===== LLM 配置 =====
llm = ChatOpenAI(
    model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
    temperature=0.7,
    max_tokens=2048,
)


# ===== 节点函数 =====


def understand_intent(state: AgentState) -> dict:
    """Step 1: 意图识别 + 参数提取"""
    query = state.get("user_query", "")
    prompt = INTENT_RECOGNITION_PROMPT.format(user_query=query)

    response, error = safe_invoke(llm, prompt, label="意图识别")

    if error:
        # LLM 调用失败，关键词回退
        logger.warning(f"意图识别 LLM 调用失败，使用关键词回退: {error}")
        intent = "segmentation"
        if any(w in query for w in ["文案", "推送", "生成"]):
            intent = "copywriting"
        elif any(w in query for w in ["预测", "预估", "效果", "ROI"]):
            intent = "prediction"
        result = {"intent": intent, "confidence": 0.5, "params": {}}
    else:
        result = parse_llm_json(response, {"intent": "segmentation", "confidence": 0.5, "params": {}})

    return {
        "intent": result.get("intent", "segmentation"),
        "intent_confidence": result.get("confidence", 0.5),
        "extracted_params": result.get("params", {}),
        "current_step": "understand_intent",
        "error_message": error,
        "messages": [AIMessage(content=f"✅ 识别意图：{result.get('intent', '')}，置信度 {result.get('confidence', 0):.0%}")],
    }


def retrieve_data(state: AgentState) -> dict:
    """Step 2: 检索 Mock 数据"""
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from data.loader import get_members, get_campaigns

    params = state.get("extracted_params", {})
    brand = params.get("brand")

    # 品牌名映射
    brand_map = {
        "百丽": "belle", "百丽集团": "belle", "belle": "belle",
        "安踏": "anta", "安踏集团": "anta", "anta": "anta",
        "慕思": "derucci", "慕思寝具": "derucci", "derucci": "derucci",
    }
    brand_id = brand_map.get(brand) if brand else None

    members = get_members(brand_id)
    campaigns = get_campaigns(brand_id)

    return {
        "retrieved_members": members,
        "retrieved_campaigns": campaigns,
        "current_step": "retrieve_data",
        "messages": [AIMessage(content=f"✅ 检索数据：{len(members)} 条会员，{len(campaigns)} 条历史活动")],
    }


def generate_segmentation(state: AgentState) -> dict:
    """Step 3: 分层策略生成"""
    from agent.tools.segmentation import SegmentationTool

    tool = SegmentationTool()
    params = state.get("extracted_params", {})
    members = state.get("retrieved_members", [])

    result = tool.execute(members, params)
    return {
        "segmentation_result": result,
        "current_step": "generate_segmentation",
        "messages": [AIMessage(content=f"✅ 分层完成：{len(result.get('segments', []))} 个分层")],
    }


def generate_copywriting(state: AgentState) -> dict:
    """Step 3: 文案生成"""
    from agent.tools.copywriting import CopywritingTool

    tool = CopywritingTool()
    params = state.get("extracted_params", {})
    members = state.get("retrieved_members", [])
    campaigns = state.get("retrieved_campaigns", [])

    result = tool.execute(members, campaigns, params)
    return {
        "copywriting_result": result,
        "current_step": "generate_copywriting",
        "messages": [AIMessage(content=f"✅ 文案生成：{len(result.get('variants', []))} 个变体")],
    }


def predict_effect(state: AgentState) -> dict:
    """Step 3: 效果预测"""
    from agent.tools.prediction import PredictionTool

    tool = PredictionTool()
    params = state.get("extracted_params", {})
    campaigns = state.get("retrieved_campaigns", [])

    result = tool.execute(campaigns, params)
    return {
        "prediction_result": result,
        "current_step": "predict_effect",
        "messages": [AIMessage(content=f"✅ 预测完成：预计转化率 {result.get('metrics', {}).get('conversion', {}).get('value', 0)}")],
    }


def generate_report(state: AgentState) -> dict:
    """Step 4: 组装最终报告"""
    intent = state.get("intent", "segmentation")

    report_map = {
        "segmentation": "segmentation_result",
        "copywriting": "copywriting_result",
        "prediction": "prediction_result",
    }
    result_key = report_map.get(intent)
    result = state.get(result_key, {})

    return {
        "done": True,
        "current_step": "generate_report",
        "intent": intent,
        "error_message": state.get("error_message", ""),
        "segmentation_result": state.get("segmentation_result", {}),
        "copywriting_result": state.get("copywriting_result", {}),
        "prediction_result": state.get("prediction_result", {}),
        "messages": [AIMessage(content=json.dumps({"type": intent, "result": result}, ensure_ascii=False))],
    }


# ===== 路由函数 =====

def route_by_intent(state: AgentState) -> Literal["generate_segmentation", "generate_copywriting", "predict_effect"]:
    """根据意图路由到对应工具节点"""
    intent = state.get("intent", "segmentation")
    routes = {
        "segmentation": "generate_segmentation",
        "copywriting": "generate_copywriting",
        "prediction": "predict_effect",
    }
    return routes.get(intent, "generate_segmentation")


# ===== 构建图 =====

def build_graph() -> StateGraph:
    """构建并编译 LangGraph 工作流"""
    workflow = StateGraph(AgentState)

    # 添加节点
    workflow.add_node("understand_intent", understand_intent)
    workflow.add_node("retrieve_data", retrieve_data)
    workflow.add_node("generate_segmentation", generate_segmentation)
    workflow.add_node("generate_copywriting", generate_copywriting)
    workflow.add_node("predict_effect", predict_effect)
    workflow.add_node("generate_report", generate_report)

    # 定义边
    workflow.set_entry_point("understand_intent")
    workflow.add_edge("understand_intent", "retrieve_data")

    # 条件路由
    workflow.add_conditional_edges(
        "retrieve_data",
        route_by_intent,
        {
            "generate_segmentation": "generate_segmentation",
            "generate_copywriting": "generate_copywriting",
            "predict_effect": "predict_effect",
        }
    )

    # 所有工具 → 生成报告 → 结束
    workflow.add_edge("generate_segmentation", "generate_report")
    workflow.add_edge("generate_copywriting", "generate_report")
    workflow.add_edge("predict_effect", "generate_report")
    workflow.add_edge("generate_report", END)

    return workflow.compile()


# 编译后的图实例
graph = build_graph()
