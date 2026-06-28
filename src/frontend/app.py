"""
会员运营智能体 — Streamlit 前端
自然语言驱动的对话式 Agent 界面
"""
import streamlit as st
import requests
import json
import time
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="会员运营智能体",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_URL = "http://localhost:8000/api/agent/chat"

# =========== Sidebar ===========
with st.sidebar:
    st.markdown("## 🤖 会员运营智能体")

    st.divider()

    st.markdown("### 💡 试试这样说")
    examples = [
        ("📊", "帮我给百丽品牌做会员分层，分析近90天数据"),
        ("✍️", "给高价值活跃会员生成促活文案，调性高端轻奢"),
        ("📈", "预测满399减60活动效果，目标高价值会员，企微触达7天"),
    ]
    for icon, ex in examples:
        if st.button(f"{icon} {ex[:28]}...", use_container_width=True, key=f"eg_{ex[:12]}"):
            st.session_state.pending_message = ex

    st.divider()

# =========== Init ===========
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_message" not in st.session_state:
    st.session_state.pending_message = ""

# =========== Chat Display ===========
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        role = msg["role"]

        if role == "user":
            st.markdown(msg["content"])
        elif msg.get("result_data"):
            result = msg["result_data"]
            rtype = result.get("type", "")
            data = result.get("result", {})

            if rtype == "segmentation":
                if data.get("overall_recommendation"):
                    st.info(data["overall_recommendation"])
                segs = data.get("segments", [])
                st.success(f"✅ 分层完成，共 {len(segs)} 个分层")
                _render_segmentation(data)

            elif rtype == "copywriting":
                if data.get("recommendation"):
                    st.info(data["recommendation"])
                st.success(f"✅ 生成 {len(data.get('variants', []))} 版文案")
                _render_copywriting(data)

            elif rtype == "prediction":
                st.success("✅ 预测完成")
                _render_prediction(data)
        elif "error" in msg:
            st.error(msg["content"])
        else:
            st.markdown(msg.get("content", ""))


def _render_result(result: dict):
    """根据结果类型渲染不同组件"""
    result_type = result.get("type", "")

    if result_type == "segmentation":
        _render_segmentation(result.get("result", {}))
    elif result_type == "copywriting":
        _render_copywriting(result.get("result", {}))
    elif result_type == "prediction":
        _render_prediction(result.get("result", {}))
    elif result_type == "error":
        st.error(result.get("result", {}).get("message", "执行出错"))


def _render_segmentation(data: dict):
    """渲染分层结果"""
    segments = data.get("segments", [])
    if not segments:
        return

    # Overall recommendation
    if data.get("overall_recommendation"):
        st.info(data["overall_recommendation"])

    # Pyramid chart
    sizes = [s.get("percentage", 0) for s in segments]
    names = [s.get("name", "") for s in segments]

    fig = go.Figure(go.Funnel(
        y=names, x=sizes,
        textinfo="value+percent initial",
        marker={"color": ["#F59E0B", "#3B82F6", "#14B8A6", "#8B5CF6", "#EC4899", "#F43F5E"]},
    ))
    fig.update_layout(height=300, margin=dict(l=20, r=20, t=10, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

    # Strategy cards
    cols = st.columns(min(3, len(segments)))
    for i, seg in enumerate(segments):
        with cols[i % 3]:
            with st.container(border=True):
                emoji = ["👑", "🟢", "🟡", "🔵", "🟠", "🔴"][i % 6]
                st.subheader(f"{emoji} {seg.get('name', '')}")
                st.metric("规模", f"{seg.get('size', 0):,}人", f"{seg.get('percentage', 0)}%")
                st.caption(f"策略: {seg.get('strategy_direction', '')}")
                chs = seg.get("channels", [])
                if chs:
                    st.caption(f"渠道: {' · '.join(chs)}")
                conv = seg.get("expected_conversion", 0)
                if conv:
                    st.metric("预期转化率", f"{conv:.0%}")


def _render_copywriting(data: dict):
    """渲染文案结果"""
    variants = data.get("variants", [])
    if not variants:
        return

    if data.get("recommendation"):
        st.info(data["recommendation"])

    cols = st.columns(len(variants))
    for i, v in enumerate(variants):
        with cols[i]:
            with st.container(border=True):
                st.caption(v.get("type", "").upper())
                st.markdown(f"**{v.get('title', '')}**")
                st.markdown(v.get("body", ""))
                st.divider()
                conv = v.get("predicted_conversion", 0)
                st.metric("预测转化率", f"{conv:.0%}")
                st.caption(f"🕐 {v.get('send_time', '')} · 📱 {v.get('channel', '')}")


def _render_prediction(data: dict):
    """渲染预测结果"""
    metrics = data.get("metrics", {})
    if not metrics:
        return

    # KPI cards
    cols = st.columns(3)
    metric_list = [
        ("coverage", "覆盖率", "{:.0%}"),
        ("conversion", "转化率", "{:.1%}"),
        ("roi", "ROI", "{:.1f}"),
    ]
    for i, (key, label, fmt) in enumerate(metric_list):
        m = metrics.get(key, {})
        val = m.get("value", 0)
        bench = m.get("benchmark", 0)
        with cols[i]:
            delta = (val - bench) / max(bench, 0.001) if bench else 0
            st.metric(label, fmt.format(val), delta=f"{delta:+.0%} vs 基准")

    cols2 = st.columns(3)
    for i, (key, label) in enumerate([("gmv", "GMV"), ("avg_order", "客单价"), ("cost", "优惠成本")]):
        m = metrics.get(key, {})
        val = m.get("value", 0)
        with cols2[i]:
            if isinstance(val, (int, float)):
                st.metric(label, f"¥{val:,.0f}" if val > 1000 else f"{val:.0f}")

    # Warnings
    for w in data.get("warnings", []):
        st.warning(w.get("message", ""))

    # Suggestions
    for s in data.get("suggestions", []):
        st.info(f"💡 {s.get('action', '')} — {s.get('expected_impact', '')}")


# =========== Chat Input & Send ===========
def process_message(prompt: str):
    """发送消息到后端"""
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Agent 思考中..."):
                resp = requests.post(
                    API_URL,
                    json={"message": prompt, "stream": False},
                    timeout=120,
                )
                resp.raise_for_status()
                result = resp.json()

            rtype = result.get("type", "")
            data = result.get("result", {})

            if rtype == "segmentation":
                segs = data.get("segments", [])
                if data.get("overall_recommendation"):
                    st.info(data["overall_recommendation"])
                st.success(f"✅ 分层完成，共 {len(segs)} 个分层")
                _render_segmentation(data)

            elif rtype == "copywriting":
                variants = data.get("variants", [])
                st.success(f"✅ 生成 {len(variants)} 版文案")
                _render_copywriting(data)

            elif rtype == "prediction":
                st.success("✅ 预测完成")
                _render_prediction(data)

            elif rtype == "error":
                st.error(data.get("message", "执行出错"))

            # Save
            st.session_state.messages.append({
                "role": "assistant",
                "result_type": rtype,
                "result_data": result,
            })

        except requests.exceptions.ConnectionError:
            error_msg = "⚠️ 后端未启动，请先运行 `python src/backend/main.py`"
            st.error(error_msg)
            st.session_state.messages.append({"role": "assistant", "error": True, "content": error_msg})
        except Exception as e:
            error_msg = f"❌ 调用失败: {str(e)[:200]}"
            st.error(error_msg)
            st.session_state.messages.append({"role": "assistant", "error": True, "content": error_msg})


# Handle pending (from sidebar)
if st.session_state.pending_message:
    prompt = st.session_state.pending_message
    st.session_state.pending_message = ""
    process_message(prompt)

# Chat input
if prompt := st.chat_input("用自然语言描述你的需求..."):
    process_message(prompt)

# Welcome state
if not st.session_state.messages:
    st.title("🤖 会员运营智能体")
    st.caption("直接告诉我你的需求，我会自动识别意图、提取参数、执行分析。")
    st.divider()
    cols = st.columns(3)
    with cols[0]:
        st.markdown("### 📊 会员分层")
        st.caption("帮你分析品牌会员数据，自动聚类分层并给出差异化运营策略")
    with cols[1]:
        st.markdown("### ✍️ 文案生成")
        st.caption("根据目标群体和品牌调性，生成多版本个性化营销文案")
    with cols[2]:
        st.markdown("### 📈 效果预测")
        st.caption("基于历史数据预测活动转化率、ROI等关键指标，识别风险")
