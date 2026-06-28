"""
会员分层策略工具
RFM 计算 + K-Means 聚类 + LLM 策略生成
"""
import json
import os
import sys
from typing import Any

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from agent.prompts.templates import SEGMENTATION_PROMPT
from agent.llm_utils import safe_invoke, parse_llm_json, safe_json_dumps

# 延迟导入避免循环
def _get_llm():
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
        temperature=0.7,
        max_tokens=2048,
    )


class SegmentationTool:
    """会员分层策略生成"""

    def execute(self, members: list[dict], params: dict) -> dict[str, Any]:
        """执行分层策略生成"""
        if not members:
            return self._empty_result()

        # 1. 计算 RFM
        df = self._calculate_rfm(members)

        # 2. K-Means 聚类
        n_clusters = params.get("n_clusters", 6)
        segments = self._kmeans_cluster(df, n_clusters)

        # 3. LLM 生成策略
        industry = self._get_industry(members)
        strategies = self._generate_strategies(segments, industry)

        return strategies

    def _calculate_rfm(self, members: list[dict]) -> pd.DataFrame:
        """计算 RFM 指标"""
        from datetime import datetime

        now = datetime.now()
        records = []
        for m in members:
            try:
                last_date = pd.to_datetime(m.get("last_order_date", "2025-01-01"))
                recency = (now - last_date).days
            except Exception:
                recency = 365

            records.append({
                "member_id": m["member_id"],
                "recency": recency,
                "frequency": m.get("orders_365d", 0),
                "monetary": m.get("total_spent", 0),
                "brand_name": m.get("brand_name", ""),
            })

        return pd.DataFrame(records)

    def _kmeans_cluster(self, df: pd.DataFrame, n_clusters: int = 6) -> list[dict]:
        """K-Means 聚类"""
        features = df[["recency", "frequency", "monetary"]].copy()
        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(features)

        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        df["cluster"] = kmeans.fit_predict(features_scaled)

        segments = []
        segment_names = {
            0: "高价值活跃会员",
            1: "稳定复购会员",
            2: "潜力成长会员",
            3: "低频沉睡会员",
            4: "价格敏感会员",
            5: "流失预警会员",
        }

        for cluster_id in range(n_clusters):
            cluster_df = df[df["cluster"] == cluster_id]
            if len(cluster_df) == 0:
                continue

            segments.append({
                "name": segment_names.get(cluster_id, f"分层{cluster_id+1}"),
                "size": len(cluster_df),
                "percentage": round(len(cluster_df) / len(df) * 100, 1),
                "avg_recency": round(cluster_df["recency"].mean(), 0),
                "avg_frequency": round(cluster_df["frequency"].mean(), 1),
                "avg_monetary": round(cluster_df["monetary"].mean(), 0),
            })

        segments.sort(key=lambda s: s["avg_monetary"], reverse=True)
        return segments

    def _generate_strategies(self, segments: list[dict], industry: str) -> dict:
        """调用 LLM 生成策略建议"""
        segments_json = safe_json_dumps(segments, max_chars=15_000)
        prompt = SEGMENTATION_PROMPT.format(
            industry=industry or "鞋服",
            segments_json=segments_json,
        )

        llm = _get_llm()
        response, error = safe_invoke(llm, prompt, label="分层策略生成")

        if error:
            # LLM 调用失败，使用基于规则的回退
            return {
                "overall_recommendation": f"基于RFM分析自动生成（LLM调用异常: {error[:80]}）",
                "segments": [
                    {**s, "strategy_direction": "精细化运营", "channels": ["企微"], "offer_type": "满减券", "expected_conversion": 0.15}
                    for s in segments
                ],
            }

        fallback = {
            "overall_recommendation": "基于RFM分析自动生成",
            "segments": [
                {**s, "strategy_direction": "精细化运营", "channels": ["企微"], "offer_type": "满减券", "expected_conversion": 0.15}
                for s in segments
            ],
        }
        result = parse_llm_json(response, fallback)

        # 注入原始聚类数据
        result["segments"] = [
            {**next((s for s in segments if s["name"] == strat.get("name", "")), {}), **strat}
            for strat in result.get("segments", [])
        ]
        return result

    def _get_industry(self, members: list[dict]) -> str:
        """从会员数据中推断行业"""
        for m in members:
            if m.get("brand_industry"):
                return m["brand_industry"]
        return "鞋服"

    def _empty_result(self) -> dict:
        return {
            "overall_recommendation": "暂无足够数据进行分析",
            "segments": [],
        }
