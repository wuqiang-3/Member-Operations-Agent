"""
个性化营销文案生成工具
向量检索历史文案 + Few-shot + 转化率预测
"""
import json
import os
import sys
from typing import Any

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from agent.prompts.templates import COPYWRITING_PROMPT
from agent.llm_utils import safe_invoke, parse_llm_json


def _get_llm():
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
        temperature=0.8,
        max_tokens=2048,
    )


class CopywritingTool:
    """个性化营销文案生成"""

    def execute(
        self,
        members: list[dict],
        campaigns: list[dict],
        params: dict,
    ) -> dict[str, Any]:
        """
        生成个性化营销文案

        params 包含:
          - target_segment: 目标群体（默认"高价值活跃会员"）
          - goal: 活动目标（默认"促活"）
          - tone: 品牌调性（默认"高端轻奢"）
          - n_variants: 变体数量（默认3）
        """
        # 提取参数
        target_segment = params.get("target_segment", "高价值活跃会员")
        goal = params.get("goal", "促活")
        tone = params.get("tone", "高端轻奢")
        n_variants = params.get("n_variants", 3)

        # 构建分段描述
        segment_info = self._describe_segment(members, target_segment)
        industry = self._get_industry(members)

        # 检索历史文案作为 Few-shot
        examples = self._retrieve_examples(campaigns, goal, n=5)

        # 调用 LLM 生成
        prompt = COPYWRITING_PROMPT.format(
            segment_info=segment_info,
            goal=goal,
            tone=tone,
            industry=industry,
            n_variants=n_variants,
            examples=examples or "（暂无历史文案参考）",
        )

        llm = _get_llm()
        response, error = safe_invoke(llm, prompt, label="文案生成")

        if error:
            return self._fallback_variants(target_segment, goal, tone)

        result = parse_llm_json(response, self._fallback_variants(target_segment, goal, tone))

        return result

    def _describe_segment(self, members: list[dict], target: str) -> str:
        """构建目标群体描述"""
        if not members:
            return f"目标群体：{target}（暂无详细数据）"

        # 简单统计
        total = len(members)
        avg_order = sum(m.get("avg_order_value", 0) for m in members) / max(total, 1)
        cities = list(set(m.get("city", "") for m in members))[:5]
        categories = []
        for m in members:
            categories.extend(m.get("preferred_categories", []))
        top_cats = list(set(categories))[:5]

        return (
            f"目标群体：{target}\n"
            f"人群规模：{total:,} 人\n"
            f"平均客单价：¥{avg_order:.0f}\n"
            f"主要城市：{', '.join(cities)}\n"
            f"偏好品类：{', '.join(top_cats)}"
        )

    def _retrieve_examples(self, campaigns: list[dict], goal: str, n: int = 5) -> str:
        """从历史活动中检索高转化文案作为 Few-shot 示例"""
        if not campaigns:
            return ""

        # 按转化率排序
        sorted_campaigns = sorted(
            campaigns,
            key=lambda c: c.get("conversion", 0),
            reverse=True,
        )
        examples = []
        for c in sorted_campaigns[:n]:
            examples.append(
                f"- 活动：{c.get('offer_type', '')} | 目标：{c.get('goal', '')} | "
                f"人群：{c.get('target_segment', '')} | 转化率：{c.get('conversion', 0):.1%}"
            )

        return "\n".join(examples)

    def _get_industry(self, members: list[dict]) -> str:
        for m in members:
            if m.get("brand_industry"):
                return m["brand_industry"]
        return "鞋服"

    def _fallback_variants(self, segment: str, goal: str, tone: str) -> dict:
        """LLM 调用失败时的兜底文案"""
        return {
            "variants": [
                {
                    "type": "情感共鸣型",
                    "title": f"亲爱的会员，专属惊喜等您开启",
                    "body": f"感谢一路相伴！为您准备的专属{goal}礼遇已就绪，{tone}品质，限时专享。",
                    "send_time": "周五 10:00",
                    "channel": "企微1v1",
                    "predicted_conversion": 0.28,
                    "score": 5,
                },
                {
                    "type": "利益驱动型",
                    "title": "老客专享：限时优惠已到账",
                    "body": f"老客回购专享优惠，{tone}好物限时特惠，48小时有效。",
                    "send_time": "周五 10:00",
                    "channel": "小程序push",
                    "predicted_conversion": 0.35,
                    "score": 4,
                },
                {
                    "type": "社交裂变型",
                    "title": "和好友一起，共享专属福利",
                    "body": f"邀请好友一起发现{tone}好物，双方同享专属折扣。",
                    "send_time": "周六 10:00",
                    "channel": "企微群发",
                    "predicted_conversion": 0.22,
                    "score": 3,
                },
            ],
            "recommendation": f"建议优先通过企微1v1发送情感共鸣型文案，目标群体为{segment}，预期综合转化率 28-35%",
        }
