"""
会员运营智能体 — FastAPI 后端
提供 /health 和 /api/agent/chat (SSE流式) 端点
Phase 2: 接入真实 LangGraph Agent
"""
import json
import os
import sys
import time
import asyncio
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

# 确保 agent 模块可导入 — 添加 src/ 到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

app = FastAPI(title="会员运营智能体 API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    context: dict | None = None
    stream: bool = True


@app.get("/api/health")
async def health():
    from agent.graph import graph
    return {
        "status": "ok",
        "version": "0.2.0",
        "agent": "LangGraph + DeepSeek V3",
        "graph_nodes": list(graph.get_graph().nodes.keys()),
        "timestamp": time.time(),
    }


def _format_step_event(step_num: int, status: str, label: str, detail: str = "") -> dict:
    """生成步骤进度事件"""
    return {
        "event": "step",
        "data": json.dumps({
            "step": step_num,
            "status": status,
            "label": label,
            "detail": detail,
        }, ensure_ascii=False),
    }


async def _run_agent(message: str) -> AsyncGenerator[dict, None]:
    """运行 LangGraph Agent 并流式推送"""
    from agent.graph import graph

    step_num = 0

    # 初始状态
    initial_state = {
        "user_query": message,
        "messages": [],
        "intent": "",
        "intent_confidence": 0.0,
        "extracted_params": {},
        "retrieved_members": [],
        "retrieved_campaigns": [],
        "segmentation_result": {},
        "copywriting_result": {},
        "prediction_result": {},
        "current_step": "",
        "error_message": "",
        "done": False,
    }

    try:
        # 使用 astream 逐步获取节点输出
        async for event in graph.astream(initial_state, stream_mode="updates"):
            for node_name, node_output in event.items():
                step_num += 1

                current_step = node_output.get("current_step", node_name)
                done = node_output.get("done", False)

                # 提取节点描述
                step_labels = {
                    "understand_intent": ("理解意图", f"意图={node_output.get('intent', '?')}"),
                    "retrieve_data": ("检索数据", f"会员={len(node_output.get('retrieved_members', []))}条"),
                    "generate_segmentation": ("分层策略", "RFM计算+聚类完成"),
                    "generate_copywriting": ("文案生成", "生成文案变体"),
                    "predict_effect": ("效果预测", "预测报告生成"),
                    "generate_report": ("输出报告", "组装结果"),
                }
                label_info = step_labels.get(current_step, (current_step, ""))
                label, detail = label_info if isinstance(label_info, tuple) else (label_info, "")

                yield _format_step_event(step_num, "done", label, detail)

                if done:
                    # 发送最终结果
                    result_data = None
                    for key in ["segmentation_result", "copywriting_result", "prediction_result"]:
                        if node_output.get(key):
                            result_data = node_output[key]
                            break

                    if result_data:
                        intent = node_output.get("intent", "segmentation")
                        error_msg = node_output.get("error_message", "")
                        yield {
                            "event": "result",
                            "data": json.dumps({
                                "type": intent,
                                "result": result_data,
                                "error": error_msg,
                                "timestamp": time.time(),
                            }, ensure_ascii=False),
                        }

                    yield {"event": "done", "data": "{}"}
                    return

        # 如果没有 done，手动发送
        yield {"event": "done", "data": "{}"}

    except Exception as e:
        yield _format_step_event(step_num + 1, "error", "执行错误", str(e))
        yield {
            "event": "result",
            "data": json.dumps({
                "type": "error",
                "result": {"error": str(e), "message": "Agent 执行出错，请重试"},
            }, ensure_ascii=False),
        }
        yield {"event": "done", "data": "{}"}


@app.post("/api/agent/chat")
async def agent_chat(req: ChatRequest):
    """Agent 对话入口"""
    from agent.graph import graph

    # 非流式模式：直接返回 JSON
    if not req.stream:
        initial_state = {
            "user_query": req.message,
            "messages": [],
            "intent": "", "intent_confidence": 0.0, "extracted_params": {},
            "retrieved_members": [], "retrieved_campaigns": [],
            "segmentation_result": {}, "copywriting_result": {}, "prediction_result": {},
            "current_step": "", "error_message": "", "done": False,
        }
        try:
            result = graph.invoke(initial_state)
            intent = result.get("intent", "segmentation")
            result_data = result.get(f"{intent}_result", {})
            return {
                "type": intent,
                "result": result_data,
                "error": result.get("error_message", ""),
                "timestamp": time.time(),
            }
        except Exception as e:
            return {
                "type": "error",
                "result": {"error": str(e), "message": "Agent 执行出错"},
                "timestamp": time.time(),
            }

    # 流式模式：SSE
    async def event_generator():
        async for event in _run_agent(req.message):
            yield event

    return EventSourceResponse(event_generator())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
